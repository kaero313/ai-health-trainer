from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.models.rag import RagSchedulerRun, RagSchedulerRunItem, RagSource
from app.services.rag_catalog_control_service import RAGCatalogControlService
from app.services.rag_pipeline import hash_text
from app.services.rag_source_adapters import (
    ACQUISITION_LOCAL_FILE,
    ACQUISITION_URL_HTML,
    CatalogSource,
    load_catalog_sources,
    resolve_catalog_path,
)


DEFAULT_SCHEDULER_CATALOGS = (
    "rag_sources/catalog.json",
    "rag_sources/document_catalog.json",
)

SCHEDULER_STATUS_NO_DUE = "no_due_sources"
SCHEDULER_STATUS_NO_CHANGE = "no_change"
SCHEDULER_STATUS_APPROVAL = "approval_required"
SCHEDULER_STATUS_ERRORS = "completed_with_errors"

PLAN_ONLY_MODE = "plan_only"


@dataclass(frozen=True)
class CatalogDueCheck:
    catalog_file: Path
    catalog_version: int | None
    total_sources: int
    due_source_count: int
    due_status: str
    reason_code: str
    reasons: list[dict[str, object]]


class RAGRefreshSchedulerService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        self.catalog_service = RAGCatalogControlService(db, settings)

    async def run(
        self,
        *,
        catalog_files: list[str | Path] | None = None,
        report_path: str | Path | None = None,
        force_plan: bool = False,
        limit_catalogs: int | None = None,
    ) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        catalogs = [Path(value) for value in (catalog_files or list(DEFAULT_SCHEDULER_CATALOGS))]
        if limit_catalogs is not None:
            catalogs = catalogs[:limit_catalogs]

        run = RagSchedulerRun(
            status="running",
            mode=PLAN_ONLY_MODE,
            target_catalogs=[str(path) for path in catalogs],
            force_plan=force_plan,
            report_path=str(report_path) if report_path else None,
            catalog_count=len(catalogs),
            started_at=started_at,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        for catalog_path in catalogs:
            try:
                due_check = await self._check_catalog_due(catalog_path, force_plan=force_plan)
                if due_check.due_status == "not_due":
                    item = RagSchedulerRunItem(
                        run_id=run.id,
                        catalog_file=str(catalog_path),
                        catalog_version=due_check.catalog_version,
                        status=SCHEDULER_STATUS_NO_DUE,
                        due_status=due_check.due_status,
                        reason_code=due_check.reason_code,
                        total_sources=due_check.total_sources,
                        due_source_count=0,
                        context={"reasons": due_check.reasons},
                    )
                    self.db.add(item)
                    await self.db.commit()
                    continue

                plan = await self.catalog_service.create_plan(catalog_file=catalog_path)
                plan_run = plan["run"]
                requires_approval = _requires_approval(plan_run)
                item = RagSchedulerRunItem(
                    run_id=run.id,
                    catalog_file=str(catalog_path),
                    catalog_version=due_check.catalog_version,
                    status=SCHEDULER_STATUS_APPROVAL if requires_approval else SCHEDULER_STATUS_NO_CHANGE,
                    due_status=due_check.due_status,
                    reason_code="APPROVAL_REQUIRED" if requires_approval else "PLAN_NO_CHANGE",
                    plan_run_id=int(plan_run["id"]),
                    requires_approval=requires_approval,
                    total_sources=int(plan_run["total_sources"]),
                    due_source_count=due_check.due_source_count,
                    planned_create_count=int(plan_run["planned_create_count"]),
                    planned_skip_count=int(plan_run["planned_skip_count"]),
                    planned_partial_count=int(plan_run["planned_partial_count"]),
                    planned_full_count=int(plan_run["planned_full_count"]),
                    planned_manual_count=int(plan_run["planned_manual_count"]),
                    planned_defer_count=int(plan_run["planned_defer_count"]),
                    context={"reasons": due_check.reasons, "plan_status": plan_run["status"]},
                )
                self.db.add(item)
                await self.db.commit()
            except Exception as exc:
                item = RagSchedulerRunItem(
                    run_id=run.id,
                    catalog_file=str(catalog_path),
                    status=SCHEDULER_STATUS_ERRORS,
                    due_status="error",
                    reason_code="CATALOG_CHECK_FAILED",
                    requires_approval=True,
                    error_code="CATALOG_CHECK_FAILED",
                    error_message=str(exc),
                    context={"error": str(exc)},
                )
                self.db.add(item)
                await self.db.commit()

        await self._finalize_run(run.id)
        result = await self.get_run(run.id)
        if report_path:
            self.write_scheduler_report(result, Path(report_path))
        return result

    async def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(RagSchedulerRun).order_by(RagSchedulerRun.id.desc()).limit(limit)
            )
        ).scalars().all()
        return [self._run_summary(row) for row in rows]

    async def get_run(self, run_id: int) -> dict[str, Any]:
        run = (
            await self.db.execute(
                select(RagSchedulerRun)
                .options(selectinload(RagSchedulerRun.items))
                .where(RagSchedulerRun.id == run_id)
            )
        ).scalar_one_or_none()
        if run is None:
            return {"status": "not_found", "run_id": run_id}
        return {
            "status": "found",
            "run": self._run_summary(run),
            "items": [self._item_summary(item) for item in sorted(run.items, key=lambda row: row.id)],
        }

    async def _check_catalog_due(self, catalog_file: Path, *, force_plan: bool) -> CatalogDueCheck:
        payload = json.loads(catalog_file.read_text(encoding="utf-8"))
        catalog_version = _optional_int(payload.get("version")) if isinstance(payload, dict) else None
        catalog_sources = load_catalog_sources(payload)
        active_sources = await self._load_active_sources(catalog_sources)
        reasons: list[dict[str, object]] = []

        if force_plan:
            return CatalogDueCheck(
                catalog_file=catalog_file,
                catalog_version=catalog_version,
                total_sources=len(catalog_sources),
                due_source_count=len(catalog_sources),
                due_status="forced",
                reason_code="FORCE_PLAN",
                reasons=[{"catalog_key": source.key, "reason_code": "FORCE_PLAN"} for source in catalog_sources],
            )

        for catalog_source in catalog_sources:
            existing_source = self._match_catalog_source(catalog_source, active_sources, catalog_file)
            reason = self._due_reason(catalog_source, existing_source, catalog_file)
            if reason:
                reasons.append({"catalog_key": catalog_source.key, **reason})

        if not reasons:
            return CatalogDueCheck(
                catalog_file=catalog_file,
                catalog_version=catalog_version,
                total_sources=len(catalog_sources),
                due_source_count=0,
                due_status="not_due",
                reason_code="NO_DUE_SOURCE",
                reasons=[],
            )
        return CatalogDueCheck(
            catalog_file=catalog_file,
            catalog_version=catalog_version,
            total_sources=len(catalog_sources),
            due_source_count=len(reasons),
            due_status="due",
            reason_code="DUE_SOURCE_FOUND",
            reasons=reasons,
        )

    async def _load_active_sources(self, catalog_sources: list[CatalogSource]) -> list[RagSource]:
        acquisition_types = {source.acquisition_type for source in catalog_sources}
        origin_types: set[str] = set()
        for acquisition_type in acquisition_types:
            if acquisition_type == ACQUISITION_LOCAL_FILE:
                origin_types.update({"file_markdown", "file_text", "file_pdf"})
            else:
                origin_types.add("url_html")
        if not origin_types:
            return []
        return (
            await self.db.execute(
                select(RagSource)
                .where(RagSource.status == "active", RagSource.origin_type.in_(origin_types))
                .order_by(RagSource.id.asc())
            )
        ).scalars().all()

    def _match_catalog_source(
        self,
        catalog_source: CatalogSource,
        sources: list[RagSource],
        catalog_file: Path,
    ) -> RagSource | None:
        origin_uri = _catalog_origin_uri(catalog_source, catalog_file)
        for source in sources:
            if catalog_source.key and _source_catalog_key(source) == catalog_source.key:
                return source
        for source in sources:
            if origin_uri and source.origin_uri == origin_uri:
                return source
        for source in sources:
            if catalog_source.url and catalog_source.url in {source.origin_uri, source.source_url}:
                return source
        return None

    def _due_reason(
        self,
        catalog_source: CatalogSource,
        existing_source: RagSource | None,
        catalog_file: Path,
    ) -> dict[str, object] | None:
        if existing_source is None:
            return {"reason_code": "SOURCE_NOT_REGISTERED", "acquisition_type": catalog_source.acquisition_type}
        if catalog_source.acquisition_type == ACQUISITION_LOCAL_FILE:
            return _local_file_due_reason(catalog_source, existing_source, catalog_file)
        return _url_due_reason(existing_source)

    async def _finalize_run(self, run_id: int) -> None:
        run = (
            await self.db.execute(
                select(RagSchedulerRun)
                .options(selectinload(RagSchedulerRun.items))
                .where(RagSchedulerRun.id == run_id)
            )
        ).scalar_one()
        items = list(run.items)
        plan_run_ids = [item.plan_run_id for item in items if item.plan_run_id is not None]
        run.due_catalog_count = sum(1 for item in items if item.due_status in {"due", "forced"})
        run.plan_run_ids = plan_run_ids
        run.approval_required_count = sum(1 for item in items if item.requires_approval)
        run.no_change_count = sum(1 for item in items if item.status in {SCHEDULER_STATUS_NO_DUE, SCHEDULER_STATUS_NO_CHANGE})
        run.error_count = sum(1 for item in items if item.status == SCHEDULER_STATUS_ERRORS)
        if run.error_count:
            run.status = SCHEDULER_STATUS_ERRORS
        elif run.approval_required_count:
            run.status = SCHEDULER_STATUS_APPROVAL
        elif not plan_run_ids:
            run.status = SCHEDULER_STATUS_NO_DUE
        else:
            run.status = SCHEDULER_STATUS_NO_CHANGE
        run.summary = {
            "items": len(items),
            "plan_run_ids": plan_run_ids,
            "approval_required_count": run.approval_required_count,
            "no_change_count": run.no_change_count,
            "error_count": run.error_count,
        }
        run.finished_at = datetime.now(timezone.utc)
        await self.db.commit()

    @staticmethod
    def _run_summary(run: RagSchedulerRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "status": run.status,
            "mode": run.mode,
            "target_catalogs": run.target_catalogs,
            "force_plan": run.force_plan,
            "report_path": run.report_path,
            "catalog_count": run.catalog_count,
            "due_catalog_count": run.due_catalog_count,
            "plan_run_ids": run.plan_run_ids,
            "approval_required_count": run.approval_required_count,
            "no_change_count": run.no_change_count,
            "error_count": run.error_count,
            "summary": run.summary,
            "started_at": _dt(run.started_at),
            "finished_at": _dt(run.finished_at),
            "created_at": _dt(run.created_at),
        }

    @staticmethod
    def _item_summary(item: RagSchedulerRunItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "run_id": item.run_id,
            "catalog_file": item.catalog_file,
            "catalog_version": item.catalog_version,
            "status": item.status,
            "due_status": item.due_status,
            "reason_code": item.reason_code,
            "plan_run_id": item.plan_run_id,
            "requires_approval": item.requires_approval,
            "total_sources": item.total_sources,
            "due_source_count": item.due_source_count,
            "planned_create_count": item.planned_create_count,
            "planned_skip_count": item.planned_skip_count,
            "planned_partial_count": item.planned_partial_count,
            "planned_full_count": item.planned_full_count,
            "planned_manual_count": item.planned_manual_count,
            "planned_defer_count": item.planned_defer_count,
            "error_code": item.error_code,
            "error_message": item.error_message,
            "context": item.context,
            "created_at": _dt(item.created_at),
        }

    @staticmethod
    def write_scheduler_report(result: dict[str, Any], report_path: Path) -> None:
        run = result.get("run", {})
        items = result.get("items", [])
        lines = [
            "# RAG Scheduler Report",
            "",
            f"- run_id: {run.get('id')}",
            f"- status: {run.get('status')}",
            f"- mode: {run.get('mode')}",
            f"- force_plan: {run.get('force_plan')}",
            f"- catalog_count: {run.get('catalog_count')}",
            f"- due_catalog_count: {run.get('due_catalog_count')}",
            f"- plan_run_ids: {', '.join(str(value) for value in run.get('plan_run_ids') or [])}",
            f"- approval_required_count: {run.get('approval_required_count')}",
            f"- no_change_count: {run.get('no_change_count')}",
            f"- error_count: {run.get('error_count')}",
            "",
            "## Catalogs",
            "",
            "| Catalog | Due | Status | Plan Run | Approval | Create | Skip | Partial | Full | Manual | Defer | Reason |",
            "|---------|-----|--------|----------|----------|--------|------|---------|------|--------|-------|--------|",
        ]
        for item in items:
            lines.append(
                "| {catalog_file} | {due_status} | {status} | {plan_run_id} | {requires_approval} | "
                "{planned_create_count} | {planned_skip_count} | {planned_partial_count} | "
                "{planned_full_count} | {planned_manual_count} | {planned_defer_count} | {reason_code} |".format(
                    catalog_file=_escape_table_value(str(item.get("catalog_file") or "")),
                    due_status=item.get("due_status"),
                    status=item.get("status"),
                    plan_run_id=item.get("plan_run_id") or "",
                    requires_approval=item.get("requires_approval"),
                    planned_create_count=item.get("planned_create_count"),
                    planned_skip_count=item.get("planned_skip_count"),
                    planned_partial_count=item.get("planned_partial_count"),
                    planned_full_count=item.get("planned_full_count"),
                    planned_manual_count=item.get("planned_manual_count"),
                    planned_defer_count=item.get("planned_defer_count"),
                    reason_code=item.get("reason_code") or "",
                )
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _requires_approval(plan_run: dict[str, Any]) -> bool:
    return any(
        int(plan_run.get(key) or 0) > 0
        for key in [
            "planned_create_count",
            "planned_partial_count",
            "planned_full_count",
            "planned_manual_count",
            "planned_defer_count",
        ]
    )


def _local_file_due_reason(
    catalog_source: CatalogSource,
    existing_source: RagSource,
    catalog_file: Path,
) -> dict[str, object] | None:
    if not catalog_source.path:
        return {"reason_code": "LOCAL_FILE_PATH_MISSING"}
    try:
        resolved_path = resolve_catalog_path(catalog_source.path, catalog_file)
        raw_hash = hash_text(resolved_path.read_bytes())
    except OSError as exc:
        return {"reason_code": "LOCAL_FILE_UNAVAILABLE", "error": str(exc)}
    fetch_metadata = _fetch_metadata(existing_source)
    previous_hash = fetch_metadata.get("raw_content_hash")
    if previous_hash != raw_hash:
        return {
            "reason_code": "LOCAL_FILE_FINGERPRINT_CHANGED",
            "origin_uri": str(resolved_path),
            "previous_raw_content_hash": previous_hash,
            "current_raw_content_hash": raw_hash,
        }
    return None


def _url_due_reason(existing_source: RagSource) -> dict[str, object] | None:
    if existing_source.refresh_policy != "scheduled":
        return None
    if existing_source.next_refresh_at is None:
        return {"reason_code": "REFRESH_SCHEDULE_MISSING"}
    now = datetime.now(timezone.utc)
    if existing_source.next_refresh_at <= now:
        return {
            "reason_code": "REFRESH_DUE",
            "next_refresh_at": existing_source.next_refresh_at.isoformat(),
        }
    return None


def _catalog_origin_uri(catalog_source: CatalogSource, catalog_file: Path) -> str | None:
    if catalog_source.acquisition_type == ACQUISITION_LOCAL_FILE and catalog_source.path:
        try:
            return str(resolve_catalog_path(catalog_source.path, catalog_file))
        except OSError:
            return catalog_source.path
    if catalog_source.acquisition_type == ACQUISITION_URL_HTML:
        return catalog_source.url
    return catalog_source.path or catalog_source.url


def _source_catalog_key(source: RagSource) -> str | None:
    value = _fetch_metadata(source).get("catalog_key")
    return str(value) if value else None


def _fetch_metadata(source: RagSource) -> dict[str, object]:
    metadata = source.metadata_ or {}
    fetch_metadata = metadata.get("fetch_metadata") if isinstance(metadata, dict) else None
    return fetch_metadata if isinstance(fetch_metadata, dict) else {}


def _optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _escape_table_value(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
