from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.models.ai_recommendation import AIRecommendation
from app.models.rag import (
    AIGenerationTrace,
    RagPipelineDecision,
    RagRetrievalTrace,
)
from app.services.ai_quota_service import AIQuotaService
from app.services.ai_trace_service import abandon_stale_ai_requests
from app.services.ai_validation_service import AIValidationError, AIValidationService


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return str(value)


async def _reconcile_stale(args: argparse.Namespace) -> None:
    stale_before = datetime.now(timezone.utc) - timedelta(
        minutes=args.stale_minutes
    )
    quota_service = AIQuotaService(get_settings(), get_redis_client())
    async with AsyncSessionLocal() as db:
        result = await abandon_stale_ai_requests(
            db,
            stale_before=stale_before,
            quota_service=quota_service,
        )
    print(
        json.dumps(
            {
                "stale_before": stale_before,
                **result,
            },
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )


async def _trace(args: argparse.Namespace) -> None:
    request_id = UUID(args.request_id)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AIGenerationTrace)
            .options(selectinload(AIGenerationTrace.attempts))
            .where(AIGenerationTrace.request_id == request_id)
        )
        trace = result.scalar_one_or_none()
        if trace is None:
            raise SystemExit(f"AI request trace not found: {request_id}")

        payload = {
            "request_id": trace.request_id,
            "trace_id": trace.id,
            "request_type": trace.request_type,
            "status": trace.status,
            "provider_invoked": trace.provider_invoked,
            "quota_policy_version": trace.quota_policy_version,
            "quota_status": trace.quota_status,
            "quota_bucket": trace.quota_bucket,
            "quota_timezone": trace.quota_timezone,
            "quota_limit": trace.quota_limit,
            "quota_position": trace.quota_position,
            "quota_reserved_at": trace.quota_reserved_at,
            "quota_finalized_at": trace.quota_finalized_at,
            "response_schema_version": trace.response_schema_version,
            "model_used": trace.model_used,
            "error_code": trace.error_code,
            "error_stage": trace.error_stage,
            "started_at": trace.started_at,
            "completed_at": trace.completed_at,
            "deadline_at": trace.deadline_at,
            "attempts": [
                {
                    "attempt_no": attempt.attempt_no,
                    "attempt_kind": attempt.attempt_kind,
                    "status": attempt.status,
                    "model_used": attempt.model_used,
                    "latency_ms": attempt.latency_ms,
                    "tokens_input": attempt.tokens_input,
                    "tokens_output": attempt.tokens_output,
                    "finish_reason": attempt.finish_reason,
                    "provider_response_id": attempt.provider_response_id,
                    "error_code": attempt.error_code,
                    "error_stage": attempt.error_stage,
                    "started_at": attempt.started_at,
                    "completed_at": attempt.completed_at,
                }
                for attempt in trace.attempts
            ],
        }
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )


async def _privacy_audit(_: argparse.Namespace) -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        counts = (
            await db.execute(
                select(
                    func.count(RagRetrievalTrace.id),
                    func.count(RagRetrievalTrace.id).filter(
                        RagRetrievalTrace.query_text.is_not(None)
                    ),
                    func.count(RagRetrievalTrace.id).filter(
                        RagRetrievalTrace.query_hash.is_(None)
                    ),
                    func.count(RagRetrievalTrace.id).filter(
                        RagRetrievalTrace.query_retention_until <= now
                    ),
                )
            )
        ).one()
        policy_rows = (
            await db.execute(
                select(
                    RagRetrievalTrace.query_policy_version,
                    func.count(RagRetrievalTrace.id),
                )
                .group_by(RagRetrievalTrace.query_policy_version)
                .order_by(RagRetrievalTrace.query_policy_version)
            )
        ).all()
        raw_decision_context_rows = int(
            await db.scalar(
                select(func.count(RagPipelineDecision.id)).where(
                    RagPipelineDecision.context.has_key("query")  # type: ignore[attr-defined]
                )
            )
            or 0
        )
        raw_chat_context_rows = int(
            await db.scalar(
                select(func.count(AIRecommendation.id)).where(
                    AIRecommendation.context_summary.like("% 채팅:%")
                )
            )
            or 0
        )

    print(
        json.dumps(
            {
                "checked_at": now,
                "total_rows": int(counts[0]),
                "raw_query_rows": int(counts[1]),
                "missing_query_hash_rows": int(counts[2]),
                "raw_decision_context_rows": raw_decision_context_rows,
                "raw_chat_context_rows": raw_chat_context_rows,
                "expired_rows": int(counts[3]),
                "policy_versions": {
                    str(policy): int(count)
                    for policy, count in policy_rows
                },
            },
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )


async def _retrieval_retention(args: argparse.Namespace) -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        group_rows = (
            await db.execute(
                select(
                    RagRetrievalTrace.rag_trace_group_id,
                    func.min(RagRetrievalTrace.query_retention_until).label(
                        "first_expiry"
                    ),
                )
                .group_by(RagRetrievalTrace.rag_trace_group_id)
                .having(func.max(RagRetrievalTrace.query_retention_until) <= now)
                .order_by("first_expiry", RagRetrievalTrace.rag_trace_group_id)
                .limit(args.limit_groups)
            )
        ).all()
        group_ids = [str(row[0]) for row in group_rows]
        eligible_rows = 0
        if group_ids:
            eligible_rows = int(
                await db.scalar(
                    select(func.count(RagRetrievalTrace.id)).where(
                        RagRetrievalTrace.rag_trace_group_id.in_(group_ids)
                    )
                )
                or 0
            )
        deleted_rows = 0
        if args.execute and group_ids:
            result = await db.execute(
                delete(RagRetrievalTrace).where(
                    RagRetrievalTrace.rag_trace_group_id.in_(group_ids)
                )
            )
            deleted_rows = int(result.rowcount or 0)
            await db.commit()

    print(
        json.dumps(
            {
                "mode": "execute" if args.execute else "dry_run",
                "checked_at": now,
                "eligible_groups": len(group_ids),
                "eligible_rows": eligible_rows,
                "deleted_rows": deleted_rows,
                "group_batch_limit": args.limit_groups,
            },
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )


async def _validate_integration(args: argparse.Namespace) -> None:
    settings = get_settings()
    base_url = args.base_url or settings.AI_VALIDATION_BASE_URL
    image_path = args.image_path or settings.AI_VALIDATION_IMAGE_PATH
    async with AsyncSessionLocal() as db:
        service = AIValidationService(
            db,
            settings,
            redis_client=get_redis_client(),
        )
        result = await service.validate_integration(
            base_url=base_url,
            image_path=image_path,
            report_path=args.report_path,
            mode=args.mode,
        )
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )
    if result["status"] != "succeeded":
        raise SystemExit(1)


async def _validation_runs(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as db:
        result = await AIValidationService(
            db,
            get_settings(),
        ).list_runs(limit=args.limit)
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )


async def _validation_run(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as db:
        try:
            result = await AIValidationService(
                db,
                get_settings(),
            ).get_run(args.run_id)
        except (AIValidationError, ValueError) as exc:
            raise SystemExit(f"Validation run not found: {args.run_id}") from exc
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )


async def _validation_cleanup(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        try:
            result = await AIValidationService(
                db,
                settings,
                redis_client=get_redis_client(),
            ).cleanup_validation_run(args.run_id)
        except (AIValidationError, ValueError) as exc:
            raise SystemExit(f"Validation run cleanup failed: {args.run_id}") from exc
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Request Lifecycle CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reconcile = subparsers.add_parser(
        "reconcile-stale",
        help="Mark stale started requests and attempts as abandoned",
    )
    reconcile.add_argument(
        "--stale-minutes",
        type=int,
        default=5,
        help="Minimum started age before abandonment (default: 5)",
    )
    reconcile.set_defaults(handler=_reconcile_stale)

    trace = subparsers.add_parser(
        "trace",
        help="Show one request lifecycle and its provider attempts",
    )
    trace.add_argument("--request-id", required=True)
    trace.set_defaults(handler=_trace)

    privacy_audit = subparsers.add_parser(
        "privacy-audit",
        help="Audit retrieval traces for raw or expired query metadata",
    )
    privacy_audit.set_defaults(handler=_privacy_audit)

    retention = subparsers.add_parser(
        "retrieval-retention",
        help="Dry-run or delete expired retrieval trace rows in bounded batches",
    )
    retention.add_argument(
        "--limit-groups",
        type=int,
        default=1000,
        choices=range(1, 10001),
        metavar="1..10000",
    )
    retention.add_argument(
        "--execute",
        action="store_true",
        help="Delete complete eligible trace groups; omitted means dry-run",
    )
    retention.set_defaults(handler=_retrieval_retention)

    validate = subparsers.add_parser(
        "validate-integration",
        help="Run auditable UI/API/AI/RAG integration validation",
    )
    validate.add_argument(
        "--base-url",
        default=None,
        help="API v1 base URL; defaults to AI_VALIDATION_BASE_URL",
    )
    validate.add_argument(
        "--image-path",
        default=None,
        help="JPEG/PNG fixture path; defaults to AI_VALIDATION_IMAGE_PATH",
    )
    validate.add_argument(
        "--report-path",
        default="/workspace/docs/UI_AI_INTEGRATION_VALIDATION_REPORT.md",
        help="UTF-8 Markdown report path",
    )
    validate.add_argument(
        "--mode",
        choices=("live_api", "mock"),
        default="live_api",
    )
    validate.set_defaults(handler=_validate_integration)

    validation_runs = subparsers.add_parser(
        "validation-runs",
        help="List recent integration validation runs",
    )
    validation_runs.add_argument("--limit", type=int, default=20, choices=range(1, 101))
    validation_runs.set_defaults(handler=_validation_runs)

    validation_run = subparsers.add_parser(
        "validation-run",
        help="Show one integration validation run and its checks",
    )
    validation_run.add_argument("--run-id", required=True)
    validation_run.set_defaults(handler=_validation_run)

    validation_cleanup = subparsers.add_parser(
        "validation-cleanup",
        help="Clean residual test data for an interrupted validation run",
    )
    validation_cleanup.add_argument("--run-id", required=True)
    validation_cleanup.set_defaults(handler=_validation_cleanup)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(args.handler(args))


if __name__ == "__main__":
    main()
