from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.models.ai_recommendation import AIRecommendation, RecommendationTypeEnum
from app.models.ai_validation import AIValidationItem, AIValidationRun
from app.models.diet import DietLog, DietLogItem, MealTypeEnum
from app.models.exercise import ExerciseLog, ExerciseSet, MuscleGroupEnum
from app.models.rag import AIGenerationTrace, RagRetrievalTrace
from app.models.token import RefreshToken
from app.models.user import ActivityLevelEnum, GenderEnum, GoalEnum, User, UserProfile
from app.services.ai_validation_service import (
    AIValidationError,
    AIValidationService,
    ValidationOutcome,
)


class StubTraceValidationService(AIValidationService):
    async def _check_generation_trace_integrity(self, run, user_id):
        return ValidationOutcome(
            evidence={
                "trace_count": 4,
                "attempt_count": 4,
                "request_types": ["chat", "diet", "exercise", "food_analysis"],
            }
        )

    async def _check_retrieval_source_integrity(self, run, user_id):
        return ValidationOutcome(
            evidence={
                "trace_group_count": 3,
                "retrieval_rows": 9,
                "response_rows": 3,
                "source_count": 3,
                "search_backends": ["opensearch"],
            }
        )

    async def _check_privacy_invariants(self, run, user_id, chat_message):
        return ValidationOutcome(
            evidence={
                "retrieval_rows_checked": 9,
                "raw_query_rows": 0,
                "raw_prompt_rows": 0,
                "raw_chat_rows": 0,
            }
        )


def _settings() -> Settings:
    return Settings(
        AI_QUOTA_TIMEZONE="UTC",
        AI_VALIDATION_TIMEOUT_SECONDS=5,
    )


def _mock_transport(*, fail_diet_recommendation: bool = False) -> httpx.MockTransport:
    state = {"diet_id": 10, "exercise_id": 20}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method
        if path.endswith("/health"):
            return httpx.Response(
                200,
                json={"status": "ok", "db": "connected", "redis": "connected"},
            )
        if path.endswith("/auth/register"):
            return httpx.Response(
                201,
                json={
                    "status": "success",
                    "data": {
                        "user": {"id": 42},
                        "access_token": "register-secret-token",
                    },
                },
            )
        if path.endswith("/auth/login"):
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {"access_token": "login-secret-token"},
                },
            )
        if path.endswith("/profile"):
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "weight_kg": 78.4,
                        "goal": "bulk",
                        "target_calories": 3100,
                    },
                },
            )
        if path.endswith("/diet/logs") and method == "POST":
            state["diet_id"] += 1
            return httpx.Response(
                201,
                json={"status": "success", "data": {"id": state["diet_id"]}},
            )
        if path.endswith("/diet/logs") and method == "GET":
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {"meals": {"lunch": [{"id": state["diet_id"]}]}},
                },
            )
        if path.endswith("/exercise/logs") and method == "POST":
            return httpx.Response(
                201,
                json={"status": "success", "data": {"id": state["exercise_id"]}},
            )
        if path.endswith("/exercise/logs") and method == "GET":
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {"exercises": [{"id": state["exercise_id"]}]},
                },
            )
        if path.endswith("/dashboard/today"):
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "nutrition": {"consumed": {"calories": 620}},
                        "exercise": {"exercises_count": 1},
                    },
                },
            )
        if path.endswith("/diet/recommend"):
            if fail_diet_recommendation:
                return httpx.Response(
                    503,
                    json={
                        "status": "error",
                        "error": {"code": "RAG_CONTEXT_UNAVAILABLE"},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {"sources": ["source-a"], "suggested_foods": [{}]},
                },
            )
        if path.endswith("/exercise/recommend"):
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {"sources": ["source-b"], "suggested_exercises": [{}]},
                },
            )
        if path.endswith("/ai/chat"):
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {"answer": "safe answer", "sources": ["source-c"]},
                },
            )
        if path.endswith("/diet/analyze-image"):
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "foods": [
                            {
                                "food_name": "salmon",
                                "serving_size": "100g",
                                "calories": 200,
                                "protein_g": 25,
                                "carbs_g": 0,
                                "fat_g": 10,
                                "confidence": 0.95,
                            }
                        ]
                    },
                },
            )
        if method == "DELETE" and ("/diet/logs/" in path or "/exercise/logs/" in path):
            return httpx.Response(200, json={"status": "success"})
        raise AssertionError(f"Unexpected request: {method} {path}")

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_validation_run_records_checks_report_and_redacts_secrets(
    db_session,
    tmp_path,
):
    image_path = tmp_path / "meal.jpg"
    image_path.write_bytes(b"\xff\xd8\xff\xd9")
    report_path = tmp_path / "validation.md"
    async with httpx.AsyncClient(
        transport=_mock_transport(),
        base_url="http://test/api/v1/",
    ) as client:
        service = StubTraceValidationService(
            db_session,
            _settings(),
            http_client=client,
        )
        result = await service.validate_integration(
            base_url="http://test/api/v1",
            image_path=image_path,
            report_path=report_path,
            mode="mock",
        )

    assert result["status"] == "succeeded"
    assert result["passed_checks"] == 14
    assert result["failed_checks"] == 0
    assert result["cleanup_status"] == "succeeded"
    assert len(result["items"]) == 14

    report_bytes = report_path.read_bytes()
    report = report_bytes.decode("utf-8")
    assert b"\r\n" not in report_bytes
    assert "login-secret-token" not in report
    assert "ui-e2e-" not in report
    assert "오늘 기록" not in report
    assert "raw_user_content_persisted" not in report
    assert "Privacy And Cleanup Boundary" in report

    stored_run = await db_session.scalar(select(AIValidationRun))
    item_count = int(await db_session.scalar(select(func.count(AIValidationItem.id))) or 0)
    assert stored_run is not None
    assert stored_run.status == "succeeded"
    assert item_count == 14


@pytest.mark.asyncio
async def test_validation_run_preserves_partial_failure_and_still_cleans_up(
    db_session,
    tmp_path,
):
    image_path = tmp_path / "meal.jpg"
    image_path.write_bytes(b"\xff\xd8\xff\xd9")
    async with httpx.AsyncClient(
        transport=_mock_transport(fail_diet_recommendation=True),
        base_url="http://test/api/v1/",
    ) as client:
        service = StubTraceValidationService(
            db_session,
            _settings(),
            http_client=client,
        )
        result = await service.validate_integration(
            base_url="http://test/api/v1",
            image_path=image_path,
            mode="mock",
        )

    failed = {
        item["check_name"]: item
        for item in result["items"]
        if item["status"] == "failed"
    }
    assert result["status"] == "partial"
    assert result["cleanup_status"] == "succeeded"
    assert failed["diet_recommendation"]["error_code"] == "RAG_CONTEXT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_registration_persists_cleanup_lineage_before_login_can_fail(db_session):
    run = AIValidationRun(
        mode="mock",
        status="started",
        base_url="http://test/api/v1",
        expected_checks=14,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/register"):
            return httpx.Response(
                201,
                json={"status": "success", "data": {"user": {"id": 77}}},
            )
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(
                503,
                json={"status": "error", "error": {"code": "AUTH_BACKEND_DOWN"}},
            )
        raise AssertionError(request.url.path)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://test/api/v1/",
    ) as client:
        service = AIValidationService(
            db_session,
            _settings(),
            http_client=client,
        )
        with pytest.raises(AIValidationError, match="AUTH_BACKEND_DOWN"):
            await service._check_account_auth(client, run)

    await db_session.refresh(run)
    assert run.validation_user_id == 77


@pytest.mark.asyncio
async def test_cleanup_removes_user_data_and_anonymizes_trace_foreign_keys(db_session):
    user = User(
        email="validation-cleanup@example.com",
        password_hash="hash",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add_all(
        [
            UserProfile(
                user_id=user.id,
                height_cm=175,
                weight_kg=78.4,
                age=32,
                gender=GenderEnum.MALE,
                goal=GoalEnum.BULK,
                activity_level=ActivityLevelEnum.ACTIVE,
            ),
            RefreshToken(
                user_id=user.id,
                token="refresh",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            ),
            AIRecommendation(
                user_id=user.id,
                type=RecommendationTypeEnum.COACHING,
                recommendation="temporary",
            ),
        ]
    )
    diet = DietLog(
        user_id=user.id,
        log_date=datetime.now(timezone.utc).date(),
        meal_type=MealTypeEnum.LUNCH,
    )
    diet.diet_log_items = [
        DietLogItem(
            food_name="temporary",
            calories=100,
            protein_g=10,
            carbs_g=10,
            fat_g=2,
        )
    ]
    exercise = ExerciseLog(
        user_id=user.id,
        exercise_date=datetime.now(timezone.utc).date(),
        exercise_name="temporary",
        muscle_group=MuscleGroupEnum.LEGS,
    )
    exercise.exercise_sets = [ExerciseSet(set_number=1, reps=10, weight_kg=20)]
    generation = AIGenerationTrace(
        user_id=user.id,
        request_type="chat",
        prompt_version="chat_v2",
        status="succeeded",
    )
    retrieval = RagRetrievalTrace(
        user_id=user.id,
        request_type="chat",
        rag_trace_group_id="cleanup-group",
        query_text=None,
        query_hash="a" * 64,
        query_summary="type=chat;chars=10;terms=2;raw_stored=false",
        query_policy_version="query-minimization-v1",
        query_key_version="v1",
        query_retention_until=datetime.now(timezone.utc) + timedelta(days=90),
        query_redacted_at=datetime.now(timezone.utc),
        search_backend="opensearch",
        search_mode="hybrid",
        top_k=3,
        rank=1,
    )
    db_session.add_all([diet, exercise, generation, retrieval])
    await db_session.commit()
    user_id = user.id

    evidence = await AIValidationService(
        db_session,
        _settings(),
    )._cleanup_validation_user(user_id)

    await db_session.refresh(generation)
    await db_session.refresh(retrieval)
    assert evidence["validation_user_removed"] is True
    assert await db_session.get(User, user_id) is None
    assert generation.user_id is None
    assert retrieval.user_id is None
    assert int(await db_session.scalar(select(func.count(DietLog.id))) or 0) == 0
    assert int(await db_session.scalar(select(func.count(ExerciseLog.id))) or 0) == 0
