from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.config import Settings


QUERY_PRIVACY_POLICY_VERSION = "query-minimization-v1"


@dataclass(frozen=True)
class RetrievalQueryAudit:
    query_hash: str
    summary: str
    policy_version: str
    key_version: str
    retention_until: datetime
    redacted_at: datetime


def build_retrieval_query_audit(
    query: str,
    *,
    settings: Settings,
    request_type: str,
    category: str | None,
    now: datetime | None = None,
) -> RetrievalQueryAudit:
    observed_at = _as_utc(now or datetime.now(timezone.utc))
    normalized_query = " ".join(query.split())
    category_scope = category or "all"
    secret = settings.RAG_TRACE_HASH_KEY or f"{settings.JWT_SECRET_KEY}:rag-query"
    key_version = settings.RAG_TRACE_HASH_KEY_VERSION
    fingerprint_input = (
        f"{QUERY_PRIVACY_POLICY_VERSION}\0{key_version}\0{request_type}\0"
        f"{category_scope}\0{normalized_query}"
    ).encode("utf-8")
    query_hash = hmac.new(
        secret.encode("utf-8"),
        fingerprint_input,
        hashlib.sha256,
    ).hexdigest()
    approximate_terms = len(normalized_query.split())
    summary = (
        f"type={request_type};category={category_scope};"
        f"chars={len(normalized_query)};terms={approximate_terms};raw_stored=false"
    )
    return RetrievalQueryAudit(
        query_hash=query_hash,
        summary=summary,
        policy_version=QUERY_PRIVACY_POLICY_VERSION,
        key_version=key_version,
        retention_until=observed_at
        + timedelta(days=int(settings.RAG_TRACE_RETENTION_DAYS)),
        redacted_at=observed_at,
    )


def decision_query_context(audit: RetrievalQueryAudit) -> dict[str, str]:
    return {
        "query_hash": audit.query_hash,
        "query_summary": audit.summary,
        "query_policy_version": audit.policy_version,
        "query_key_version": audit.key_version,
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
