from __future__ import annotations

import json
import mimetypes
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

import httpx
from redis.asyncio import Redis
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.models.ai_recommendation import AIRecommendation
from app.models.ai_validation import AIValidationItem, AIValidationRun
from app.models.diet import DietLog
from app.models.exercise import ExerciseLog
from app.models.rag import AIGenerationTrace, RagPipelineDecision, RagRetrievalTrace
from app.models.token import RefreshToken
from app.models.user import User, UserProfile
from app.models.weight_log import WeightLog


VALIDATION_SCHEMA_VERSION = "ui-ai-integration-v1"

CHECK_DEFINITIONS = (
    ("health", "setup"),
    ("account_auth", "setup"),
    ("profile_upsert", "api"),
    ("diet_create_read", "api"),
    ("exercise_create_read", "api"),
    ("dashboard_projection", "api"),
    ("diet_recommendation", "ai"),
    ("exercise_recommendation", "ai"),
    ("ai_chat", "ai"),
    ("food_analysis_save", "ai"),
    ("generation_trace_integrity", "trace"),
    ("retrieval_source_integrity", "trace"),
    ("privacy_invariants", "privacy"),
    ("cleanup", "cleanup"),
)

_SENSITIVE_EVIDENCE_KEYS = {
    "access_token",
    "answer",
    "authorization",
    "email",
    "food_name",
    "message",
    "password",
    "password_confirm",
    "prompt",
    "prompt_used",
    "query",
    "query_text",
    "raw_response",
    "refresh_token",
    "recommendation",
    "token",
}
_EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


class AIValidationError(Exception):
    def __init__(
        self,
        code: str,
        *,
        http_status: int | None = None,
        evidence: dict[str, object] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status
        self.evidence = evidence or {}


@dataclass(frozen=True)
class ValidationOutcome:
    value: object | None = None
    evidence: dict[str, object] | None = None
    http_status: int | None = None


@dataclass(frozen=True)
class CheckExecution:
    passed: bool
    value: object | None = None


@dataclass(frozen=True)
class HTTPResult:
    payload: dict[str, object]
    status_code: int
    latency_ms: int


class AIValidationService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        *,
        redis_client: Redis | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.redis = redis_client
        self.http_client = http_client

    async def validate_integration(
        self,
        *,
        base_url: str,
        image_path: str | Path,
        report_path: str | Path | None = None,
        mode: str = "live_api",
    ) -> dict[str, object]:
        normalized_base_url = base_url.rstrip("/")
        run = AIValidationRun(
            mode=mode,
            status="started",
            base_url=normalized_base_url,
            expected_checks=len(CHECK_DEFINITIONS),
            cleanup_status="pending",
            report_path=str(report_path) if report_path else None,
            summary={"schema_version": VALIDATION_SCHEMA_VERSION},
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        state: dict[str, object] = {
            "diet_log_ids": [],
            "exercise_log_ids": [],
        }
        owns_client = self.http_client is None
        client = self.http_client or httpx.AsyncClient(
            base_url=normalized_base_url + "/",
            timeout=httpx.Timeout(self.settings.AI_VALIDATION_TIMEOUT_SECONDS),
            follow_redirects=True,
        )

        try:
            health = await self._execute_check(
                run,
                "health",
                "setup",
                lambda: self._check_health(client),
            )
            account = await self._execute_check(
                run,
                "account_auth",
                "setup",
                lambda: self._check_account_auth(client, run),
            )
            if account.passed and isinstance(account.value, dict):
                state.update(account.value)
                run.validation_user_id = int(state["user_id"])
                await self.db.commit()

            if not health.passed or not account.passed:
                await self._skip_dependent_checks(run, reason_code="SETUP_PREREQUISITE_FAILED")
            else:
                await self._run_api_and_ai_checks(
                    run,
                    client,
                    state,
                    Path(image_path),
                )
        except Exception as exc:
            run.summary = {
                **dict(run.summary or {}),
                "orchestrator_error": type(exc).__name__,
            }
            await self.db.commit()
            await self._skip_dependent_checks(run, reason_code="ORCHESTRATOR_INTERRUPTED")
        finally:
            await self._run_cleanup_check(run, client, state)
            if owns_client:
                await client.aclose()

        await self._finalize_run(run)
        if report_path:
            try:
                await self.write_report(run.run_id, report_path)
            except Exception as exc:
                run.summary = {
                    **dict(run.summary or {}),
                    "report_error": type(exc).__name__,
                }
                if run.status == "succeeded":
                    run.status = "partial"
                await self.db.commit()

        return await self.get_run(run.run_id)

    async def _run_api_and_ai_checks(
        self,
        run: AIValidationRun,
        client: httpx.AsyncClient,
        state: dict[str, object],
        image_path: Path,
    ) -> None:
        token = str(state["access_token"])
        user_id = int(state["user_id"])

        await self._execute_check(
            run,
            "profile_upsert",
            "api",
            lambda: self._check_profile(client, token),
        )
        diet = await self._execute_check(
            run,
            "diet_create_read",
            "api",
            lambda: self._check_diet_create_read(client, token),
        )
        if diet.passed and isinstance(diet.value, int):
            cast_ids = state["diet_log_ids"]
            assert isinstance(cast_ids, list)
            cast_ids.append(diet.value)

        exercise = await self._execute_check(
            run,
            "exercise_create_read",
            "api",
            lambda: self._check_exercise_create_read(client, token),
        )
        if exercise.passed and isinstance(exercise.value, int):
            cast_ids = state["exercise_log_ids"]
            assert isinstance(cast_ids, list)
            cast_ids.append(exercise.value)

        await self._execute_check(
            run,
            "dashboard_projection",
            "api",
            lambda: self._check_dashboard(client, token),
        )
        await self._execute_check(
            run,
            "diet_recommendation",
            "ai",
            lambda: self._check_diet_recommendation(client, token),
        )
        await self._execute_check(
            run,
            "exercise_recommendation",
            "ai",
            lambda: self._check_exercise_recommendation(client, token),
        )
        chat_message = "오늘 기록을 고려해 안전하게 개선할 한 가지를 알려줘."
        state["chat_message"] = chat_message
        await self._execute_check(
            run,
            "ai_chat",
            "ai",
            lambda: self._check_chat(client, token, chat_message),
        )
        food = await self._execute_check(
            run,
            "food_analysis_save",
            "ai",
            lambda: self._check_food_analysis_save(client, token, image_path),
        )
        if food.passed and isinstance(food.value, int):
            cast_ids = state["diet_log_ids"]
            assert isinstance(cast_ids, list)
            cast_ids.append(food.value)

        await self._execute_check(
            run,
            "generation_trace_integrity",
            "trace",
            lambda: self._check_generation_trace_integrity(run, user_id),
        )
        await self._execute_check(
            run,
            "retrieval_source_integrity",
            "trace",
            lambda: self._check_retrieval_source_integrity(run, user_id),
        )
        await self._execute_check(
            run,
            "privacy_invariants",
            "privacy",
            lambda: self._check_privacy_invariants(
                run,
                user_id,
                chat_message,
            ),
        )

    async def _check_health(self, client: httpx.AsyncClient) -> ValidationOutcome:
        result = await self._request_json(client, "GET", "health", expected_status=200)
        status_value = str(result.payload.get("status", ""))
        if status_value != "ok":
            raise AIValidationError(
                "HEALTH_NOT_READY",
                http_status=result.status_code,
                evidence={"service_status": status_value or "missing"},
            )
        return ValidationOutcome(
            evidence={
                "service_status": status_value,
                "database": result.payload.get("db"),
                "redis": result.payload.get("redis"),
            },
            http_status=result.status_code,
        )

    async def _check_account_auth(
        self,
        client: httpx.AsyncClient,
        run: AIValidationRun,
    ) -> ValidationOutcome:
        suffix = uuid4().hex
        email = f"ui-e2e-{suffix}@example.com"
        password = f"E2e!{suffix}Aa1"
        register = await self._request_json(
            client,
            "POST",
            "auth/register",
            expected_status=201,
            json={
                "email": email,
                "password": password,
                "password_confirm": password,
            },
        )
        register_data = self._response_data(register.payload)
        user_payload = register_data.get("user")
        if not isinstance(user_payload, dict) or not isinstance(user_payload.get("id"), int):
            user_id = await self.db.scalar(select(User.id).where(User.email == email))
            if user_id is not None:
                run.validation_user_id = int(user_id)
                await self.db.commit()
            raise AIValidationError("AUTH_REGISTER_RESPONSE_INVALID", http_status=register.status_code)
        run.validation_user_id = int(user_payload["id"])
        await self.db.commit()

        login = await self._request_json(
            client,
            "POST",
            "auth/login",
            expected_status=200,
            json={"email": email, "password": password},
        )
        login_data = self._response_data(login.payload)
        access_token = login_data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise AIValidationError("AUTH_LOGIN_RESPONSE_INVALID", http_status=login.status_code)

        return ValidationOutcome(
            value={
                "user_id": int(user_payload["id"]),
                "access_token": access_token,
            },
            evidence={
                "account_created": True,
                "login_verified": True,
            },
            http_status=login.status_code,
        )

    async def _check_profile(self, client: httpx.AsyncClient, token: str) -> ValidationOutcome:
        result = await self._request_json(
            client,
            "PUT",
            "profile",
            expected_status=200,
            headers=self._auth_headers(token),
            json={
                "height_cm": 175,
                "weight_kg": 78.4,
                "age": 32,
                "gender": "male",
                "goal": "bulk",
                "activity_level": "active",
                "allergies": ["lactose sensitivity"],
                "food_preferences": ["high protein", "Mediterranean"],
            },
        )
        data = self._response_data(result.payload)
        if float(data.get("weight_kg", 0)) != 78.4 or data.get("goal") != "bulk":
            raise AIValidationError("PROFILE_PROJECTION_MISMATCH", http_status=result.status_code)
        return ValidationOutcome(
            evidence={
                "profile_saved": True,
                "targets_calculated": data.get("target_calories") is not None,
            },
            http_status=result.status_code,
        )

    async def _check_diet_create_read(
        self,
        client: httpx.AsyncClient,
        token: str,
    ) -> ValidationOutcome:
        today = date.today().isoformat()
        create = await self._request_json(
            client,
            "POST",
            "diet/logs",
            expected_status=201,
            headers=self._auth_headers(token),
            json={
                "log_date": today,
                "meal_type": "lunch",
                "items": [
                    {
                        "food_name": "[UI-E2E] balanced lunch",
                        "serving_size": "1 serving",
                        "calories": 620,
                        "protein_g": 45,
                        "carbs_g": 68,
                        "fat_g": 18,
                    }
                ],
            },
        )
        created = self._response_data(create.payload)
        log_id = created.get("id")
        if not isinstance(log_id, int):
            raise AIValidationError("DIET_CREATE_RESPONSE_INVALID", http_status=create.status_code)

        read = await self._request_json(
            client,
            "GET",
            "diet/logs",
            expected_status=200,
            headers=self._auth_headers(token),
            params={"date": today},
        )
        data = self._response_data(read.payload)
        meals = data.get("meals")
        found = isinstance(meals, dict) and any(
            isinstance(logs, list) and any(
                isinstance(log, dict) and log.get("id") == log_id
                for log in logs
            )
            for logs in meals.values()
        )
        if not found:
            raise AIValidationError("DIET_READ_AFTER_WRITE_FAILED", http_status=read.status_code)
        return ValidationOutcome(
            value=log_id,
            evidence={"created_count": 1, "read_after_write": True},
            http_status=create.status_code,
        )

    async def _check_exercise_create_read(
        self,
        client: httpx.AsyncClient,
        token: str,
    ) -> ValidationOutcome:
        today = date.today().isoformat()
        create = await self._request_json(
            client,
            "POST",
            "exercise/logs",
            expected_status=201,
            headers=self._auth_headers(token),
            json={
                "exercise_date": today,
                "exercise_name": "[UI-E2E] back squat",
                "muscle_group": "legs",
                "duration_min": 45,
                "memo": "[UI-E2E] validation record",
                "sets": [
                    {"set_number": 1, "reps": 8, "weight_kg": 60},
                    {"set_number": 2, "reps": 8, "weight_kg": 60},
                ],
            },
        )
        created = self._response_data(create.payload)
        log_id = created.get("id")
        if not isinstance(log_id, int):
            raise AIValidationError("EXERCISE_CREATE_RESPONSE_INVALID", http_status=create.status_code)

        read = await self._request_json(
            client,
            "GET",
            "exercise/logs",
            expected_status=200,
            headers=self._auth_headers(token),
            params={"date": today},
        )
        data = self._response_data(read.payload)
        exercises = data.get("exercises")
        if not isinstance(exercises, list) or not any(
            isinstance(log, dict) and log.get("id") == log_id
            for log in exercises
        ):
            raise AIValidationError("EXERCISE_READ_AFTER_WRITE_FAILED", http_status=read.status_code)
        return ValidationOutcome(
            value=log_id,
            evidence={"created_count": 1, "read_after_write": True, "set_count": 2},
            http_status=create.status_code,
        )

    async def _check_dashboard(self, client: httpx.AsyncClient, token: str) -> ValidationOutcome:
        result = await self._request_json(
            client,
            "GET",
            "dashboard/today",
            expected_status=200,
            headers=self._auth_headers(token),
        )
        data = self._response_data(result.payload)
        nutrition = data.get("nutrition")
        exercise = data.get("exercise")
        consumed = nutrition.get("consumed") if isinstance(nutrition, dict) else None
        calories = consumed.get("calories") if isinstance(consumed, dict) else None
        exercise_count = exercise.get("exercises_count") if isinstance(exercise, dict) else None
        if not isinstance(calories, (int, float)) or calories <= 0:
            raise AIValidationError("DASHBOARD_DIET_PROJECTION_MISSING", http_status=result.status_code)
        if not isinstance(exercise_count, int) or exercise_count <= 0:
            raise AIValidationError("DASHBOARD_EXERCISE_PROJECTION_MISSING", http_status=result.status_code)
        return ValidationOutcome(
            evidence={
                "nutrition_projected": True,
                "exercise_projected": True,
                "exercise_count": exercise_count,
            },
            http_status=result.status_code,
        )

    async def _check_diet_recommendation(
        self,
        client: httpx.AsyncClient,
        token: str,
    ) -> ValidationOutcome:
        result = await self._request_json(
            client,
            "GET",
            "diet/recommend",
            expected_status=200,
            headers=self._auth_headers(token),
        )
        data = self._response_data(result.payload)
        sources = data.get("sources")
        suggestions = data.get("suggested_foods")
        if not isinstance(sources, list) or not sources:
            raise AIValidationError("DIET_RECOMMENDATION_SOURCE_MISSING", http_status=result.status_code)
        if not isinstance(suggestions, list) or not suggestions:
            raise AIValidationError("DIET_RECOMMENDATION_EMPTY", http_status=result.status_code)
        return ValidationOutcome(
            evidence={"source_count": len(sources), "suggestion_count": len(suggestions)},
            http_status=result.status_code,
        )

    async def _check_exercise_recommendation(
        self,
        client: httpx.AsyncClient,
        token: str,
    ) -> ValidationOutcome:
        result = await self._request_json(
            client,
            "GET",
            "exercise/recommend",
            expected_status=200,
            headers=self._auth_headers(token),
            params={"muscle_group": "legs"},
        )
        data = self._response_data(result.payload)
        sources = data.get("sources")
        suggestions = data.get("suggested_exercises")
        if not isinstance(sources, list) or not sources:
            raise AIValidationError("EXERCISE_RECOMMENDATION_SOURCE_MISSING", http_status=result.status_code)
        if not isinstance(suggestions, list) or not suggestions:
            raise AIValidationError("EXERCISE_RECOMMENDATION_EMPTY", http_status=result.status_code)
        return ValidationOutcome(
            evidence={"source_count": len(sources), "suggestion_count": len(suggestions)},
            http_status=result.status_code,
        )

    async def _check_chat(
        self,
        client: httpx.AsyncClient,
        token: str,
        message: str,
    ) -> ValidationOutcome:
        result = await self._request_json(
            client,
            "POST",
            "ai/chat",
            expected_status=200,
            headers=self._auth_headers(token),
            json={"message": message, "context_type": "general"},
        )
        data = self._response_data(result.payload)
        answer = data.get("answer")
        sources = data.get("sources")
        if not isinstance(answer, str) or not answer.strip():
            raise AIValidationError("CHAT_ANSWER_EMPTY", http_status=result.status_code)
        if not isinstance(sources, list) or not sources:
            raise AIValidationError("CHAT_SOURCE_MISSING", http_status=result.status_code)
        return ValidationOutcome(
            evidence={"source_count": len(sources), "answer_present": True},
            http_status=result.status_code,
        )

    async def _check_food_analysis_save(
        self,
        client: httpx.AsyncClient,
        token: str,
        image_path: Path,
    ) -> ValidationOutcome:
        if not image_path.is_file():
            raise AIValidationError("VALIDATION_IMAGE_NOT_FOUND")
        image_bytes = image_path.read_bytes()
        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        if mime_type not in {"image/jpeg", "image/png"}:
            raise AIValidationError("VALIDATION_IMAGE_TYPE_UNSUPPORTED")

        analyzed = await self._request_json(
            client,
            "POST",
            "diet/analyze-image",
            expected_status=200,
            headers=self._auth_headers(token),
            files={"image": (image_path.name, image_bytes, mime_type)},
            data={"meal_type": "snack"},
        )
        analyzed_data = self._response_data(analyzed.payload)
        foods = analyzed_data.get("foods")
        if not isinstance(foods, list) or not foods or not isinstance(foods[0], dict):
            raise AIValidationError("FOOD_ANALYSIS_EMPTY", http_status=analyzed.status_code)
        first_food = foods[0]

        save = await self._request_json(
            client,
            "POST",
            "diet/logs",
            expected_status=201,
            headers=self._auth_headers(token),
            json={
                "log_date": date.today().isoformat(),
                "meal_type": "snack",
                "items": [
                    {
                        "food_name": str(first_food.get("food_name") or "[UI-E2E] analyzed food"),
                        "serving_size": first_food.get("serving_size"),
                        "calories": float(first_food.get("calories", 0)),
                        "protein_g": float(first_food.get("protein_g", 0)),
                        "carbs_g": float(first_food.get("carbs_g", 0)),
                        "fat_g": float(first_food.get("fat_g", 0)),
                        "confidence": float(first_food.get("confidence", 0)),
                    }
                ],
            },
        )
        saved_data = self._response_data(save.payload)
        saved_log_id = saved_data.get("id")
        if not isinstance(saved_log_id, int):
            raise AIValidationError("FOOD_ANALYSIS_SAVE_FAILED", http_status=save.status_code)
        return ValidationOutcome(
            value=saved_log_id,
            evidence={
                "image_bytes": len(image_bytes),
                "recognized_count": len(foods),
                "selected_items_saved": 1,
            },
            http_status=analyzed.status_code,
        )

    async def _check_generation_trace_integrity(
        self,
        run: AIValidationRun,
        user_id: int,
    ) -> ValidationOutcome:
        traces = list(
            (
                await self.db.execute(
                    select(AIGenerationTrace)
                    .options(selectinload(AIGenerationTrace.attempts))
                    .where(
                        AIGenerationTrace.user_id == user_id,
                        AIGenerationTrace.created_at >= run.started_at,
                    )
                    .order_by(AIGenerationTrace.id)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        expected_types = {"diet", "exercise", "chat", "food_analysis"}
        observed_types = {trace.request_type for trace in traces}
        invalid = [
            trace
            for trace in traces
            if trace.status != "succeeded"
            or not trace.provider_invoked
            or trace.quota_status != "consumed"
            or not trace.response_schema_version
            or not trace.provider_response_id
            or not trace.raw_response_hash
            or trace.tokens_input is None
            or trace.tokens_output is None
            or not trace.attempts
            or not any(attempt.status == "succeeded" for attempt in trace.attempts)
            or any(attempt.status in {"started", "abandoned"} for attempt in trace.attempts)
        ]
        if not expected_types.issubset(observed_types) or invalid:
            raise AIValidationError(
                "GENERATION_TRACE_INTEGRITY_FAILED",
                evidence={
                    "trace_count": len(traces),
                    "request_types": sorted(observed_types),
                    "invalid_trace_count": len(invalid),
                },
            )
        return ValidationOutcome(
            evidence={
                "trace_count": len(traces),
                "attempt_count": sum(len(trace.attempts) for trace in traces),
                "request_types": sorted(observed_types),
                "request_ids": [str(trace.request_id) for trace in traces],
                "models": sorted({str(trace.model_used) for trace in traces}),
                "tokens_input_total": sum(int(trace.tokens_input or 0) for trace in traces),
                "tokens_output_total": sum(int(trace.tokens_output or 0) for trace in traces),
                "provider_latency_max_ms": max(int(trace.latency_ms or 0) for trace in traces),
            }
        )

    async def _check_retrieval_source_integrity(
        self,
        run: AIValidationRun,
        user_id: int,
    ) -> ValidationOutcome:
        generation_traces = list(
            (
                await self.db.execute(
                    select(AIGenerationTrace).where(
                        AIGenerationTrace.user_id == user_id,
                        AIGenerationTrace.created_at >= run.started_at,
                        AIGenerationTrace.request_type.in_(["diet", "exercise", "chat"]),
                    )
                )
            ).scalars()
        )
        groups = [
            trace.rag_trace_group_id
            for trace in generation_traces
            if trace.rag_trace_group_id
        ]
        rows = list(
            (
                await self.db.execute(
                    select(RagRetrievalTrace).where(
                        RagRetrievalTrace.rag_trace_group_id.in_(groups)
                    )
                )
            ).scalars()
        ) if groups else []
        response_rows = [row for row in rows if row.used_in_response]
        observed_groups = {row.rag_trace_group_id for row in rows}
        if len(groups) != 3 or set(groups) != observed_groups:
            raise AIValidationError(
                "RETRIEVAL_TRACE_GROUP_MISSING",
                evidence={"expected_group_count": len(groups), "observed_group_count": len(observed_groups)},
            )
        if not response_rows or any(row.source_id is None or row.chunk_id is None for row in response_rows):
            raise AIValidationError(
                "RETRIEVAL_FINAL_SOURCE_INVALID",
                evidence={"retrieval_rows": len(rows), "response_rows": len(response_rows)},
            )
        return ValidationOutcome(
            evidence={
                "trace_group_count": len(observed_groups),
                "retrieval_rows": len(rows),
                "prompt_rows": sum(1 for row in rows if row.used_in_prompt),
                "response_rows": len(response_rows),
                "source_count": len({row.source_id for row in response_rows}),
                "search_backends": sorted({row.search_backend for row in rows}),
            }
        )

    async def _check_privacy_invariants(
        self,
        run: AIValidationRun,
        user_id: int,
        chat_message: str,
    ) -> ValidationOutcome:
        groups = list(
            (
                await self.db.execute(
                    select(AIGenerationTrace.rag_trace_group_id).where(
                        AIGenerationTrace.user_id == user_id,
                        AIGenerationTrace.created_at >= run.started_at,
                        AIGenerationTrace.rag_trace_group_id.is_not(None),
                    )
                )
            ).scalars()
        )
        rows = list(
            (
                await self.db.execute(
                    select(RagRetrievalTrace).where(
                        RagRetrievalTrace.rag_trace_group_id.in_(groups)
                    )
                )
            ).scalars()
        ) if groups else []
        recommendations = list(
            (
                await self.db.execute(
                    select(AIRecommendation).where(
                        AIRecommendation.user_id == user_id,
                        AIRecommendation.created_at >= run.started_at,
                    )
                )
            ).scalars()
        )
        raw_query_rows = sum(1 for row in rows if row.query_text is not None)
        invalid_hash_rows = sum(1 for row in rows if len(row.query_hash or "") != 64)
        raw_prompt_rows = sum(1 for row in recommendations if row.prompt_used is not None)
        raw_chat_rows = sum(
            1
            for row in recommendations
            if row.context_summary and chat_message in row.context_summary
        )
        raw_decision_context_rows = int(
            await self.db.scalar(
                select(func.count(RagPipelineDecision.id)).where(
                    RagPipelineDecision.context.has_key("query")  # type: ignore[attr-defined]
                )
            )
            or 0
        )
        if (
            raw_query_rows
            or invalid_hash_rows
            or raw_prompt_rows
            or raw_chat_rows
            or raw_decision_context_rows
        ):
            raise AIValidationError(
                "PRIVACY_INVARIANT_FAILED",
                evidence={
                    "raw_query_rows": raw_query_rows,
                    "invalid_hash_rows": invalid_hash_rows,
                    "raw_prompt_rows": raw_prompt_rows,
                    "raw_chat_rows": raw_chat_rows,
                    "raw_decision_context_rows": raw_decision_context_rows,
                },
            )
        return ValidationOutcome(
            evidence={
                "retrieval_rows_checked": len(rows),
                "recommendation_rows_checked": len(recommendations),
                "raw_query_rows": 0,
                "invalid_hash_rows": 0,
                "raw_prompt_rows": 0,
                "raw_chat_rows": 0,
                "raw_decision_context_rows": 0,
                "query_policy_versions": sorted({row.query_policy_version for row in rows}),
                "query_key_versions": sorted({row.query_key_version for row in rows}),
            }
        )

    async def _run_cleanup_check(
        self,
        run: AIValidationRun,
        client: httpx.AsyncClient,
        state: dict[str, object],
    ) -> None:
        existing = await self._get_item(run.id, "cleanup")
        if existing is not None and existing.status in {"passed", "failed"}:
            return

        async def cleanup() -> ValidationOutcome:
            user_id = run.validation_user_id
            if user_id is None:
                run.cleanup_status = "not_required"
                await self.db.commit()
                return ValidationOutcome(evidence={"cleanup_required": False})

            api_delete_failures = 0
            token = state.get("access_token")
            if isinstance(token, str):
                for log_id in state.get("diet_log_ids", []):
                    try:
                        response = await client.delete(
                            f"diet/logs/{int(log_id)}",
                            headers=self._auth_headers(token),
                        )
                    except httpx.HTTPError:
                        api_delete_failures += 1
                    else:
                        if response.status_code != 200:
                            api_delete_failures += 1
                for log_id in state.get("exercise_log_ids", []):
                    try:
                        response = await client.delete(
                            f"exercise/logs/{int(log_id)}",
                            headers=self._auth_headers(token),
                        )
                    except httpx.HTTPError:
                        api_delete_failures += 1
                    else:
                        if response.status_code != 200:
                            api_delete_failures += 1

            cleanup_evidence = await self._cleanup_validation_user(user_id)
            run.cleanup_status = "succeeded" if api_delete_failures == 0 else "failed"
            await self.db.commit()
            if api_delete_failures:
                raise AIValidationError(
                    "API_DELETE_VERIFICATION_FAILED",
                    evidence={
                        **cleanup_evidence,
                        "api_delete_failures": api_delete_failures,
                    },
                )
            return ValidationOutcome(
                evidence={
                    **cleanup_evidence,
                    "api_delete_failures": 0,
                }
            )

        execution = await self._execute_check(run, "cleanup", "cleanup", cleanup)
        if not execution.passed and run.cleanup_status == "pending":
            run.cleanup_status = "failed"
            await self.db.commit()

    async def _cleanup_validation_user(self, user_id: int) -> dict[str, object]:
        tables = (
            (RefreshToken, RefreshToken.user_id),
            (WeightLog, WeightLog.user_id),
            (DietLog, DietLog.user_id),
            (ExerciseLog, ExerciseLog.user_id),
            (AIRecommendation, AIRecommendation.user_id),
            (UserProfile, UserProfile.user_id),
        )
        deleted_rows: dict[str, int] = {}
        try:
            for model, user_column in tables:
                result = await self.db.execute(
                    delete(model).where(user_column == user_id)
                )
                deleted_rows[model.__tablename__] = int(result.rowcount or 0)
            user_result = await self.db.execute(delete(User).where(User.id == user_id))
            deleted_rows[User.__tablename__] = int(user_result.rowcount or 0)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        remaining_user = int(
            await self.db.scalar(select(func.count(User.id)).where(User.id == user_id))
            or 0
        )
        linked_generation_rows = int(
            await self.db.scalar(
                select(func.count(AIGenerationTrace.id)).where(
                    AIGenerationTrace.user_id == user_id
                )
            )
            or 0
        )
        linked_retrieval_rows = int(
            await self.db.scalar(
                select(func.count(RagRetrievalTrace.id)).where(
                    RagRetrievalTrace.user_id == user_id
                )
            )
            or 0
        )
        if remaining_user or linked_generation_rows or linked_retrieval_rows:
            raise AIValidationError("VALIDATION_CLEANUP_INCOMPLETE")

        quota_keys_deleted = 0
        if self.redis is not None:
            pattern = f"{self.settings.AI_QUOTA_KEY_PREFIX.rstrip(':')}:{{{user_id}:*}}:*"
            keys = [key async for key in self.redis.scan_iter(match=pattern, count=100)]
            if keys:
                quota_keys_deleted = int(await self.redis.delete(*keys))

        return {
            "database_rows_deleted": sum(deleted_rows.values()),
            "quota_keys_deleted": quota_keys_deleted,
            "validation_user_removed": True,
            "generation_traces_anonymized": linked_generation_rows == 0,
            "retrieval_traces_anonymized": linked_retrieval_rows == 0,
        }

    async def cleanup_validation_run(self, run_id: UUID | str) -> dict[str, object]:
        run = await self._load_run(run_id)
        if run is None:
            raise AIValidationError("VALIDATION_RUN_NOT_FOUND")
        if run.validation_user_id is not None:
            try:
                evidence = await self._cleanup_validation_user(run.validation_user_id)
            except Exception:
                run.cleanup_status = "failed"
                await self.db.commit()
                raise
        else:
            evidence = {"cleanup_required": False}
            run.cleanup_status = "not_required"

        item = await self._get_item(run.id, "cleanup")
        now = datetime.now(timezone.utc)
        if item is None:
            item = AIValidationItem(
                validation_run_id=run.id,
                check_name="cleanup",
                category="cleanup",
                status="passed",
                evidence=self._safe_evidence(evidence),
                started_at=now,
                finished_at=now,
            )
            self.db.add(item)
        else:
            item.status = "passed"
            item.error_code = None
            item.evidence = self._safe_evidence(evidence)
            item.finished_at = now
        if run.status == "started":
            run.status = "abandoned"
            run.finished_at = now
        await self.db.commit()
        await self._refresh_run_counts(run)
        if run.report_path:
            await self.write_report(run.run_id, run.report_path)
        return await self.get_run(run.run_id)

    async def _execute_check(
        self,
        run: AIValidationRun,
        check_name: str,
        category: str,
        callback: Callable[[], Awaitable[ValidationOutcome]],
    ) -> CheckExecution:
        item = await self._get_item(run.id, check_name)
        if item is None:
            item = AIValidationItem(
                validation_run_id=run.id,
                check_name=check_name,
                category=category,
                required=True,
                status="started",
                evidence={},
            )
            self.db.add(item)
        else:
            item.status = "started"
            item.error_code = None
            item.evidence = {}
            item.started_at = datetime.now(timezone.utc)
            item.finished_at = None
        await self.db.commit()

        started = time.perf_counter()
        try:
            outcome = await callback()
        except AIValidationError as exc:
            item.status = "failed"
            item.http_status = exc.http_status
            item.error_code = exc.code
            item.evidence = self._safe_evidence(exc.evidence)
            item.latency_ms = int((time.perf_counter() - started) * 1000)
            item.finished_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self._refresh_run_counts(run)
            return CheckExecution(passed=False)
        except Exception as exc:
            item.status = "failed"
            item.error_code = "UNEXPECTED_VALIDATION_ERROR"
            item.evidence = {"failure_type": type(exc).__name__}
            item.latency_ms = int((time.perf_counter() - started) * 1000)
            item.finished_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self._refresh_run_counts(run)
            return CheckExecution(passed=False)

        item.status = "passed"
        item.http_status = outcome.http_status
        item.error_code = None
        item.evidence = self._safe_evidence(outcome.evidence or {})
        item.latency_ms = int((time.perf_counter() - started) * 1000)
        item.finished_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self._refresh_run_counts(run)
        return CheckExecution(passed=True, value=outcome.value)

    async def _skip_dependent_checks(
        self,
        run: AIValidationRun,
        *,
        reason_code: str,
    ) -> None:
        for check_name, category in CHECK_DEFINITIONS:
            if check_name in {"health", "account_auth", "cleanup"}:
                continue
            if await self._get_item(run.id, check_name) is not None:
                continue
            now = datetime.now(timezone.utc)
            self.db.add(
                AIValidationItem(
                    validation_run_id=run.id,
                    check_name=check_name,
                    category=category,
                    required=True,
                    status="skipped",
                    error_code=reason_code,
                    evidence={"dependency_failed": True},
                    started_at=now,
                    finished_at=now,
                )
            )
        await self.db.commit()
        await self._refresh_run_counts(run)

    async def _refresh_run_counts(self, run: AIValidationRun) -> None:
        rows = (
            await self.db.execute(
                select(AIValidationItem.status, func.count(AIValidationItem.id))
                .where(AIValidationItem.validation_run_id == run.id)
                .group_by(AIValidationItem.status)
            )
        ).all()
        counts = {str(status): int(count) for status, count in rows}
        run.passed_checks = counts.get("passed", 0)
        run.failed_checks = counts.get("failed", 0)
        run.skipped_checks = counts.get("skipped", 0)
        await self.db.commit()

    async def _finalize_run(self, run: AIValidationRun) -> None:
        await self._refresh_run_counts(run)
        completed = run.passed_checks + run.failed_checks + run.skipped_checks
        if run.failed_checks == 0 and run.skipped_checks == 0 and completed == run.expected_checks:
            run.status = "succeeded"
        elif run.passed_checks == 0:
            run.status = "failed"
        else:
            run.status = "partial"
        run.finished_at = datetime.now(timezone.utc)
        run.summary = {
            **dict(run.summary or {}),
            "checks_completed": completed,
            "all_required_passed": run.status == "succeeded",
            "cleanup_status": run.cleanup_status,
            "raw_user_content_persisted": False,
        }
        await self.db.commit()

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        *,
        expected_status: int,
        **kwargs: object,
    ) -> HTTPResult:
        started = time.perf_counter()
        try:
            response = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise AIValidationError("API_TIMEOUT") from exc
        except httpx.HTTPError as exc:
            raise AIValidationError("API_CONNECTION_FAILED") from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            payload = response.json()
        except ValueError as exc:
            raise AIValidationError(
                "API_RESPONSE_NOT_JSON",
                http_status=response.status_code,
            ) from exc
        if not isinstance(payload, dict):
            raise AIValidationError(
                "API_RESPONSE_INVALID",
                http_status=response.status_code,
            )
        if response.status_code != expected_status:
            error = payload.get("error")
            api_code = error.get("code") if isinstance(error, dict) else None
            raise AIValidationError(
                str(api_code or "API_STATUS_UNEXPECTED"),
                http_status=response.status_code,
                evidence={"expected_http_status": expected_status},
            )
        return HTTPResult(payload=payload, status_code=response.status_code, latency_ms=latency_ms)

    async def list_runs(self, *, limit: int = 20) -> list[dict[str, object]]:
        runs = list(
            (
                await self.db.execute(
                    select(AIValidationRun)
                    .options(selectinload(AIValidationRun.items))
                    .order_by(AIValidationRun.id.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return [self._serialize_run(run, include_items=False) for run in runs]

    async def get_run(self, run_id: UUID | str) -> dict[str, object]:
        run = await self._load_run(run_id)
        if run is None:
            raise AIValidationError("VALIDATION_RUN_NOT_FOUND")
        return self._serialize_run(run, include_items=True)

    async def write_report(
        self,
        run_id: UUID | str,
        report_path: str | Path,
    ) -> Path:
        run = await self._load_run(run_id)
        if run is None:
            raise AIValidationError("VALIDATION_RUN_NOT_FOUND")
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# UI / AI Integration Validation Report",
            "",
            f"> Run ID: `{run.run_id}`  ",
            f"> Mode: `{run.mode}`  ",
            f"> Status: `{run.status}`  ",
            f"> Started: `{run.started_at.isoformat()}`  ",
            f"> Finished: `{run.finished_at.isoformat() if run.finished_at else 'in progress'}`",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Expected checks | {run.expected_checks} |",
            f"| Passed | {run.passed_checks} |",
            f"| Failed | {run.failed_checks} |",
            f"| Skipped | {run.skipped_checks} |",
            f"| Cleanup | `{run.cleanup_status}` |",
            "",
            "## Check Results",
            "",
            "| Check | Category | Status | HTTP | Latency | Error |",
            "|---|---|---|---:|---:|---|",
        ]
        for item in run.items:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{item.check_name}`",
                        item.category,
                        f"`{item.status}`",
                        str(item.http_status or "-"),
                        f"{item.latency_ms or 0}ms",
                        f"`{item.error_code}`" if item.error_code else "-",
                    ]
                )
                + " |"
            )

        lines.extend(["", "## Evidence", ""])
        for item in run.items:
            evidence_json = json.dumps(
                self._safe_evidence(item.evidence or {}),
                ensure_ascii=False,
                sort_keys=True,
                default=self._json_default,
            )
            lines.append(f"- `{item.check_name}`: `{evidence_json}`")

        lines.extend(
            [
                "",
                "## Privacy And Cleanup Boundary",
                "",
                "- Credentials, authorization tokens, prompts, user questions, provider responses, and food names are not stored.",
                "- Validation diet, exercise, profile, token, recommendation, and user rows are removed after the run.",
                "- Generation and retrieval traces remain only as anonymized operational evidence after their user foreign keys are cleared.",
                "- Retrieval query text remains null; only keyed fingerprints and bounded summaries are retained.",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        run.report_path = str(path)
        await self.db.commit()
        return path

    async def _load_run(self, run_id: UUID | str) -> AIValidationRun | None:
        parsed_id = run_id if isinstance(run_id, UUID) else UUID(str(run_id))
        result = await self.db.execute(
            select(AIValidationRun)
            .options(selectinload(AIValidationRun.items))
            .where(AIValidationRun.run_id == parsed_id)
        )
        return result.scalar_one_or_none()

    async def _get_item(self, run_id: int, check_name: str) -> AIValidationItem | None:
        result = await self.db.execute(
            select(AIValidationItem).where(
                AIValidationItem.validation_run_id == run_id,
                AIValidationItem.check_name == check_name,
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    def _serialize_run(
        cls,
        run: AIValidationRun,
        *,
        include_items: bool,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "run_id": str(run.run_id),
            "mode": run.mode,
            "status": run.status,
            "base_url": run.base_url,
            "expected_checks": run.expected_checks,
            "passed_checks": run.passed_checks,
            "failed_checks": run.failed_checks,
            "skipped_checks": run.skipped_checks,
            "cleanup_status": run.cleanup_status,
            "report_path": run.report_path,
            "summary": cls._safe_evidence(run.summary or {}),
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        }
        if include_items:
            payload["items"] = [
                {
                    "check_name": item.check_name,
                    "category": item.category,
                    "required": item.required,
                    "status": item.status,
                    "latency_ms": item.latency_ms,
                    "http_status": item.http_status,
                    "error_code": item.error_code,
                    "evidence": cls._safe_evidence(item.evidence or {}),
                    "started_at": item.started_at,
                    "finished_at": item.finished_at,
                }
                for item in run.items
            ]
        return payload

    @classmethod
    def _safe_evidence(cls, value: object) -> Any:
        if isinstance(value, dict):
            return {
                str(key): cls._safe_evidence(item)
                for key, item in value.items()
                if str(key).lower() not in _SENSITIVE_EVIDENCE_KEYS
            }
        if isinstance(value, (list, tuple, set)):
            return [cls._safe_evidence(item) for item in value]
        if isinstance(value, str):
            if _EMAIL_PATTERN.search(value) or _JWT_PATTERN.search(value) or value.startswith("Bearer "):
                return "[REDACTED]"
            return value[:1000]
        if isinstance(value, (datetime, date, UUID, Path)):
            return str(value)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return type(value).__name__

    @staticmethod
    def _response_data(payload: dict[str, object]) -> dict[str, object]:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise AIValidationError("API_DATA_ENVELOPE_INVALID")
        return data

    @staticmethod
    def _auth_headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _json_default(value: object) -> str:
        if isinstance(value, (datetime, date, UUID, Path)):
            return str(value)
        return type(value).__name__
