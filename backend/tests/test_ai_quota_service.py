from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from sqlalchemy import select

from app.core.config import get_settings
from app.models.rag import AIGenerationAttempt, AIGenerationTrace
from app.models.user import User
from app.services.ai_service import AIService
from app.services.ai_quota_service import AIQuotaError, AIQuotaService
from app.services.ai_trace_service import AIGenerationAttemptRecorder
from app.services.ai_trace_service import abandon_stale_ai_requests


class _FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


class _FailingRedis:
    async def eval(self, *_args, **_kwargs):
        raise ConnectionError("redis unavailable")


class _MalformedRedis:
    async def eval(self, *_args, **_kwargs):
        return ["invalid"]


def _test_redis_url() -> str:
    configured = os.getenv("TEST_REDIS_URL")
    if configured:
        return configured
    parsed = urlsplit(get_settings().REDIS_URL)
    return urlunsplit((parsed.scheme, parsed.netloc, "/15", parsed.query, parsed.fragment))


@pytest_asyncio.fixture
async def quota_redis():
    client = aioredis.from_url(_test_redis_url(), decode_responses=True)
    await client.ping()
    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


def _trace(user_id: int = 7) -> AIGenerationTrace:
    return AIGenerationTrace(
        request_id=uuid4(),
        user_id=user_id,
        request_type="chat",
        prompt_version="chat_v2",
        status="started",
        model_used="gemini-test",
        trace_metadata={},
    )


@pytest.mark.asyncio
async def test_atomic_reservation_never_exceeds_limit_under_concurrency(quota_redis):
    settings = get_settings().model_copy(
        update={
            "AI_DAILY_REQUEST_LIMIT": 10,
            "AI_QUOTA_KEY_PREFIX": "test:quota:concurrency",
        }
    )
    service = AIQuotaService(settings, quota_redis)
    observed_at = datetime(2026, 7, 12, 3, 0, tzinfo=timezone.utc)

    async def reserve_once(index: int) -> str:
        trace = _trace(user_id=100)
        try:
            await service.reserve(_FakeSession(), trace, now=observed_at)
        except AIQuotaError as exc:
            assert exc.code == "DAILY_LIMIT_EXCEEDED"
            return "rejected"
        assert trace.quota_position is not None
        return "reserved"

    results = await asyncio.gather(*(reserve_once(index) for index in range(50)))

    assert results.count("reserved") == 10
    assert results.count("rejected") == 40


@pytest.mark.asyncio
async def test_reservation_is_idempotent_for_same_request_id(quota_redis):
    settings = get_settings().model_copy(
        update={
            "AI_DAILY_REQUEST_LIMIT": 2,
            "AI_QUOTA_KEY_PREFIX": "test:quota:idempotent",
        }
    )
    service = AIQuotaService(settings, quota_redis)
    trace = _trace()
    session = _FakeSession()
    observed_at = datetime(2026, 7, 12, 3, 0, tzinfo=timezone.utc)

    first = await service.reserve(session, trace, now=observed_at)
    second = await service.reserve(session, trace, now=observed_at)
    keys = service._keys(trace, observed_at)

    assert first.position == 1
    assert first.idempotent is False
    assert second.position == 1
    assert second.idempotent is True
    assert await quota_redis.get(keys.counter) == "1"


@pytest.mark.asyncio
async def test_provider_retry_consumes_one_logical_request(quota_redis):
    settings = get_settings().model_copy(
        update={"AI_QUOTA_KEY_PREFIX": "test:quota:retry"}
    )
    service = AIQuotaService(settings, quota_redis)
    trace = _trace()
    observed_at = datetime(2026, 7, 12, 3, 0, tzinfo=timezone.utc)
    await service.reserve(_FakeSession(), trace, now=observed_at)

    await service.consume(trace, now=observed_at)
    await service.consume(trace, now=observed_at)
    await service.release(trace, now=observed_at)
    keys = service._keys(trace, observed_at)

    assert trace.quota_status == "consumed"
    assert await quota_redis.get(keys.counter) == "1"


@pytest.mark.asyncio
async def test_pre_provider_failure_releases_reservation(quota_redis):
    settings = get_settings().model_copy(
        update={"AI_QUOTA_KEY_PREFIX": "test:quota:release"}
    )
    service = AIQuotaService(settings, quota_redis)
    trace = _trace()
    observed_at = datetime(2026, 7, 12, 3, 0, tzinfo=timezone.utc)
    await service.reserve(_FakeSession(), trace, now=observed_at)

    await service.release(trace, now=observed_at)
    keys = service._keys(trace, observed_at)

    assert trace.quota_status == "released"
    assert await quota_redis.get(keys.counter) == "0"


@pytest.mark.asyncio
async def test_kst_midnight_creates_a_new_daily_bucket(quota_redis):
    settings = get_settings().model_copy(
        update={
            "AI_DAILY_REQUEST_LIMIT": 1,
            "AI_QUOTA_KEY_PREFIX": "test:quota:midnight",
            "AI_QUOTA_TIMEZONE": "Asia/Seoul",
        }
    )
    service = AIQuotaService(settings, quota_redis)
    before_midnight = datetime(2026, 7, 12, 14, 59, tzinfo=timezone.utc)
    after_midnight = datetime(2026, 7, 12, 15, 1, tzinfo=timezone.utc)
    first_trace = _trace(user_id=55)
    second_trace = _trace(user_id=55)

    first = await service.reserve(_FakeSession(), first_trace, now=before_midnight)
    second = await service.reserve(_FakeSession(), second_trace, now=after_midnight)

    assert first.bucket == "2026-07-12@Asia/Seoul"
    assert second.bucket == "2026-07-13@Asia/Seoul"
    assert first.position == second.position == 1


@pytest.mark.asyncio
async def test_redis_failure_is_fail_closed_and_audited():
    settings = get_settings().model_copy(
        update={"AI_QUOTA_KEY_PREFIX": "test:quota:failure"}
    )
    service = AIQuotaService(settings, _FailingRedis())
    trace = _trace()
    session = _FakeSession()

    with pytest.raises(AIQuotaError) as captured:
        await service.reserve(session, trace)

    assert captured.value.code == "AI_QUOTA_UNAVAILABLE"
    assert captured.value.status_code == 503
    assert trace.status == "failed"
    assert trace.quota_status == "error"
    assert trace.error_stage == "quota_admission"
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_malformed_redis_state_is_fail_closed_and_audited():
    settings = get_settings().model_copy(
        update={"AI_QUOTA_KEY_PREFIX": "test:quota:malformed"}
    )
    service = AIQuotaService(settings, _MalformedRedis())
    trace = _trace()
    session = _FakeSession()

    with pytest.raises(AIQuotaError) as captured:
        await service.reserve(session, trace)

    assert captured.value.code == "AI_QUOTA_STATE_INVALID"
    assert trace.status == "failed"
    assert trace.quota_status == "error"
    assert trace.error_code == "AI_QUOTA_STATE_INVALID"
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_provider_attempts_consume_one_durable_quota_reservation(
    db_session,
    quota_redis,
):
    user = User(
        email="quota-attempts@example.com",
        password_hash="not-used",
    )
    db_session.add(user)
    await db_session.commit()
    settings = get_settings().model_copy(
        update={"AI_QUOTA_KEY_PREFIX": "test:quota:attempt-link"}
    )
    quota_service = AIQuotaService(settings, quota_redis)
    ai_service = AIService(settings)
    trace = await ai_service.start_generation_trace(
        db_session,
        user_id=user.id,
        request_type="chat",
        prompt_version="chat_v2",
    )
    await quota_service.reserve(db_session, trace)
    recorder = AIGenerationAttemptRecorder(
        db_session,
        trace.id,
        quota_service,
    )

    first_attempt = await recorder.start_attempt(
        attempt_kind="initial",
        model="gemini-test",
    )
    await recorder.complete_attempt(
        first_attempt,
        status="failed",
        error_code="AI_TIMEOUT",
        error_stage="provider_call",
    )
    retry_attempt = await recorder.start_attempt(
        attempt_kind="provider_retry",
        model="gemini-test",
    )
    await recorder.complete_attempt(retry_attempt, status="succeeded")

    persisted = await db_session.get(AIGenerationTrace, trace.id)
    keys = quota_service._keys(persisted, datetime.now(timezone.utc))
    attempts = (
        await db_session.execute(
            select(AIGenerationAttempt)
            .where(AIGenerationAttempt.generation_trace_id == trace.id)
            .order_by(AIGenerationAttempt.attempt_no)
        )
    ).scalars().all()

    assert persisted.quota_status == "consumed"
    assert persisted.provider_invoked is True
    assert [attempt.attempt_kind for attempt in attempts] == [
        "initial",
        "provider_retry",
    ]
    assert all(attempt.attempt_metadata["quota_status"] == "consumed" for attempt in attempts)
    assert await quota_redis.get(keys.counter) == "1"


@pytest.mark.asyncio
async def test_terminal_request_without_provider_releases_durable_reservation(
    db_session,
    quota_redis,
):
    user = User(
        email="quota-release@example.com",
        password_hash="not-used",
    )
    db_session.add(user)
    await db_session.commit()
    settings = get_settings().model_copy(
        update={"AI_QUOTA_KEY_PREFIX": "test:quota:terminal-release"}
    )
    quota_service = AIQuotaService(settings, quota_redis)
    ai_service = AIService(settings)
    trace = await ai_service.start_generation_trace(
        db_session,
        user_id=user.id,
        request_type="chat",
        prompt_version="chat_v2",
    )
    await quota_service.reserve(db_session, trace)

    await ai_service.complete_generation_trace(
        db_session,
        trace.id,
        quota_service=quota_service,
        user_id=user.id,
        request_type="chat",
        prompt_version="chat_v2",
        status="skipped",
        error_code="RAG_CONTEXT_UNAVAILABLE",
        error_stage="retrieval",
        provider_invoked=False,
    )

    persisted = (
        await db_session.execute(
            select(AIGenerationTrace).where(AIGenerationTrace.id == trace.id)
        )
    ).scalar_one()
    keys = quota_service._keys(persisted, datetime.now(timezone.utc))

    assert persisted.status == "skipped"
    assert persisted.quota_status == "released"
    assert persisted.quota_finalized_at is not None
    assert await quota_redis.get(keys.counter) == "0"


@pytest.mark.asyncio
async def test_rejected_reservation_is_persisted_as_skipped_request(
    db_session,
    quota_redis,
):
    user = User(
        email="quota-rejected@example.com",
        password_hash="not-used",
    )
    db_session.add(user)
    await db_session.commit()
    settings = get_settings().model_copy(
        update={
            "AI_DAILY_REQUEST_LIMIT": 1,
            "AI_QUOTA_KEY_PREFIX": "test:quota:rejected-audit",
        }
    )
    quota_service = AIQuotaService(settings, quota_redis)
    ai_service = AIService(settings)
    admitted = await ai_service.start_generation_trace(
        db_session,
        user_id=user.id,
        request_type="chat",
        prompt_version="chat_v2",
    )
    rejected = await ai_service.start_generation_trace(
        db_session,
        user_id=user.id,
        request_type="diet",
        prompt_version="diet_recommend_v2",
    )
    await quota_service.reserve(db_session, admitted)

    with pytest.raises(AIQuotaError) as captured:
        await quota_service.reserve(db_session, rejected)

    await db_session.refresh(rejected)
    assert captured.value.code == "DAILY_LIMIT_EXCEEDED"
    assert rejected.status == "skipped"
    assert rejected.quota_status == "rejected"
    assert rejected.quota_position == 1
    assert rejected.error_stage == "quota_admission"
    assert rejected.provider_invoked is False


@pytest.mark.asyncio
async def test_stale_reconciliation_releases_unconsumed_reservation(
    db_session,
    quota_redis,
):
    user = User(
        email="quota-stale@example.com",
        password_hash="not-used",
    )
    db_session.add(user)
    await db_session.commit()
    settings = get_settings().model_copy(
        update={"AI_QUOTA_KEY_PREFIX": "test:quota:stale-release"}
    )
    quota_service = AIQuotaService(settings, quota_redis)
    ai_service = AIService(settings)
    trace = await ai_service.start_generation_trace(
        db_session,
        user_id=user.id,
        request_type="chat",
        prompt_version="chat_v2",
    )
    await quota_service.reserve(db_session, trace)
    trace.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    await db_session.commit()

    result = await abandon_stale_ai_requests(
        db_session,
        stale_before=datetime.now(timezone.utc) - timedelta(minutes=5),
        quota_service=quota_service,
    )
    await db_session.refresh(trace)
    keys = quota_service._keys(trace, datetime.now(timezone.utc))

    assert result["requests_abandoned"] == 1
    assert result["quota_reservations_released"] == 1
    assert trace.status == "abandoned"
    assert trace.quota_status == "released"
    assert await quota_redis.get(keys.counter) == "0"
