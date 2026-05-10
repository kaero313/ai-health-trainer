from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.models.rag import (
    RagCatalogPlanItem,
    RagCatalogPlanRun,
    RagReviewItem,
    RagReviewRun,
    RagSchedulerRun,
)


REVIEW_TYPE_CATALOG = "catalog_plan"
REVIEW_TYPE_SCHEDULER = "scheduler_run"

DECISION_NO_ACTION = "no_action"
DECISION_APPROVE_CREATE = "approve_create"
DECISION_APPROVE_PARTIAL = "approve_partial_refresh"
DECISION_CONFIRM_FULL = "manual_confirm_full_reindex"
DECISION_BLOCK_MANUAL = "blocked_manual_review"
DECISION_BLOCK_DEFER = "blocked_defer_reembedding"
DECISION_FIX_ACQUISITION = "fix_source_acquisition"

ACTION_NO_ACTION = "no_action"
ACTION_REVIEW_THEN_APPLY = "review_then_apply"
ACTION_CONFIRM_BEFORE_APPLY = "manual_confirm_before_apply"
ACTION_DO_NOT_APPLY = "do_not_apply_until_resolved"

BLOCKING_DECISIONS = {DECISION_BLOCK_MANUAL, DECISION_BLOCK_DEFER, DECISION_FIX_ACQUISITION}


@dataclass(frozen=True)
class ItemReview:
    decision: str
    recommendation: str
    blocking_reason: str | None = None


class RAGReviewService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    async def review_catalog_plan(
        self,
        *,
        run_id: int,
        report_path: str | Path | None = None,
    ) -> dict[str, Any]:
        plan_run = await self._load_catalog_plan(run_id)
        if plan_run is None:
            return {"status": "not_found", "run_id": run_id}

        review_run = RagReviewRun(
            review_type=REVIEW_TYPE_CATALOG,
            target_run_id=plan_run.id,
            catalog_plan_run_id=plan_run.id,
            status="running",
            recommended_action=ACTION_NO_ACTION,
            risk_level="low",
            report_path=str(report_path) if report_path else None,
        )
        self.db.add(review_run)
        await self.db.flush()

        review_items = self._review_plan_items(
            plan_run.items,
            review_run_id=review_run.id,
            plan_context={"catalog_file": plan_run.catalog_file},
        )
        for item in review_items:
            self.db.add(item)
        await self.db.flush()
        self._finalize_review_run(review_run, review_items)
        await self.db.commit()

        result = await self.get_run(review_run.id)
        if report_path:
            self.write_review_report(result, Path(report_path))
        return result

    async def review_scheduler_run(
        self,
        *,
        run_id: int,
        report_path: str | Path | None = None,
    ) -> dict[str, Any]:
        scheduler_run = await self._load_scheduler_run(run_id)
        if scheduler_run is None:
            return {"status": "not_found", "run_id": run_id}

        plan_runs = await self._load_catalog_plans_from_scheduler(scheduler_run)
        review_run = RagReviewRun(
            review_type=REVIEW_TYPE_SCHEDULER,
            target_run_id=scheduler_run.id,
            scheduler_run_id=scheduler_run.id,
            status="running",
            recommended_action=ACTION_NO_ACTION,
            risk_level="low",
            report_path=str(report_path) if report_path else None,
        )
        self.db.add(review_run)
        await self.db.flush()

        review_items: list[RagReviewItem] = []
        for plan_run in plan_runs:
            review_items.extend(
                self._review_plan_items(
                    plan_run.items,
                    review_run_id=review_run.id,
                    plan_context={"catalog_file": plan_run.catalog_file, "catalog_plan_run_id": plan_run.id},
                )
            )
        for item in review_items:
            self.db.add(item)
        await self.db.flush()
        self._finalize_review_run(
            review_run,
            review_items,
            extra_summary={
                "scheduler_status": scheduler_run.status,
                "catalog_plan_run_ids": [plan.id for plan in plan_runs],
            },
        )
        await self.db.commit()

        result = await self.get_run(review_run.id)
        if report_path:
            self.write_review_report(result, Path(report_path))
        return result

    async def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(RagReviewRun).order_by(RagReviewRun.id.desc()).limit(limit)
            )
        ).scalars().all()
        return [self._run_summary(row) for row in rows]

    async def get_run(self, run_id: int) -> dict[str, Any]:
        run = (
            await self.db.execute(
                select(RagReviewRun)
                .options(selectinload(RagReviewRun.items))
                .where(RagReviewRun.id == run_id)
            )
        ).scalar_one_or_none()
        if run is None:
            return {"status": "not_found", "run_id": run_id}
        items = sorted(run.items, key=lambda item: item.id)
        return {
            "status": "found",
            "run": self._run_summary(run),
            "items": [self._item_summary(item) for item in items],
        }

    async def _load_catalog_plan(self, run_id: int) -> RagCatalogPlanRun | None:
        return (
            await self.db.execute(
                select(RagCatalogPlanRun)
                .options(selectinload(RagCatalogPlanRun.items))
                .where(RagCatalogPlanRun.id == run_id)
            )
        ).scalar_one_or_none()

    async def _load_scheduler_run(self, run_id: int) -> RagSchedulerRun | None:
        return (
            await self.db.execute(
                select(RagSchedulerRun)
                .options(selectinload(RagSchedulerRun.items))
                .where(RagSchedulerRun.id == run_id)
            )
        ).scalar_one_or_none()

    async def _load_catalog_plans_from_scheduler(self, scheduler_run: RagSchedulerRun) -> list[RagCatalogPlanRun]:
        plan_ids = [item.plan_run_id for item in scheduler_run.items if item.plan_run_id is not None]
        if not plan_ids:
            plan_ids = [int(value) for value in scheduler_run.plan_run_ids or []]
        if not plan_ids:
            return []
        rows = (
            await self.db.execute(
                select(RagCatalogPlanRun)
                .options(selectinload(RagCatalogPlanRun.items))
                .where(RagCatalogPlanRun.id.in_(plan_ids))
            )
        ).scalars().all()
        by_id = {row.id: row for row in rows}
        return [by_id[plan_id] for plan_id in plan_ids if plan_id in by_id]

    def _review_plan_items(
        self,
        plan_items: list[RagCatalogPlanItem],
        *,
        review_run_id: int,
        plan_context: dict[str, object],
    ) -> list[RagReviewItem]:
        review_items: list[RagReviewItem] = []
        for item in sorted(plan_items, key=lambda row: row.id):
            review = _review_item_decision(item)
            review_items.append(
                RagReviewItem(
                    review_run_id=review_run_id,
                    catalog_plan_run_id=item.run_id,
                    catalog_plan_item_id=item.id,
                    source_id=item.source_id,
                    catalog_key=item.catalog_key,
                    title=item.title,
                    acquisition_type=item.acquisition_type,
                    source_grade=item.source_grade,
                    planned_action=item.planned_action,
                    reason_code=item.reason_code,
                    risk_level=item.risk_level,
                    review_decision=review.decision,
                    operator_recommendation=review.recommendation,
                    blocking_reason=review.blocking_reason,
                    parser_confidence=item.parser_confidence,
                    section_change_ratio=item.section_change_ratio,
                    chunk_change_ratio=item.chunk_change_ratio,
                    estimated_embedding_seconds=item.estimated_embedding_seconds,
                    quality_warnings=list(item.quality_warnings or []),
                    context={
                        **plan_context,
                        "catalog_status": item.catalog_status,
                        "fetch_status": item.fetch_status,
                        "metadata_changed_fields": list(item.metadata_changed_fields or []),
                        "sections": {
                            "added": item.sections_added,
                            "removed": item.sections_removed,
                            "changed": item.sections_changed,
                            "unchanged": item.sections_unchanged,
                            "change_ratio": item.section_change_ratio,
                        },
                        "chunks": {
                            "added": item.chunks_added,
                            "removed": item.chunks_removed,
                            "changed": item.chunks_changed,
                            "unchanged": item.chunks_unchanged,
                            "change_ratio": item.chunk_change_ratio,
                        },
                        "plan_context": item.context,
                    },
                )
            )
        return review_items

    @staticmethod
    def _finalize_review_run(
        review_run: RagReviewRun,
        items: list[RagReviewItem],
        *,
        extra_summary: dict[str, object] | None = None,
    ) -> None:
        recommended_action, risk_level, requires_approval = _run_recommendation(items)
        review_run.status = "completed"
        review_run.requires_approval = requires_approval
        review_run.recommended_action = recommended_action
        review_run.risk_level = risk_level
        counts: dict[str, int] = {}
        for item in items:
            counts[item.review_decision] = counts.get(item.review_decision, 0) + 1
        review_run.summary = {
            "total_items": len(items),
            "decision_counts": counts,
            "blocking_count": sum(1 for item in items if item.review_decision in BLOCKING_DECISIONS),
            "approval_candidate_count": sum(
                1
                for item in items
                if item.review_decision in {DECISION_APPROVE_CREATE, DECISION_APPROVE_PARTIAL, DECISION_CONFIRM_FULL}
            ),
            **(extra_summary or {}),
        }

    @staticmethod
    def _run_summary(run: RagReviewRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "review_type": run.review_type,
            "target_run_id": run.target_run_id,
            "catalog_plan_run_id": run.catalog_plan_run_id,
            "scheduler_run_id": run.scheduler_run_id,
            "status": run.status,
            "requires_approval": run.requires_approval,
            "recommended_action": run.recommended_action,
            "risk_level": run.risk_level,
            "report_path": run.report_path,
            "summary": run.summary,
            "created_at": _dt(run.created_at),
        }

    @staticmethod
    def _item_summary(item: RagReviewItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "review_run_id": item.review_run_id,
            "catalog_plan_run_id": item.catalog_plan_run_id,
            "catalog_plan_item_id": item.catalog_plan_item_id,
            "source_id": item.source_id,
            "catalog_key": item.catalog_key,
            "title": item.title,
            "acquisition_type": item.acquisition_type,
            "source_grade": item.source_grade,
            "planned_action": item.planned_action,
            "reason_code": item.reason_code,
            "risk_level": item.risk_level,
            "review_decision": item.review_decision,
            "operator_recommendation": item.operator_recommendation,
            "blocking_reason": item.blocking_reason,
            "parser_confidence": item.parser_confidence,
            "section_change_ratio": item.section_change_ratio,
            "chunk_change_ratio": item.chunk_change_ratio,
            "estimated_embedding_seconds": item.estimated_embedding_seconds,
            "quality_warnings": item.quality_warnings,
            "context": item.context,
            "created_at": _dt(item.created_at),
        }

    @staticmethod
    def write_review_report(result: dict[str, Any], report_path: Path) -> None:
        run = result.get("run", {})
        items = result.get("items", [])
        lines = [
            "# RAG Review Report",
            "",
            f"- review_run_id: {run.get('id')}",
            f"- review_type: {run.get('review_type')}",
            f"- target_run_id: {run.get('target_run_id')}",
            f"- status: {run.get('status')}",
            f"- requires_approval: {run.get('requires_approval')}",
            f"- recommended_action: {run.get('recommended_action')}",
            f"- risk_level: {run.get('risk_level')}",
            "",
            "## Items",
            "",
            "| Source | Plan | Reason | Risk | Review Decision | Blocking | Recommendation |",
            "|--------|------|--------|------|-----------------|----------|----------------|",
        ]
        for item in items:
            lines.append(
                "| {source} | {planned_action} | {reason_code} | {risk_level} | {review_decision} | "
                "{blocking_reason} | {operator_recommendation} |".format(
                    source=_escape_table_value(str(item.get("title") or item.get("catalog_key") or "")),
                    planned_action=item.get("planned_action"),
                    reason_code=item.get("reason_code"),
                    risk_level=item.get("risk_level"),
                    review_decision=item.get("review_decision"),
                    blocking_reason=item.get("blocking_reason") or "",
                    operator_recommendation=_escape_table_value(str(item.get("operator_recommendation") or "")),
                )
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _review_item_decision(item: RagCatalogPlanItem) -> ItemReview:
    warnings = set(item.quality_warnings or [])
    if item.fetch_status == "failed" or item.reason_code == "FETCH_OR_PARSE_FAILED" or "fetch_or_parse_failed" in warnings:
        return ItemReview(
            DECISION_FIX_ACQUISITION,
            "Fix the source acquisition path before apply: verify URL access, source replacement, or adapter behavior.",
            "FETCH_OR_PARSE_FAILED",
        )
    if item.planned_action == "skip_refresh":
        return ItemReview(DECISION_NO_ACTION, "No apply is needed because the source and metadata are unchanged.")
    if item.planned_action == "create_source":
        return ItemReview(DECISION_APPROVE_CREATE, "Review source metadata and trust grade, then apply if expected.")
    if item.planned_action == "partial_refresh":
        return ItemReview(DECISION_APPROVE_PARTIAL, "Review changed section/chunk ratios, then apply partial refresh.")
    if item.planned_action == "full_reindex":
        return ItemReview(
            DECISION_CONFIRM_FULL,
            "Confirm reindex scope and embedding cost before apply.",
        )
    if item.planned_action == "manual_review_required":
        return ItemReview(
            DECISION_BLOCK_MANUAL,
            "Resolve quality warnings or catalog/source mismatch before apply.",
            item.reason_code,
        )
    if item.planned_action == "defer_reembedding":
        return ItemReview(
            DECISION_BLOCK_DEFER,
            "Increase reembedding budget or defer this source to a later maintenance window.",
            item.reason_code,
        )
    return ItemReview(DECISION_BLOCK_MANUAL, "Unknown plan action requires manual review.", item.reason_code)


def _run_recommendation(items: list[RagReviewItem]) -> tuple[str, str, bool]:
    if not items or all(item.review_decision == DECISION_NO_ACTION for item in items):
        return ACTION_NO_ACTION, "low", False
    if any(item.review_decision in BLOCKING_DECISIONS for item in items):
        return ACTION_DO_NOT_APPLY, _max_risk(items), True
    if any(item.review_decision == DECISION_CONFIRM_FULL or item.risk_level == "high" for item in items):
        return ACTION_CONFIRM_BEFORE_APPLY, _max_risk(items), True
    return ACTION_REVIEW_THEN_APPLY, _max_risk(items), True


def _max_risk(items: list[RagReviewItem]) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    highest = "low"
    for item in items:
        if order.get(item.risk_level, 0) > order[highest]:
            highest = item.risk_level
    return highest


def _dt(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _escape_table_value(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
