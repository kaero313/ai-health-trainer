from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import AIGenerationAttempt, AIGenerationTrace
from app.services.ai_quota_service import AIQuotaError, AIQuotaService


class AITracePersistenceError(Exception):
    """Raised when an AI audit record cannot be persisted safely."""


class AIGenerationAttemptRecorder:
    def __init__(
        self,
        db: AsyncSession,
        generation_trace_id: int,
        quota_service: AIQuotaService | None = None,
    ):
        self.db = db
        self.generation_trace_id = generation_trace_id
        self.quota_service = quota_service
        self._next_attempt_no = 1

    async def start_attempt(
        self,
        *,
        attempt_kind: str,
        model: str,
        metadata: dict[str, object] | None = None,
    ) -> int:
        attempt = AIGenerationAttempt(
            generation_trace_id=self.generation_trace_id,
            attempt_no=self._next_attempt_no,
            attempt_kind=attempt_kind,
            model_used=model,
            status="started",
            attempt_metadata=dict(metadata or {}),
        )
        self._next_attempt_no += 1

        try:
            trace = await self.db.get(AIGenerationTrace, self.generation_trace_id)
            if trace is None:
                raise AITracePersistenceError(
                    f"generation trace {self.generation_trace_id} does not exist"
                )
            if self.quota_service is not None:
                await self.quota_service.consume(trace)
            trace.provider_invoked = True
            attempt.attempt_metadata = {
                **dict(attempt.attempt_metadata or {}),
                "quota_status": trace.quota_status,
                "quota_position": trace.quota_position,
            }
            self.db.add(attempt)
            await self.db.commit()
            return attempt.id
        except AIQuotaError:
            await self.db.rollback()
            raise
        except AITracePersistenceError:
            await self.db.rollback()
            raise
        except Exception as exc:
            await self.db.rollback()
            raise AITracePersistenceError("failed to start provider attempt trace") from exc

    async def complete_attempt(
        self,
        attempt_id: int,
        *,
        status: str,
        latency_ms: int | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        finish_reason: str | None = None,
        provider_response_id: str | None = None,
        raw_response_hash: str | None = None,
        error_code: str | None = None,
        error_stage: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        try:
            attempt = await self.db.get(AIGenerationAttempt, attempt_id)
            if attempt is None:
                raise AITracePersistenceError(
                    f"generation attempt {attempt_id} does not exist"
                )
            attempt.status = status
            attempt.latency_ms = latency_ms
            attempt.tokens_input = tokens_input
            attempt.tokens_output = tokens_output
            attempt.finish_reason = finish_reason
            attempt.provider_response_id = provider_response_id
            attempt.raw_response_hash = raw_response_hash
            attempt.error_code = error_code
            attempt.error_stage = error_stage
            attempt.attempt_metadata = {
                **dict(attempt.attempt_metadata or {}),
                **dict(metadata or {}),
            }
            attempt.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
        except AITracePersistenceError:
            await self.db.rollback()
            raise
        except Exception as exc:
            await self.db.rollback()
            raise AITracePersistenceError("failed to complete provider attempt trace") from exc


async def abandon_stale_ai_requests(
    db: AsyncSession,
    *,
    stale_before: datetime,
    quota_service: AIQuotaService | None = None,
) -> dict[str, int]:
    completed_at = datetime.now(timezone.utc)
    try:
        stale_traces = (
            await db.execute(
                select(AIGenerationTrace).where(
                    AIGenerationTrace.status == "started",
                    AIGenerationTrace.started_at < stale_before,
                )
            )
        ).scalars().all()
        quota_reservations_released = 0
        for trace in stale_traces:
            if quota_service is not None and trace.quota_status == "reserved":
                await quota_service.release(trace, now=completed_at)
                quota_reservations_released += 1
            trace.status = "abandoned"
            trace.completed_at = completed_at
            trace.error_code = "AI_REQUEST_ABANDONED"
            trace.error_stage = "lifecycle_reconciliation"

        attempt_result = await db.execute(
            update(AIGenerationAttempt)
            .where(
                AIGenerationAttempt.status == "started",
                AIGenerationAttempt.started_at < stale_before,
            )
            .values(
                status="abandoned",
                completed_at=completed_at,
                error_code="AI_ATTEMPT_ABANDONED",
                error_stage="lifecycle_reconciliation",
            )
        )
        await db.commit()
        return {
            "attempts_abandoned": int(attempt_result.rowcount or 0),
            "requests_abandoned": len(stale_traces),
            "quota_reservations_released": quota_reservations_released,
        }
    except AIQuotaError as exc:
        await db.rollback()
        raise AITracePersistenceError(
            f"failed to reconcile stale AI quota reservation: {exc.code}"
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise AITracePersistenceError(
            "failed to reconcile stale AI request traces"
        ) from exc
