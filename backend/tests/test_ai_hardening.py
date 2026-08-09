from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import get_settings
from app.models.ai_recommendation import AIRecommendation
from app.models.exercise import ExerciseLog, ExerciseSet, MuscleGroupEnum
from app.models.rag import AIGenerationAttempt, AIGenerationTrace
from app.models.user import ActivityLevelEnum, GoalEnum, User, UserProfile
from app.schemas.ai_generation import DietRecommendationV2, ExerciseRecommendationV2, FoodAnalysisV2
from app.services.ai_service import (
    CHAT_SCHEMA_VERSION,
    DIET_RECOMMEND_SCHEMA_VERSION,
    FOOD_ANALYSIS_SCHEMA_VERSION,
    AIInvocationResult,
    AIService,
    AIServiceError,
    _ProviderCallResult,
)
from app.services.chat_service import ChatService
from app.services.ai_trace_service import (
    AIGenerationAttemptRecorder,
    abandon_stale_ai_requests,
)
from app.services.rag_prompt_context import build_rag_prompt_context
from app.services.recommendation_service import RecommendationService


def _provider_result(payload: dict, *, response_id: str = "response-1") -> _ProviderCallResult:
    import hashlib

    text = json.dumps(payload)
    return _ProviderCallResult(
        text=text,
        model="gemini-test",
        response_id=response_id,
        tokens_input=11,
        tokens_output=7,
        finish_reason="STOP",
        latency_ms=20,
        retry_count=0,
        raw_response_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


def _provider_response(payload: dict, *, response_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        text=json.dumps(payload),
        model_version="gemini-test",
        response_id=response_id,
        usage_metadata=SimpleNamespace(
            prompt_token_count=11,
            candidates_token_count=7,
        ),
        candidates=[SimpleNamespace(finish_reason="STOP")],
    )


def _diet_payload(*, source_refs: list[str] | None = None) -> dict:
    return {
        "recommendation": "남은 단백질을 채우는 식사입니다.",
        "suggested_foods": [
            {
                "food_name": "닭가슴살 현미밥",
                "serving_size": "1인분",
                "calories": 520,
                "protein_g": 45,
                "carbs_g": 60,
                "fat_g": 10,
                "reason": "단백질과 탄수화물 보충",
            }
        ],
        "source_refs": source_refs or ["S1"],
    }


def _diet_context() -> dict:
    return {
        "height_cm": 175,
        "weight_kg": 78,
        "goal": "bulk",
        "goal_description": "벌크업",
        "activity_level": "active",
        "allergies": "유당",
        "food_preferences": "고단백",
        "target_calories": 2800,
        "target_protein_g": 160,
        "target_carbs_g": 350,
        "target_fat_g": 75,
        "consumed_calories": 1200,
        "consumed_protein": 70,
        "consumed_carbs": 130,
        "consumed_fat": 35,
    }


def _service_without_client() -> AIService:
    service = AIService.__new__(AIService)
    service.settings = SimpleNamespace(AI_MAX_OUTPUT_TOKENS=1024, AI_DAILY_REQUEST_LIMIT=30)
    service.flash_model = "gemini-test"
    service.pro_model = "gemini-pro-test"
    return service


class FakeRAGService:
    def __init__(self, documents: list[dict]):
        self.documents = documents
        self.queries: list[str] = []
        self.used_chunk_ids: list[int] = []

    async def search(self, query: str, **kwargs):
        _ = kwargs
        self.queries.append(query)
        return self.documents

    async def mark_traces_used_in_response(self, trace_group_id: str, chunk_ids: list[int]) -> None:
        _ = trace_group_id
        self.used_chunk_ids = chunk_ids

    async def mark_traces_request_id(self, trace_group_id: str | None, request_id: int | None) -> None:
        _ = trace_group_id, request_id


async def _create_profile(db_session) -> User:
    user = User(email="ai-hardening@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserProfile(
            user_id=user.id,
            height_cm=Decimal("175.0"),
            weight_kg=Decimal("78.0"),
            age=32,
            goal=GoalEnum.BULK,
            activity_level=ActivityLevelEnum.ACTIVE,
            allergies=["유당"],
            food_preferences=["고단백"],
            target_calories=2800,
            target_protein_g=Decimal("160.0"),
            target_carbs_g=Decimal("350.0"),
            target_fat_g=Decimal("75.0"),
        )
    )
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_structured_output_repairs_schema_once_and_preserves_provider_metadata():
    service = _service_without_client()
    invalid = _diet_payload()
    invalid["suggested_foods"][0]["calories"] = -1
    service._call_with_retry = AsyncMock(
        side_effect=[_provider_result(invalid), _provider_result(_diet_payload(), response_id="response-2")]
    )

    result = await service.recommend_diet(
        _diet_context(),
        "[S1] evidence",
        allowed_source_refs={"S1"},
    )

    assert result.payload["source_refs"] == ["S1"]
    assert result.response_id == "response-2"
    assert result.tokens_input == 22
    assert result.tokens_output == 14
    assert result.retry_count == 1
    assert result.trace_metadata["provider_call_count"] == 2
    assert result.trace_metadata["provider_retry_count"] == 0
    assert result.trace_metadata["schema_repair_count"] == 1
    assert len(result.trace_metadata["schema_repair_reasons"]) == 1
    assert result.trace_metadata["structured_request_total_latency_ms"] >= 0
    assert result.trace_metadata["initial_prompt_character_count"] > 0
    assert len(result.trace_metadata["provider_prompt_character_counts"]) == 2
    assert service._call_with_retry.await_count == 2
    config = service._call_with_retry.await_args_list[0].args[2]
    assert config.response_json_schema == DietRecommendationV2.model_json_schema()


@pytest.mark.asyncio
async def test_request_lifecycle_records_initial_and_schema_repair_attempts(
    db_session,
):
    user = await _create_profile(db_session)
    service = _service_without_client()
    invalid = _diet_payload()
    invalid["suggested_foods"][0]["calories"] = -1
    generate_content = AsyncMock(
        side_effect=[
            _provider_response(invalid, response_id="invalid-response"),
            _provider_response(_diet_payload(), response_id="repaired-response"),
        ]
    )
    service.client = SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )
    )
    trace = await service.start_generation_trace(
        db_session,
        user_id=user.id,
        request_type="diet",
        prompt_version=DIET_RECOMMEND_SCHEMA_VERSION,
    )
    recorder = AIGenerationAttemptRecorder(db_session, trace.id)

    invocation = await service.recommend_diet(
        _diet_context(),
        "[S1] evidence",
        allowed_source_refs={"S1"},
        attempt_recorder=recorder,
    )
    await service.complete_generation_trace(
        db_session,
        trace.id,
        user_id=user.id,
        request_type="diet",
        prompt_version=DIET_RECOMMEND_SCHEMA_VERSION,
        status="succeeded",
        invocation=invocation,
    )

    attempts = (
        await db_session.execute(
            select(AIGenerationAttempt).order_by(
                AIGenerationAttempt.attempt_no
            )
        )
    ).scalars().all()
    persisted_trace = await db_session.get(AIGenerationTrace, trace.id)

    assert [attempt.attempt_kind for attempt in attempts] == [
        "initial",
        "schema_repair",
    ]
    assert [attempt.status for attempt in attempts] == [
        "succeeded",
        "succeeded",
    ]
    assert attempts[0].provider_response_id == "invalid-response"
    assert attempts[1].provider_response_id == "repaired-response"
    assert persisted_trace is not None
    assert persisted_trace.status == "succeeded"
    assert persisted_trace.provider_invoked is True
    assert persisted_trace.completed_at is not None


@pytest.mark.asyncio
async def test_request_lifecycle_records_provider_retry_attempt(db_session):
    user = await _create_profile(db_session)
    service = _service_without_client()
    generate_content = AsyncMock(
        side_effect=[
            asyncio.TimeoutError(),
            _provider_response(_diet_payload(), response_id="retry-response"),
        ]
    )
    service.client = SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )
    )
    trace = await service.start_generation_trace(
        db_session,
        user_id=user.id,
        request_type="diet",
        prompt_version=DIET_RECOMMEND_SCHEMA_VERSION,
    )

    invocation = await service.recommend_diet(
        _diet_context(),
        "[S1] evidence",
        allowed_source_refs={"S1"},
        attempt_recorder=AIGenerationAttemptRecorder(db_session, trace.id),
    )

    attempts = (
        await db_session.execute(
            select(AIGenerationAttempt).order_by(
                AIGenerationAttempt.attempt_no
            )
        )
    ).scalars().all()
    assert invocation.retry_count == 1
    assert [attempt.attempt_kind for attempt in attempts] == [
        "initial",
        "provider_retry",
    ]
    assert [attempt.status for attempt in attempts] == ["failed", "succeeded"]
    assert attempts[0].error_code == "AI_TIMEOUT"


@pytest.mark.asyncio
async def test_stale_request_reconciliation_marks_parent_and_attempt_abandoned(
    db_session,
):
    user = await _create_profile(db_session)
    service = _service_without_client()
    trace = await service.start_generation_trace(
        db_session,
        user_id=user.id,
        request_type="chat",
        prompt_version=CHAT_SCHEMA_VERSION,
    )
    recorder = AIGenerationAttemptRecorder(db_session, trace.id)
    attempt_id = await recorder.start_attempt(
        attempt_kind="initial",
        model="gemini-test",
    )
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    trace.started_at = stale_time
    attempt = await db_session.get(AIGenerationAttempt, attempt_id)
    assert attempt is not None
    attempt.started_at = stale_time
    await db_session.commit()

    result = await abandon_stale_ai_requests(
        db_session,
        stale_before=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    await db_session.refresh(trace)
    await db_session.refresh(attempt)

    assert result == {
        "attempts_abandoned": 1,
        "requests_abandoned": 1,
        "quota_reservations_released": 0,
    }
    assert trace.status == "abandoned"
    assert trace.error_stage == "lifecycle_reconciliation"
    assert attempt.status == "abandoned"
    assert attempt.error_code == "AI_ATTEMPT_ABANDONED"


@pytest.mark.asyncio
async def test_unknown_source_ref_gets_one_repair_then_schema_error():
    service = _service_without_client()
    service._call_with_retry = AsyncMock(return_value=_provider_result(_diet_payload(source_refs=["S9"])))

    with pytest.raises(AIServiceError) as captured:
        await service.recommend_diet(
            _diet_context(),
            "[S1] evidence",
            allowed_source_refs={"S1"},
        )

    assert captured.value.code == "AI_SCHEMA_INVALID"
    assert captured.value.stage == "schema_validation"
    assert captured.value.retry_count == 1
    assert captured.value.trace_metadata["provider_call_count"] == 2
    assert captured.value.trace_metadata["schema_repair_count"] == 1
    assert captured.value.trace_metadata["validation_errors"]
    assert service._call_with_retry.await_count == 2


@pytest.mark.asyncio
async def test_provider_error_message_does_not_leak_raw_error():
    service = _service_without_client()
    generate_content = AsyncMock(side_effect=RuntimeError("secret-provider-payload"))
    service.client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))

    with pytest.raises(AIServiceError) as captured:
        await service._call_with_retry("gemini-test", ["prompt"], SimpleNamespace(), max_retries=0)

    assert captured.value.code == "AI_SERVICE_ERROR"
    assert "secret-provider-payload" not in captured.value.message
    assert captured.value.trace_metadata == {"exception_type": "RuntimeError"}


def test_generation_schemas_reject_invalid_ranges_and_muscle_groups():
    with pytest.raises(ValidationError):
        FoodAnalysisV2.model_validate(
            {
                "foods": [
                    {
                        "food_name": "밥",
                        "serving_size": "1공기",
                        "calories": -1,
                        "protein_g": 1,
                        "carbs_g": 1,
                        "fat_g": 1,
                        "confidence": 2,
                    }
                ]
            }
        )

    with pytest.raises(ValidationError):
        ExerciseRecommendationV2.model_validate(
            {
                "recommendation": "test",
                "suggested_exercises": [
                    {
                        "exercise_name": "test",
                        "muscle_group": "invalid",
                        "sets": 0,
                        "reps": 0,
                        "reason": "test",
                    }
                ],
                "source_refs": ["S1"],
            }
        )


def test_rag_unavailable_is_skipped_without_provider_invocation():
    error = AIServiceError(
        503,
        "RAG_CONTEXT_UNAVAILABLE",
        "답변 근거를 찾지 못했습니다",
        stage="retrieval",
        provider_invoked=False,
    )

    assert error.trace_status == "skipped"
    assert error.provider_invoked is False


def test_rag_reference_markers_are_resolved_to_verified_titles():
    context = build_rag_prompt_context(
        [
            {"chunk_id": 1, "title": "단백질 가이드", "content": "근거"},
            {"chunk_id": 2, "title": "운동 가이드", "content": "근거"},
        ]
    )

    assert context.resolve_reference_markers("S1과 S2를 참고하세요") == (
        "[단백질 가이드]과 [운동 가이드]를 참고하세요"
    )


def test_internal_source_refs_are_rejected_from_all_visible_fields():
    payload = _diet_payload(source_refs=["S1"])
    payload["suggested_foods"][0]["reason"] = "S2 근거를 사용했습니다."

    with pytest.raises(ValidationError) as captured:
        DietRecommendationV2.model_validate(payload)

    assert "internal source references" in str(captured.value)


@pytest.mark.asyncio
async def test_diet_fail_closed_records_skipped_trace_and_rich_query(
    db_session,
    quota_service,
):
    user = await _create_profile(db_session)
    ai_service = AIService(get_settings())
    ai_service.recommend_diet = AsyncMock()
    rag_service = FakeRAGService([])
    service = RecommendationService(db_session, ai_service, rag_service, quota_service)

    with pytest.raises(AIServiceError) as captured:
        await service.recommend_diet(user.id, date.today())

    assert captured.value.code == "RAG_CONTEXT_UNAVAILABLE"
    assert ai_service.recommend_diet.await_count == 0
    assert "단백질" in rag_service.queries[0]
    assert "유당" in rag_service.queries[0]
    assert "고단백" in rag_service.queries[0]
    trace = (await db_session.execute(select(AIGenerationTrace))).scalar_one()
    assert trace.status == "skipped"
    assert trace.provider_invoked is False
    assert trace.error_stage == "retrieval"


@pytest.mark.asyncio
async def test_exercise_query_includes_goal_muscle_and_recent_history(
    db_session,
    quota_service,
):
    user = await _create_profile(db_session)
    exercise = ExerciseLog(
        user_id=user.id,
        exercise_date=date.today(),
        exercise_name="Bench Press",
        muscle_group=MuscleGroupEnum.CHEST,
    )
    exercise.exercise_sets = [ExerciseSet(set_number=1, reps=8, weight_kg=Decimal("70.0"))]
    db_session.add(exercise)
    await db_session.commit()

    ai_service = AIService(get_settings())
    ai_service.recommend_exercise = AsyncMock()
    rag_service = FakeRAGService([])

    with pytest.raises(AIServiceError):
        await RecommendationService(
            db_session,
            ai_service,
            rag_service,
            quota_service,
        ).recommend_exercise(user.id, "chest")

    query = rag_service.queries[0]
    assert "벌크업" in query
    assert "chest" in query
    assert "Bench Press 1세트" in query


@pytest.mark.asyncio
async def test_chat_query_includes_actual_question_and_fail_closes(
    db_session,
    quota_service,
):
    user = await _create_profile(db_session)
    ai_service = AIService(get_settings())
    ai_service.chat = AsyncMock()
    rag_service = FakeRAGService([])
    question = "오늘 가슴 운동 강도를 어떻게 조절할까?"

    with pytest.raises(AIServiceError) as captured:
        await ChatService(
            db_session,
            ai_service,
            rag_service,
            quota_service,
        ).chat(user.id, question, "exercise")

    assert captured.value.code == "RAG_CONTEXT_UNAVAILABLE"
    assert question in rag_service.queries[0]
    assert ai_service.chat.await_count == 0


@pytest.mark.asyncio
async def test_verified_source_refs_control_public_titles_and_trace_metadata(
    db_session,
    quota_service,
):
    user = await _create_profile(db_session)
    ai_service = AIService(get_settings())
    ai_service.recommend_diet = AsyncMock(
        return_value=AIInvocationResult(
            payload=_diet_payload(source_refs=["S2"]),
            model="gemini-test",
            response_schema_version=DIET_RECOMMEND_SCHEMA_VERSION,
            response_id="verified-response",
            tokens_input=30,
            tokens_output=20,
            finish_reason="STOP",
            latency_ms=50,
            raw_response_hash="b" * 64,
            trace_metadata={"provider_call_count": 2, "schema_repair_count": 1},
        )
    )
    rag_service = FakeRAGService(
        [
            {
                "chunk_id": 11,
                "source_title": "Nutrition A",
                "title": "A1",
                "content": "A evidence",
                "search_backend": "opensearch",
                "search_mode": "hybrid",
                "embedding_latency_ms": 12,
                "backend_search_latency_ms": 8,
                "retrieval_core_latency_ms": 20,
            },
            {"chunk_id": 22, "source_title": "Nutrition B", "title": "B1", "content": "B evidence"},
        ]
    )

    result = await RecommendationService(
        db_session,
        ai_service,
        rag_service,
        quota_service,
    ).recommend_diet(user.id, date.today())

    assert result["sources"] == ["Nutrition B"]
    assert rag_service.used_chunk_ids == [22]
    trace = (await db_session.execute(select(AIGenerationTrace))).scalar_one()
    assert trace.status == "succeeded"
    assert trace.provider_invoked is True
    assert trace.tokens_input == 30
    assert trace.provider_response_id == "verified-response"
    assert trace.trace_metadata["selected_source_refs"] == ["S2"]
    assert trace.trace_metadata["provider_call_count"] == 2
    assert trace.trace_metadata["schema_repair_count"] == 1
    assert trace.trace_metadata["retrieved_document_count"] == 2
    assert trace.trace_metadata["search_backend"] == "opensearch"
    assert trace.trace_metadata["search_mode"] == "hybrid"
    assert trace.trace_metadata["retrieval_embedding_latency_ms"] == 12
    assert trace.trace_metadata["retrieval_backend_search_latency_ms"] == 8
    assert trace.trace_metadata["retrieval_core_latency_ms"] == 20
    assert trace.trace_metadata["retrieval_latency_ms"] >= 0
    assert trace.trace_metadata["generation_call_latency_ms"] >= 0
    assert trace.trace_metadata["pre_persistence_pipeline_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_chat_trace_merges_retrieval_pipeline_and_schema_metrics(
    db_session,
    quota_service,
):
    user = await _create_profile(db_session)
    ai_service = AIService(get_settings())
    ai_service.chat = AsyncMock(
        return_value=AIInvocationResult(
            payload={"answer": "Protein guidance", "source_refs": ["S1"]},
            model="gemini-test",
            response_schema_version=CHAT_SCHEMA_VERSION,
            latency_ms=25,
            trace_metadata={
                "provider_call_count": 2,
                "provider_retry_count": 0,
                "schema_repair_count": 1,
            },
        )
    )
    rag_service = FakeRAGService(
        [
            {
                "chunk_id": 31,
                "source_title": "Protein Guide",
                "title": "Protein",
                "content": "Evidence",
                "search_backend": "opensearch",
                "search_mode": "hybrid",
                "embedding_latency_ms": 10,
                "backend_search_latency_ms": 4,
                "retrieval_core_latency_ms": 14,
            }
        ]
    )

    result = await ChatService(db_session, ai_service, rag_service, quota_service).chat(
        user.id,
        "How much protein?",
        "general",
    )

    assert result["sources"] == ["Protein Guide"]
    recommendation = (
        await db_session.execute(select(AIRecommendation))
    ).scalar_one()
    assert recommendation.context_summary == "general 채팅 요청 (내용 비저장)"
    assert "How much protein?" not in recommendation.context_summary
    trace = (await db_session.execute(select(AIGenerationTrace))).scalar_one()
    assert trace.request_type == "chat"
    assert trace.trace_metadata["selected_source_refs"] == ["S1"]
    assert trace.trace_metadata["provider_call_count"] == 2
    assert trace.trace_metadata["schema_repair_count"] == 1
    assert trace.trace_metadata["retrieved_document_count"] == 1
    assert trace.trace_metadata["retrieval_embedding_latency_ms"] == 10
    assert trace.trace_metadata["retrieval_backend_search_latency_ms"] == 4
    assert trace.trace_metadata["generation_call_latency_ms"] >= 0
    assert trace.trace_metadata["pre_persistence_pipeline_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_provider_failure_is_persisted_as_failed_trace(
    db_session,
    quota_service,
):
    user = await _create_profile(db_session)
    ai_service = AIService(get_settings())
    ai_service.recommend_diet = AsyncMock(
        side_effect=AIServiceError(
            503,
            "AI_TIMEOUT",
            "AI 서비스가 응답하지 않습니다",
            stage="provider_call",
            provider_invoked=True,
            model="gemini-test",
            response_schema_version=DIET_RECOMMEND_SCHEMA_VERSION,
            latency_ms=30000,
            retry_count=1,
        )
    )
    rag_service = FakeRAGService(
        [{"chunk_id": 11, "source_title": "Nutrition A", "title": "A1", "content": "A evidence"}]
    )

    with pytest.raises(AIServiceError):
        await RecommendationService(
            db_session,
            ai_service,
            rag_service,
            quota_service,
        ).recommend_diet(user.id, date.today())

    trace = (await db_session.execute(select(AIGenerationTrace))).scalar_one()
    assert trace.status == "failed"
    assert trace.provider_invoked is True
    assert trace.error_code == "AI_TIMEOUT"
    assert trace.error_stage == "provider_call"
    assert trace.retry_count == 1


@pytest.mark.asyncio
async def test_food_analysis_endpoint_records_provider_trace(
    client,
    db_session,
    register_and_get_token,
    auth_headers,
    monkeypatch,
):
    payload = {
        "foods": [
            {
                "food_name": "연어 샐러드",
                "serving_size": "1접시",
                "calories": 430,
                "protein_g": 35,
                "carbs_g": 25,
                "fat_g": 20,
                "confidence": 0.9,
            }
        ]
    }
    provider_result = _provider_result(payload, response_id="food-trace-response")

    async def fake_provider_call(
        _service,
        _model,
        _contents,
        _config,
        *,
        attempt_recorder=None,
        attempt_kind="initial",
        **_kwargs,
    ):
        assert attempt_recorder is not None
        attempt_id = await attempt_recorder.start_attempt(
            attempt_kind=attempt_kind,
            model="gemini-test",
        )
        await attempt_recorder.complete_attempt(
            attempt_id,
            status="succeeded",
            latency_ms=provider_result.latency_ms,
            tokens_input=provider_result.tokens_input,
            tokens_output=provider_result.tokens_output,
            finish_reason=provider_result.finish_reason,
            provider_response_id=provider_result.response_id,
            raw_response_hash=provider_result.raw_response_hash,
        )
        return provider_result

    monkeypatch.setattr(AIService, "_call_with_retry", fake_provider_call)
    token, user_id = await register_and_get_token(client, "food-trace@example.com")

    response = await client.post(
        "/api/v1/diet/analyze-image",
        files={"image": ("meal.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 64, "image/jpeg")},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    trace = (
        await db_session.execute(
            select(AIGenerationTrace).where(AIGenerationTrace.user_id == user_id)
        )
    ).scalar_one()
    assert trace.request_type == "food_analysis"
    assert trace.status == "succeeded"
    assert trace.provider_invoked is True
    assert trace.provider_response_id == "food-trace-response"
    assert trace.tokens_input == 11
    assert trace.trace_metadata["food_count"] == 1
    assert trace.trace_metadata["image_size_bytes"] == 68
    assert trace.trace_metadata["image_read_latency_ms"] >= 0
    assert trace.trace_metadata["generation_call_latency_ms"] >= 0
    assert trace.trace_metadata["pre_persistence_pipeline_latency_ms"] >= 0
    assert trace.trace_metadata["provider_call_count"] == 1
    assert trace.trace_metadata["schema_repair_count"] == 0
    attempt = (
        await db_session.execute(
            select(AIGenerationAttempt).where(
                AIGenerationAttempt.generation_trace_id == trace.id
            )
        )
    ).scalar_one()
    assert attempt.attempt_kind == "initial"
    assert attempt.status == "succeeded"
    assert attempt.provider_response_id == "food-trace-response"
