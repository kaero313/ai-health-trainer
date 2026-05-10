import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.rag import (
    RagCatalogPlanItem,
    RagCatalogPlanRun,
    RagChunk,
    RagReviewItem,
    RagReviewRun,
    RagSchedulerRun,
    RagSchedulerRunItem,
    RagSource,
)
from app.services.rag_review_service import RAGReviewService


async def _create_plan(db_session, *items: dict):
    run = RagCatalogPlanRun(
        catalog_file="rag_sources/catalog.json",
        catalog_version=1,
        mode="live_fetch",
        status="succeeded",
        total_sources=len(items),
        planned_create_count=sum(1 for item in items if item["planned_action"] == "create_source"),
        planned_skip_count=sum(1 for item in items if item["planned_action"] == "skip_refresh"),
        planned_partial_count=sum(1 for item in items if item["planned_action"] == "partial_refresh"),
        planned_full_count=sum(1 for item in items if item["planned_action"] == "full_reindex"),
        planned_manual_count=sum(1 for item in items if item["planned_action"] == "manual_review_required"),
        planned_defer_count=sum(1 for item in items if item["planned_action"] == "defer_reembedding"),
    )
    db_session.add(run)
    await db_session.flush()
    for index, item in enumerate(items, start=1):
        db_session.add(
            RagCatalogPlanItem(
                run_id=run.id,
                catalog_key=f"source_{index}",
                title=item.get("title", f"Source {index}"),
                acquisition_type=item.get("acquisition_type", "url_html"),
                source_grade=item.get("source_grade", "A"),
                catalog_status=item.get("catalog_status", "matched"),
                fetch_status=item.get("fetch_status", "succeeded"),
                parser_confidence=item.get("parser_confidence", 0.95),
                metadata_changed_fields=[],
                section_change_ratio=item.get("section_change_ratio", 0.0),
                chunk_change_ratio=item.get("chunk_change_ratio", 0.0),
                estimated_embedding_seconds=item.get("estimated_embedding_seconds", 0.0),
                quality_warnings=item.get("quality_warnings", []),
                planned_action=item["planned_action"],
                reason_code=item["reason_code"],
                risk_level=item.get("risk_level", "low"),
                context=item.get("context", {}),
            )
        )
    await db_session.commit()
    return run.id


def test_review_models_are_exported():
    from app.models import RagReviewItem as ExportedItem
    from app.models import RagReviewRun as ExportedRun

    assert ExportedRun is RagReviewRun
    assert ExportedItem is RagReviewItem


@pytest.mark.asyncio
async def test_catalog_review_skip_only_is_no_action(db_session):
    plan_id = await _create_plan(
        db_session,
        {"planned_action": "skip_refresh", "reason_code": "SOURCE_UNCHANGED"},
    )

    result = await RAGReviewService(db_session, get_settings()).review_catalog_plan(run_id=plan_id)
    item = result["items"][0]

    assert result["run"]["recommended_action"] == "no_action"
    assert result["run"]["requires_approval"] is False
    assert item["review_decision"] == "no_action"


@pytest.mark.asyncio
async def test_catalog_review_blocks_fetch_failure_without_mutating_rag_data(db_session):
    source_count_before = await db_session.scalar(select(func.count()).select_from(RagSource))
    chunk_count_before = await db_session.scalar(select(func.count()).select_from(RagChunk))
    plan_id = await _create_plan(
        db_session,
        {
            "planned_action": "manual_review_required",
            "reason_code": "FETCH_OR_PARSE_FAILED",
            "risk_level": "high",
            "fetch_status": "failed",
            "quality_warnings": ["fetch_or_parse_failed"],
        },
    )

    result = await RAGReviewService(db_session, get_settings()).review_catalog_plan(run_id=plan_id)
    item = result["items"][0]
    source_count_after = await db_session.scalar(select(func.count()).select_from(RagSource))
    chunk_count_after = await db_session.scalar(select(func.count()).select_from(RagChunk))

    assert result["run"]["recommended_action"] == "do_not_apply_until_resolved"
    assert result["run"]["risk_level"] == "high"
    assert item["review_decision"] == "fix_source_acquisition"
    assert item["blocking_reason"] == "FETCH_OR_PARSE_FAILED"
    assert source_count_after == source_count_before
    assert chunk_count_after == chunk_count_before


@pytest.mark.asyncio
async def test_catalog_review_maps_partial_full_and_create_actions(db_session):
    plan_id = await _create_plan(
        db_session,
        {"planned_action": "create_source", "reason_code": "NEW_CATALOG_SOURCE", "risk_level": "medium"},
        {"planned_action": "partial_refresh", "reason_code": "SMALL_CONTENT_CHANGE", "risk_level": "low"},
        {"planned_action": "full_reindex", "reason_code": "ANCHOR_LINEAGE_MISSING", "risk_level": "medium"},
    )

    result = await RAGReviewService(db_session, get_settings()).review_catalog_plan(run_id=plan_id)
    decisions = {item["planned_action"]: item["review_decision"] for item in result["items"]}

    assert result["run"]["recommended_action"] == "manual_confirm_before_apply"
    assert result["run"]["requires_approval"] is True
    assert decisions["create_source"] == "approve_create"
    assert decisions["partial_refresh"] == "approve_partial_refresh"
    assert decisions["full_reindex"] == "manual_confirm_full_reindex"


@pytest.mark.asyncio
async def test_scheduler_review_aggregates_multiple_catalog_plans(db_session):
    skip_plan_id = await _create_plan(
        db_session,
        {"planned_action": "skip_refresh", "reason_code": "SOURCE_UNCHANGED"},
    )
    partial_plan_id = await _create_plan(
        db_session,
        {"planned_action": "partial_refresh", "reason_code": "SMALL_CONTENT_CHANGE"},
    )
    scheduler = RagSchedulerRun(
        status="approval_required",
        mode="plan_only",
        target_catalogs=["catalog-a.json", "catalog-b.json"],
        force_plan=True,
        catalog_count=2,
        due_catalog_count=2,
        plan_run_ids=[skip_plan_id, partial_plan_id],
        approval_required_count=1,
        no_change_count=1,
    )
    db_session.add(scheduler)
    await db_session.flush()
    db_session.add_all(
        [
            RagSchedulerRunItem(
                run_id=scheduler.id,
                catalog_file="catalog-a.json",
                status="no_change",
                due_status="forced",
                plan_run_id=skip_plan_id,
            ),
            RagSchedulerRunItem(
                run_id=scheduler.id,
                catalog_file="catalog-b.json",
                status="approval_required",
                due_status="forced",
                plan_run_id=partial_plan_id,
                requires_approval=True,
            ),
        ]
    )
    await db_session.commit()

    result = await RAGReviewService(db_session, get_settings()).review_scheduler_run(run_id=scheduler.id)

    assert result["run"]["review_type"] == "scheduler_run"
    assert result["run"]["recommended_action"] == "review_then_apply"
    assert len(result["items"]) == 2


def test_review_report_writer_preserves_utf8_and_lf(tmp_path):
    report_path = tmp_path / "review.md"
    report = {
        "run": {
            "id": 1,
            "review_type": "catalog_plan",
            "target_run_id": 2,
            "status": "completed",
            "requires_approval": True,
            "recommended_action": "do_not_apply_until_resolved",
            "risk_level": "high",
        },
        "items": [
            {
                "title": "공식 영양 가이드",
                "planned_action": "manual_review_required",
                "reason_code": "FETCH_OR_PARSE_FAILED",
                "risk_level": "high",
                "review_decision": "fix_source_acquisition",
                "blocking_reason": "FETCH_OR_PARSE_FAILED",
                "operator_recommendation": "source acquisition을 먼저 복구한다.",
            }
        ],
    }

    RAGReviewService.write_review_report(report, report_path)

    data = report_path.read_bytes()
    assert b"\r\n" not in data
    assert "공식 영양 가이드".encode("utf-8") in data
