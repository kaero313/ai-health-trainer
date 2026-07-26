from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.rag import AIGenerationTrace


QUOTA_POLICY_VERSION = "daily-logical-request-v1"

_RESERVE_SCRIPT = """
local existing_status = redis.call('HGET', KEYS[2], 'status')
if existing_status then
    local existing_position = redis.call('HGET', KEYS[2], 'position') or '0'
    local existing_limit = redis.call('HGET', KEYS[2], 'limit') or ARGV[1]
    return {existing_status, existing_position, existing_limit, tostring(redis.call('TTL', KEYS[1])), '0'}
end

local limit = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current >= limit then
    redis.call('HSET', KEYS[2],
        'status', 'rejected',
        'position', tostring(current),
        'limit', tostring(limit))
    redis.call('EXPIRE', KEYS[2], ttl)
    return {'rejected', tostring(current), tostring(limit), tostring(ttl), '1'}
end

local next_value = redis.call('INCR', KEYS[1])
local current_ttl = redis.call('TTL', KEYS[1])
if current_ttl < 0 then
    redis.call('EXPIRE', KEYS[1], ttl)
end
redis.call('HSET', KEYS[2],
    'status', 'reserved',
    'position', tostring(next_value),
    'limit', tostring(limit))
redis.call('EXPIRE', KEYS[2], ttl)
return {'reserved', tostring(next_value), tostring(limit), tostring(redis.call('TTL', KEYS[1])), '1'}
"""

_CONSUME_SCRIPT = """
local status = redis.call('HGET', KEYS[1], 'status')
if not status then
    return {'missing', '0'}
end
local position = redis.call('HGET', KEYS[1], 'position') or '0'
if status == 'reserved' then
    redis.call('HSET', KEYS[1], 'status', 'consumed')
    return {'consumed', position}
end
return {status, position}
"""

_RELEASE_SCRIPT = """
local status = redis.call('HGET', KEYS[2], 'status')
if not status then
    return {'missing', tostring(redis.call('GET', KEYS[1]) or '0')}
end
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if status == 'reserved' then
    if current > 0 then
        current = redis.call('DECR', KEYS[1])
    end
    redis.call('HSET', KEYS[2], 'status', 'released')
    return {'released', tostring(current)}
end
return {status, tostring(current)}
"""


class AIQuotaError(Exception):
    def __init__(self, status_code: int, code: str, message: str, *, stage: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.stage = stage


@dataclass(frozen=True)
class AIQuotaDecision:
    status: str
    bucket: str
    timezone: str
    position: int
    limit: int
    reset_at: datetime
    idempotent: bool


@dataclass(frozen=True)
class _QuotaKeys:
    counter: str
    reservation: str
    bucket: str
    reset_at: datetime
    ttl_seconds: int


class AIQuotaService:
    def __init__(self, settings: Settings, redis_client: Redis):
        self.settings = settings
        self.redis = redis_client
        self.timezone_name = settings.AI_QUOTA_TIMEZONE
        self.timezone = ZoneInfo(self.timezone_name)
        self.limit = int(settings.AI_DAILY_REQUEST_LIMIT)
        self.prefix = settings.AI_QUOTA_KEY_PREFIX.rstrip(":")
        self.grace_seconds = int(settings.AI_QUOTA_KEY_GRACE_SECONDS)

    async def reserve(
        self,
        db: AsyncSession,
        trace: AIGenerationTrace,
        *,
        now: datetime | None = None,
    ) -> AIQuotaDecision:
        if trace.user_id is None:
            raise AIQuotaError(
                503,
                "AI_QUOTA_UNAVAILABLE",
                "AI 사용량 예약 대상을 확인할 수 없습니다",
                stage="quota_admission",
            )
        observed_at = self._as_utc(now or datetime.now(timezone.utc))
        keys = self._keys(trace, observed_at)

        try:
            raw_result = await self.redis.eval(
                _RESERVE_SCRIPT,
                2,
                keys.counter,
                keys.reservation,
                self.limit,
                keys.ttl_seconds,
            )
            status, position, limit, _ttl, created = self._parse_result(raw_result, 5)
            decision = AIQuotaDecision(
                status=status,
                bucket=keys.bucket,
                timezone=self.timezone_name,
                position=int(position),
                limit=int(limit),
                reset_at=keys.reset_at,
                idempotent=created == "0",
            )
        except AIQuotaError as exc:
            await self._persist_admission_failure(
                db,
                trace,
                observed_at,
                error_code=exc.code,
                error_stage=exc.stage,
            )
            raise
        except Exception as exc:
            await self._persist_admission_failure(db, trace, observed_at)
            raise AIQuotaError(
                503,
                "AI_QUOTA_UNAVAILABLE",
                "AI 사용량 확인 서비스에 연결할 수 없습니다",
                stage="quota_admission",
            ) from exc

        if decision.status not in {"reserved", "consumed", "rejected"}:
            await self._persist_admission_failure(
                db,
                trace,
                observed_at,
                error_code="AI_QUOTA_STATE_INVALID",
                error_stage="quota_admission",
            )
            raise AIQuotaError(
                503,
                "AI_QUOTA_STATE_INVALID",
                f"AI 사용량 예약 상태가 올바르지 않습니다: {decision.status}",
                stage="quota_admission",
            )

        self._apply_decision(trace, decision, observed_at)
        if decision.status == "rejected":
            trace.status = "skipped"
            trace.error_code = "DAILY_LIMIT_EXCEEDED"
            trace.error_stage = "quota_admission"
            trace.completed_at = observed_at
            trace.quota_finalized_at = observed_at

        try:
            await db.commit()
        except Exception as exc:
            await db.rollback()
            if decision.status == "reserved" and not decision.idempotent:
                await self._best_effort_release(keys)
            try:
                persisted_trace = await db.get(AIGenerationTrace, trace.id)
                if persisted_trace is not None:
                    await self._persist_admission_failure(
                        db,
                        persisted_trace,
                        observed_at,
                        error_code="AI_QUOTA_UNAVAILABLE",
                        error_stage="quota_persistence",
                    )
            except Exception:
                await db.rollback()
            raise AIQuotaError(
                503,
                "AI_QUOTA_UNAVAILABLE",
                "AI 사용량 예약 감사 기록을 저장할 수 없습니다",
                stage="quota_persistence",
            ) from exc

        if decision.status == "rejected":
            raise AIQuotaError(
                429,
                "DAILY_LIMIT_EXCEEDED",
                "일일 AI 사용 한도에 도달했습니다",
                stage="quota_admission",
            )
        return decision

    async def consume(
        self,
        trace: AIGenerationTrace,
        *,
        now: datetime | None = None,
    ) -> None:
        if trace.quota_status == "consumed":
            return
        observed_at = self._as_utc(now or datetime.now(timezone.utc))
        keys = self._keys(trace, observed_at, bucket=trace.quota_bucket)
        try:
            raw_result = await self.redis.eval(
                _CONSUME_SCRIPT,
                1,
                keys.reservation,
            )
            status, position = self._parse_result(raw_result, 2)
        except Exception as exc:
            raise AIQuotaError(
                503,
                "AI_QUOTA_UNAVAILABLE",
                "AI 사용량 예약을 확정할 수 없습니다",
                stage="quota_settlement",
            ) from exc

        if status != "consumed":
            raise AIQuotaError(
                503,
                "AI_QUOTA_STATE_INVALID",
                f"AI 사용량 예약을 확정할 수 없는 상태입니다: {status}",
                stage="quota_settlement",
            )
        trace.quota_status = "consumed"
        trace.quota_position = int(position)
        trace.quota_finalized_at = observed_at
        self._merge_quota_metadata(trace, {"status": "consumed"})

    async def release(
        self,
        trace: AIGenerationTrace,
        *,
        now: datetime | None = None,
    ) -> None:
        if trace.quota_status in {"released", "rejected", "not_checked"}:
            return
        if trace.quota_status == "consumed":
            return

        observed_at = self._as_utc(now or datetime.now(timezone.utc))
        keys = self._keys(trace, observed_at, bucket=trace.quota_bucket)
        try:
            raw_result = await self.redis.eval(
                _RELEASE_SCRIPT,
                2,
                keys.counter,
                keys.reservation,
            )
            status, current = self._parse_result(raw_result, 2)
        except Exception as exc:
            raise AIQuotaError(
                503,
                "AI_QUOTA_UNAVAILABLE",
                "AI 사용량 예약을 해제할 수 없습니다",
                stage="quota_settlement",
            ) from exc

        if status == "missing" and observed_at >= keys.reset_at:
            status = "released"
        if status != "released":
            raise AIQuotaError(
                503,
                "AI_QUOTA_STATE_INVALID",
                f"AI 사용량 예약을 해제할 수 없는 상태입니다: {status}",
                stage="quota_settlement",
            )
        trace.quota_status = "released"
        trace.quota_finalized_at = observed_at
        self._merge_quota_metadata(
            trace,
            {"status": "released", "bucket_count_after_release": int(current)},
        )

    def _keys(
        self,
        trace: AIGenerationTrace,
        observed_at: datetime,
        *,
        bucket: str | None = None,
    ) -> _QuotaKeys:
        local_now = observed_at.astimezone(self.timezone)
        local_date = local_now.date()
        bucket_label = bucket or f"{local_date.isoformat()}@{self.timezone_name}"
        bucket_date_text = bucket_label.split("@", 1)[0]
        bucket_date = datetime.strptime(bucket_date_text, "%Y-%m-%d").date()
        next_midnight_local = datetime.combine(
            bucket_date + timedelta(days=1),
            time.min,
            tzinfo=self.timezone,
        )
        reset_at = next_midnight_local.astimezone(timezone.utc)
        ttl_seconds = max(
            1,
            math.ceil((reset_at - observed_at).total_seconds()) + self.grace_seconds,
        )
        hash_tag = f"{{{trace.user_id}:{bucket_date_text}}}"
        return _QuotaKeys(
            counter=f"{self.prefix}:{hash_tag}:count",
            reservation=f"{self.prefix}:{hash_tag}:request:{trace.request_id}",
            bucket=bucket_label,
            reset_at=reset_at,
            ttl_seconds=ttl_seconds,
        )

    def _apply_decision(
        self,
        trace: AIGenerationTrace,
        decision: AIQuotaDecision,
        observed_at: datetime,
    ) -> None:
        trace.quota_policy_version = QUOTA_POLICY_VERSION
        trace.quota_status = decision.status
        trace.quota_bucket = decision.bucket
        trace.quota_timezone = decision.timezone
        trace.quota_limit = decision.limit
        trace.quota_position = decision.position
        if decision.status == "reserved" and trace.quota_reserved_at is None:
            trace.quota_reserved_at = observed_at
        self._merge_quota_metadata(
            trace,
            {
                "policy_version": QUOTA_POLICY_VERSION,
                "status": decision.status,
                "bucket": decision.bucket,
                "timezone": decision.timezone,
                "position": decision.position,
                "limit": decision.limit,
                "reset_at": decision.reset_at.isoformat(),
                "idempotent": decision.idempotent,
            },
        )

    async def _persist_admission_failure(
        self,
        db: AsyncSession,
        trace: AIGenerationTrace,
        observed_at: datetime,
        *,
        error_code: str = "AI_QUOTA_UNAVAILABLE",
        error_stage: str = "quota_admission",
    ) -> None:
        trace.quota_policy_version = QUOTA_POLICY_VERSION
        trace.quota_status = "error"
        trace.status = "failed"
        trace.error_code = error_code
        trace.error_stage = error_stage
        trace.completed_at = observed_at
        trace.quota_finalized_at = observed_at
        self._merge_quota_metadata(trace, {"status": "error"})
        try:
            await db.commit()
        except Exception:
            await db.rollback()

    async def _best_effort_release(self, keys: _QuotaKeys) -> None:
        try:
            await self.redis.eval(
                _RELEASE_SCRIPT,
                2,
                keys.counter,
                keys.reservation,
            )
        except Exception:
            return

    @staticmethod
    def _merge_quota_metadata(
        trace: AIGenerationTrace,
        quota_metadata: dict[str, object],
    ) -> None:
        trace.trace_metadata = {
            **dict(trace.trace_metadata or {}),
            "quota": {
                **dict((trace.trace_metadata or {}).get("quota", {})),
                **quota_metadata,
            },
        }

    @staticmethod
    def _parse_result(result: Any, expected_length: int) -> tuple[str, ...]:
        if not isinstance(result, (list, tuple)) or len(result) != expected_length:
            raise AIQuotaError(
                503,
                "AI_QUOTA_STATE_INVALID",
                "AI 사용량 저장소가 잘못된 응답을 반환했습니다",
                stage="quota_storage",
            )
        return tuple(
            item.decode("utf-8") if isinstance(item, bytes) else str(item)
            for item in result
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
