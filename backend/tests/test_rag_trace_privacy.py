from datetime import datetime, timezone

from app.core.config import get_settings
from app.services.rag_trace_privacy import build_retrieval_query_audit


def test_query_audit_is_deterministic_without_storing_raw_text():
    settings = get_settings().model_copy(
        update={
            "RAG_TRACE_HASH_KEY": "test-query-secret",
            "RAG_TRACE_RETENTION_DAYS": 90,
        }
    )
    query = "운동 후 단백질을 얼마나 먹어야 하나요?"
    observed_at = datetime(2026, 7, 12, 0, 0, tzinfo=timezone.utc)

    first = build_retrieval_query_audit(
        query,
        settings=settings,
        request_type="chat",
        category="nutrition",
        now=observed_at,
    )
    second = build_retrieval_query_audit(
        query,
        settings=settings,
        request_type="chat",
        category="nutrition",
        now=observed_at,
    )

    assert first.query_hash == second.query_hash
    assert len(first.query_hash) == 64
    assert query not in first.summary
    assert "raw_stored=false" in first.summary
    assert first.key_version == "v1"
    assert first.retention_until.isoformat() == "2026-10-10T00:00:00+00:00"


def test_query_fingerprint_is_scoped_by_context_and_secret():
    base = get_settings().model_copy(update={"RAG_TRACE_HASH_KEY": "secret-a"})
    other_secret = base.model_copy(update={"RAG_TRACE_HASH_KEY": "secret-b"})
    query = "same query"

    chat = build_retrieval_query_audit(
        query,
        settings=base,
        request_type="chat",
        category="nutrition",
    )
    diet = build_retrieval_query_audit(
        query,
        settings=base,
        request_type="diet",
        category="nutrition",
    )
    secret_rotated = build_retrieval_query_audit(
        query,
        settings=other_secret,
        request_type="chat",
        category="nutrition",
    )

    assert chat.query_hash != diet.query_hash
    assert chat.query_hash != secret_rotated.query_hash


def test_query_fingerprint_changes_when_key_version_rotates():
    settings_v1 = get_settings().model_copy(
        update={
            "RAG_TRACE_HASH_KEY": "same-secret",
            "RAG_TRACE_HASH_KEY_VERSION": "v1",
        }
    )
    settings_v2 = settings_v1.model_copy(
        update={"RAG_TRACE_HASH_KEY_VERSION": "v2"}
    )

    first = build_retrieval_query_audit(
        "same query",
        settings=settings_v1,
        request_type="chat",
        category=None,
    )
    rotated = build_retrieval_query_audit(
        "same query",
        settings=settings_v2,
        request_type="chat",
        category=None,
    )

    assert first.query_hash != rotated.query_hash
    assert rotated.key_version == "v2"
