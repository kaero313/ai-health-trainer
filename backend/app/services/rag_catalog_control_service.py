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
from app.models.rag import RagCatalogPlanItem, RagCatalogPlanRun, RagChunk, RagSource
from app.services.rag_pipeline import CHUNKER_VERSION, NORMALIZATION_VERSION, ChunkPlan
from app.services.rag_service import RAGService


CATALOG_PLAN_MODE = "live_fetch"
ACTION_CREATE = "create_source"
ACTION_SKIP = "skip_refresh"
ACTION_PARTIAL = "partial_refresh"
ACTION_FULL = "full_reindex"
ACTION_MANUAL = "manual_review_required"
ACTION_DEFER = "defer_reembedding"


@dataclass(frozen=True)
class CatalogSource:
    key: str | None
    url: str
    title: str | None
    category: str
    tags: list[str]
    source_type: str
    source_grade: str
    license_value: str | None
    language: str
    author_or_org: str | None
    refresh_policy: str
    refresh_interval_hours: int | None


@dataclass(frozen=True)
class DiffStats:
    added: int = 0
    removed: int = 0
    changed: int = 0
    unchanged: int = 0
    missing_lineage: bool = False

    @property
    def ratio(self) -> float:
        denominator = max(self.added + self.changed + self.unchanged, self.removed + self.changed + self.unchanged, 1)
        return round((self.added + self.removed + self.changed) / denominator, 4)


class RAGCatalogControlService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        self.rag_service = RAGService(db, settings)

    async def create_plan(self, *, catalog_file: str | Path, report_path: str | Path | None = None) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        catalog_path = Path(catalog_file)
        catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog_sources = _load_catalog_sources(catalog_payload)

        run = RagCatalogPlanRun(
            catalog_file=str(catalog_path),
            catalog_version=_optional_int(catalog_payload.get("version")) if isinstance(catalog_payload, dict) else None,
            mode=CATALOG_PLAN_MODE,
            status="running",
            report_path=str(report_path) if report_path else None,
            started_at=started_at,
        )
        self.db.add(run)
        await self.db.flush()

        active_url_sources = await self._load_active_url_sources()
        matched_source_ids: set[int] = set()
        items: list[RagCatalogPlanItem] = []
        for catalog_source in catalog_sources:
            existing_source = self._match_catalog_source(catalog_source, active_url_sources)
            if existing_source:
                matched_source_ids.add(existing_source.id)
            item = await self._plan_catalog_source(run.id, catalog_source, existing_source)
            self.db.add(item)
            items.append(item)

        catalog_urls = {source.url for source in catalog_sources}
        catalog_keys = {source.key for source in catalog_sources if source.key}
        for source in active_url_sources:
            if source.id in matched_source_ids:
                continue
            source_key = _source_catalog_key(source)
            if source.origin_uri in catalog_urls or source.source_url in catalog_urls or source_key in catalog_keys:
                continue
            item = self._plan_orphaned_source(run.id, source)
            self.db.add(item)
            items.append(item)

        await self.db.flush()
        self._apply_run_summary(run, items)
        run.status = "succeeded"
        run.finished_at = datetime.now(timezone.utc)
        await self.db.commit()

        result = await self.get_run(run.id)
        if report_path:
            self.write_plan_report(result, Path(report_path))
        return result

    async def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(RagCatalogPlanRun).order_by(RagCatalogPlanRun.id.desc()).limit(limit)
            )
        ).scalars().all()
        return [self._run_summary(row) for row in rows]

    async def get_run(self, run_id: int) -> dict[str, Any]:
        run = (
            await self.db.execute(
                select(RagCatalogPlanRun)
                .options(selectinload(RagCatalogPlanRun.items))
                .where(RagCatalogPlanRun.id == run_id)
            )
        ).scalar_one_or_none()
        if run is None:
            return {"status": "not_found", "run_id": run_id}
        items = sorted(run.items, key=lambda item: item.id)
        return {"status": "found", "run": self._run_summary(run), "items": [self._item_summary(item) for item in items]}

    async def apply_run(self, *, run_id: int) -> dict[str, Any]:
        run = (
            await self.db.execute(
                select(RagCatalogPlanRun)
                .options(selectinload(RagCatalogPlanRun.items))
                .where(RagCatalogPlanRun.id == run_id)
            )
        ).scalar_one_or_none()
        if run is None:
            return {"status": "not_found", "run_id": run_id}

        run.status = "applying"
        applied = 0
        skipped = 0
        blocked = 0
        stale = 0
        failed = 0
        for item in sorted(run.items, key=lambda row: row.id):
            try:
                item_result = await self._apply_item(item)
            except Exception as exc:  # pragma: no cover - defensive safety net
                item.apply_status = "failed"
                item.apply_error_code = "APPLY_FAILED"
                item.apply_error_message = str(exc)
                failed += 1
                continue

            status = item_result["apply_status"]
            applied += int(status == "applied")
            skipped += int(status == "skipped")
            blocked += int(status == "blocked")
            stale += int(status == "stale")
            failed += int(status == "failed")

        run.status = "applied" if not (failed or stale or blocked) else "applied_with_warnings"
        run.finished_at = datetime.now(timezone.utc)
        run.summary = {**(run.summary or {}), "apply": {"applied": applied, "skipped": skipped, "blocked": blocked, "stale": stale, "failed": failed}}
        await self.db.commit()
        return {"status": run.status, "run_id": run.id, "applied": applied, "skipped": skipped, "blocked": blocked, "stale": stale, "failed": failed}

    async def _plan_catalog_source(
        self,
        run_id: int,
        catalog_source: CatalogSource,
        existing_source: RagSource | None,
    ) -> RagCatalogPlanItem:
        try:
            fetched = await self.rag_service.url_fetcher.fetch(catalog_source.url)
            parsed = self.rag_service._parse_fetched_url(
                fetched,
                title=catalog_source.title,
                extra_metadata={"catalog_key": catalog_source.key, "catalog_file": None},
            )
            plans = self.rag_service._build_chunk_plans(
                parsed,
                source_title=catalog_source.title or parsed.title,
                category=catalog_source.category,
                tags=catalog_source.tags,
                source_grade=catalog_source.source_grade,
                source_version=(existing_source.version + 1) if existing_source else 1,
            )
            old_chunks = await self.rag_service._load_active_source_chunks(existing_source.id) if existing_source else []
            section_diff = _diff_sections(old_chunks, plans)
            chunk_diff = _diff_chunks(old_chunks, plans)
            metadata_changed_fields = _metadata_changed_fields(existing_source, catalog_source)
            quality_warnings = _quality_warnings(parsed.parser_confidence, plans, section_diff, self.settings)
            estimated_embedding_count = self.rag_service._estimate_new_embedding_count(old_chunks, plans)
            estimated_embedding_seconds = estimated_embedding_count * self.settings.RAG_ESTIMATED_EMBEDDING_SECONDS_PER_CHUNK
            action, reason_code, risk_level = self._choose_action(
                existing_source=existing_source,
                parsed_hash=parsed.content_hash,
                metadata_changed_fields=metadata_changed_fields,
                quality_warnings=quality_warnings,
                section_diff=section_diff,
                chunk_diff=chunk_diff,
                estimated_embedding_seconds=estimated_embedding_seconds,
            )
            fetch_metadata = parsed.fetch_metadata or {}
            return RagCatalogPlanItem(
                run_id=run_id,
                source_id=existing_source.id if existing_source else None,
                catalog_key=catalog_source.key,
                catalog_url=catalog_source.url,
                title=catalog_source.title or parsed.title,
                category=catalog_source.category,
                tags=catalog_source.tags,
                license=catalog_source.license_value,
                source_grade=catalog_source.source_grade,
                catalog_status=_catalog_status(existing_source, metadata_changed_fields),
                fetch_status="succeeded",
                parser_confidence=parsed.parser_confidence,
                old_content_hash=existing_source.content_hash if existing_source else None,
                new_content_hash=parsed.content_hash,
                etag_changed=_metadata_changed(existing_source.external_etag if existing_source else None, fetch_metadata.get("etag")),
                last_modified_changed=_metadata_changed(
                    existing_source.external_last_modified.isoformat() if existing_source and existing_source.external_last_modified else None,
                    fetch_metadata.get("last_modified"),
                ),
                metadata_changed_fields=metadata_changed_fields,
                sections_added=section_diff.added,
                sections_removed=section_diff.removed,
                sections_changed=section_diff.changed,
                sections_unchanged=section_diff.unchanged,
                chunks_added=chunk_diff.added,
                chunks_removed=chunk_diff.removed,
                chunks_changed=chunk_diff.changed,
                chunks_unchanged=chunk_diff.unchanged,
                section_change_ratio=section_diff.ratio,
                chunk_change_ratio=chunk_diff.ratio,
                estimated_embedding_seconds=estimated_embedding_seconds,
                quality_warnings=quality_warnings,
                planned_action=action,
                reason_code=reason_code,
                risk_level=risk_level,
                context={
                    "final_url": fetched.final_url,
                    "content_type": fetched.content_type,
                    "raw_content_hash": fetched.raw_content_hash,
                    "parser_version": parsed.parser_version,
                    "chunker_version": CHUNKER_VERSION,
                    "normalization_version": NORMALIZATION_VERSION,
                    "source_type": catalog_source.source_type,
                    "language": catalog_source.language,
                    "author_or_org": catalog_source.author_or_org,
                    "refresh_policy": catalog_source.refresh_policy,
                    "refresh_interval_hours": catalog_source.refresh_interval_hours,
                    "anchor_lineage_missing": section_diff.missing_lineage or chunk_diff.missing_lineage,
                },
            )
        except Exception as exc:
            return RagCatalogPlanItem(
                run_id=run_id,
                source_id=existing_source.id if existing_source else None,
                catalog_key=catalog_source.key,
                catalog_url=catalog_source.url,
                title=catalog_source.title,
                category=catalog_source.category,
                tags=catalog_source.tags,
                license=catalog_source.license_value,
                source_grade=catalog_source.source_grade,
                catalog_status=_catalog_status(existing_source, []),
                fetch_status="failed",
                planned_action=ACTION_MANUAL,
                reason_code="FETCH_OR_PARSE_FAILED",
                risk_level="high",
                quality_warnings=["fetch_or_parse_failed"],
                context={"error": str(exc)},
            )

    def _plan_orphaned_source(self, run_id: int, source: RagSource) -> RagCatalogPlanItem:
        return RagCatalogPlanItem(
            run_id=run_id,
            source_id=source.id,
            catalog_key=_source_catalog_key(source),
            catalog_url=source.origin_uri or source.source_url,
            title=source.title,
            category=source.category,
            tags=list(source.tags or []),
            license=source.license,
            source_grade=source.source_grade,
            catalog_status="orphaned",
            fetch_status="not_applicable",
            old_content_hash=source.content_hash,
            metadata_changed_fields=[],
            planned_action=ACTION_MANUAL,
            reason_code="ORPHANED_SOURCE",
            risk_level="medium",
            quality_warnings=["orphaned_source"],
            context={"message": "Source exists in DB but is absent from catalog"},
        )

    def _choose_action(
        self,
        *,
        existing_source: RagSource | None,
        parsed_hash: str,
        metadata_changed_fields: list[str],
        quality_warnings: list[str],
        section_diff: DiffStats,
        chunk_diff: DiffStats,
        estimated_embedding_seconds: float,
    ) -> tuple[str, str, str]:
        if any(warning in quality_warnings for warning in {"low_parser_confidence", "empty_chunk_plan"}):
            return ACTION_MANUAL, "QUALITY_GATE_FAILED", "high"
        if existing_source is None:
            return ACTION_CREATE, "NEW_CATALOG_SOURCE", "medium"
        if estimated_embedding_seconds > self.settings.RAG_ALLOWED_REEMBEDDING_SECONDS:
            return ACTION_DEFER, "EMBEDDING_BUDGET_EXCEEDED", "medium"
        if section_diff.missing_lineage or chunk_diff.missing_lineage:
            return ACTION_FULL, "ANCHOR_LINEAGE_MISSING", "medium"
        if (
            existing_source.parser_version != "html-parser-v1"
            or existing_source.chunker_version != CHUNKER_VERSION
            or existing_source.normalization_version != NORMALIZATION_VERSION
        ):
            return ACTION_FULL, "PARSER_OR_CHUNKER_CHANGED", "medium"
        if existing_source.content_hash == parsed_hash and not metadata_changed_fields:
            return ACTION_SKIP, "SOURCE_UNCHANGED", "low"
        if max(section_diff.ratio, chunk_diff.ratio) >= self.settings.RAG_PARTIAL_REFRESH_CHANGE_RATIO:
            return ACTION_FULL, "LARGE_CONTENT_CHANGE", "medium"
        if metadata_changed_fields and existing_source.content_hash == parsed_hash:
            return ACTION_PARTIAL, "METADATA_CHANGED", "low"
        return ACTION_PARTIAL, "SMALL_CONTENT_CHANGE", "low"

    async def _apply_item(self, item: RagCatalogPlanItem) -> dict[str, Any]:
        if item.planned_action == ACTION_SKIP:
            item.apply_status = "skipped"
            item.applied_at = datetime.now(timezone.utc)
            return {"apply_status": item.apply_status}
        if item.planned_action in {ACTION_MANUAL, ACTION_DEFER}:
            item.apply_status = "blocked"
            item.applied_at = datetime.now(timezone.utc)
            return {"apply_status": item.apply_status}
        if not item.catalog_url:
            item.apply_status = "blocked"
            item.apply_error_code = "CATALOG_URL_MISSING"
            item.applied_at = datetime.now(timezone.utc)
            return {"apply_status": item.apply_status}

        fetched = await self.rag_service.url_fetcher.fetch(item.catalog_url)
        parsed = self.rag_service._parse_fetched_url(
            fetched,
            title=item.title,
            extra_metadata={"catalog_key": item.catalog_key},
        )
        if parsed.content_hash != item.new_content_hash:
            item.apply_status = "stale"
            item.apply_error_code = "PLAN_STALE"
            item.apply_error_message = "Remote content hash differs from the stored plan"
            item.applied_at = datetime.now(timezone.utc)
            return {"apply_status": item.apply_status}

        existing_source = await self.rag_service._find_existing_url_source(item.catalog_url, fetched.final_url)
        result = await self.rag_service._ingest_parsed_document(
            parsed=parsed,
            title=item.title or parsed.title,
            category=item.category or "general",
            source_url=fetched.final_url,
            origin_type="url_html",
            origin_uri=item.catalog_url,
            tags=list(item.tags or []),
            source_type=str(item.context.get("source_type") or "official_guideline"),
            source_grade=item.source_grade or "A",
            license_value=item.license,
            language=str(item.context.get("language") or "en"),
            author_or_org=_optional_str(item.context.get("author_or_org")),
            refresh_policy=str(item.context.get("refresh_policy") or "scheduled"),
            refresh_interval_hours=_optional_int(item.context.get("refresh_interval_hours")),
            existing_source=existing_source,
            force=item.planned_action in {ACTION_PARTIAL, ACTION_FULL},
            force_full_reindex=item.planned_action == ACTION_FULL,
        )
        item.apply_status = "applied"
        item.applied_job_id = _optional_int(result.get("job_id"))
        item.source_id = _optional_int(result.get("source_id")) or item.source_id
        item.applied_at = datetime.now(timezone.utc)
        return {"apply_status": item.apply_status}

    async def _load_active_url_sources(self) -> list[RagSource]:
        return (
            await self.db.execute(
                select(RagSource)
                .where(RagSource.status == "active", RagSource.origin_type == "url_html")
                .order_by(RagSource.id.asc())
            )
        ).scalars().all()

    @staticmethod
    def _match_catalog_source(catalog_source: CatalogSource, sources: list[RagSource]) -> RagSource | None:
        for source in sources:
            if catalog_source.key and _source_catalog_key(source) == catalog_source.key:
                return source
        for source in sources:
            if catalog_source.url in {source.origin_uri, source.source_url}:
                return source
        return None

    @staticmethod
    def _apply_run_summary(run: RagCatalogPlanRun, items: list[RagCatalogPlanItem]) -> None:
        actions = [item.planned_action for item in items]
        run.total_sources = len(items)
        run.missing_count = sum(1 for item in items if item.catalog_status == "missing")
        run.matched_count = sum(1 for item in items if item.catalog_status in {"matched", "metadata_changed"})
        run.orphaned_count = sum(1 for item in items if item.catalog_status == "orphaned")
        run.metadata_changed_count = sum(1 for item in items if item.metadata_changed_fields)
        run.content_changed_count = sum(1 for item in items if item.old_content_hash != item.new_content_hash)
        run.quality_warning_count = sum(1 for item in items if item.quality_warnings)
        run.planned_create_count = actions.count(ACTION_CREATE)
        run.planned_skip_count = actions.count(ACTION_SKIP)
        run.planned_partial_count = actions.count(ACTION_PARTIAL)
        run.planned_full_count = actions.count(ACTION_FULL)
        run.planned_manual_count = actions.count(ACTION_MANUAL)
        run.planned_defer_count = actions.count(ACTION_DEFER)
        run.summary = {
            "actions": {
                ACTION_CREATE: run.planned_create_count,
                ACTION_SKIP: run.planned_skip_count,
                ACTION_PARTIAL: run.planned_partial_count,
                ACTION_FULL: run.planned_full_count,
                ACTION_MANUAL: run.planned_manual_count,
                ACTION_DEFER: run.planned_defer_count,
            }
        }

    @staticmethod
    def _run_summary(run: RagCatalogPlanRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "catalog_file": run.catalog_file,
            "catalog_version": run.catalog_version,
            "mode": run.mode,
            "status": run.status,
            "report_path": run.report_path,
            "total_sources": run.total_sources,
            "missing_count": run.missing_count,
            "matched_count": run.matched_count,
            "orphaned_count": run.orphaned_count,
            "metadata_changed_count": run.metadata_changed_count,
            "content_changed_count": run.content_changed_count,
            "quality_warning_count": run.quality_warning_count,
            "planned_create_count": run.planned_create_count,
            "planned_skip_count": run.planned_skip_count,
            "planned_partial_count": run.planned_partial_count,
            "planned_full_count": run.planned_full_count,
            "planned_manual_count": run.planned_manual_count,
            "planned_defer_count": run.planned_defer_count,
            "summary": run.summary,
            "started_at": _dt(run.started_at),
            "finished_at": _dt(run.finished_at),
            "created_at": _dt(run.created_at),
        }

    @staticmethod
    def _item_summary(item: RagCatalogPlanItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "run_id": item.run_id,
            "source_id": item.source_id,
            "catalog_key": item.catalog_key,
            "catalog_url": item.catalog_url,
            "title": item.title,
            "category": item.category,
            "catalog_status": item.catalog_status,
            "fetch_status": item.fetch_status,
            "parser_confidence": item.parser_confidence,
            "metadata_changed_fields": item.metadata_changed_fields,
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
            "estimated_embedding_seconds": item.estimated_embedding_seconds,
            "quality_warnings": item.quality_warnings,
            "planned_action": item.planned_action,
            "reason_code": item.reason_code,
            "risk_level": item.risk_level,
            "apply_status": item.apply_status,
            "applied_job_id": item.applied_job_id,
            "applied_at": _dt(item.applied_at),
            "apply_error_code": item.apply_error_code,
            "apply_error_message": item.apply_error_message,
            "context": item.context,
        }

    @staticmethod
    def write_plan_report(plan: dict[str, Any], report_path: Path) -> None:
        run = plan.get("run", {})
        items = plan.get("items", [])
        lines = [
            "# RAG Catalog Plan Report",
            "",
            f"- run_id: {run.get('id')}",
            f"- status: {run.get('status')}",
            f"- mode: {run.get('mode')}",
            f"- total_sources: {run.get('total_sources')}",
            f"- planned_create: {run.get('planned_create_count')}",
            f"- planned_skip: {run.get('planned_skip_count')}",
            f"- planned_partial: {run.get('planned_partial_count')}",
            f"- planned_full: {run.get('planned_full_count')}",
            f"- planned_manual: {run.get('planned_manual_count')}",
            f"- planned_defer: {run.get('planned_defer_count')}",
            "",
            "## Items",
            "",
            "| Source | Status | Action | Reason | Section Ratio | Chunk Ratio | Warnings |",
            "|--------|--------|--------|--------|---------------|-------------|----------|",
        ]
        for item in items:
            lines.append(
                "| {title} | {catalog_status} | {planned_action} | {reason_code} | {section_ratio} | {chunk_ratio} | {warnings} |".format(
                    title=_escape_pipe(str(item.get("title") or item.get("catalog_key") or "")),
                    catalog_status=item.get("catalog_status"),
                    planned_action=item.get("planned_action"),
                    reason_code=item.get("reason_code"),
                    section_ratio=(item.get("sections") or {}).get("change_ratio"),
                    chunk_ratio=(item.get("chunks") or {}).get("change_ratio"),
                    warnings=", ".join(item.get("quality_warnings") or []),
                )
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _load_catalog_sources(payload: Any) -> list[CatalogSource]:
    raw_sources = payload.get("sources", []) if isinstance(payload, dict) else payload
    if not isinstance(raw_sources, list):
        raise ValueError("Catalog file must contain a sources list")
    return [
        CatalogSource(
            key=source.get("key"),
            url=source["url"],
            title=source.get("title"),
            category=source["category"],
            tags=list(source.get("tags") or []),
            source_type=source.get("source_type", "official_guideline"),
            source_grade=source.get("source_grade", "A"),
            license_value=source.get("license"),
            language=source.get("language", "en"),
            author_or_org=source.get("author_or_org"),
            refresh_policy=source.get("refresh_policy", "scheduled"),
            refresh_interval_hours=_optional_int(source.get("refresh_interval_hours")),
        )
        for source in raw_sources
    ]


def _diff_sections(old_chunks: list[RagChunk], new_plans: list[ChunkPlan]) -> DiffStats:
    old_map = _hash_map(old_chunks, anchor_key="parent_anchor_hash", content_key="parent_content_hash")
    new_map = _plan_hash_map(new_plans, anchor_key="parent_anchor_hash", content_key="parent_content_hash")
    return _diff_hash_maps(old_map, new_map, missing_lineage=_missing_lineage(old_chunks, new_plans, "parent_anchor_hash"))


def _diff_chunks(old_chunks: list[RagChunk], new_plans: list[ChunkPlan]) -> DiffStats:
    old_map = _hash_map(old_chunks, anchor_key="chunk_anchor_hash", content_key="chunk_content_hash")
    new_map = _plan_hash_map(new_plans, anchor_key="chunk_anchor_hash", content_key="chunk_content_hash")
    return _diff_hash_maps(old_map, new_map, missing_lineage=_missing_lineage(old_chunks, new_plans, "chunk_anchor_hash"))


def _hash_map(chunks: list[RagChunk], *, anchor_key: str, content_key: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for chunk in chunks:
        metadata = chunk.metadata_ or {}
        anchor = metadata.get(anchor_key)
        content_hash = metadata.get(content_key) or chunk.content_hash
        if anchor:
            mapping[str(anchor)] = str(content_hash)
    return mapping


def _plan_hash_map(plans: list[ChunkPlan], *, anchor_key: str, content_key: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for plan in plans:
        anchor = plan.metadata.get(anchor_key)
        content_hash = plan.metadata.get(content_key) or plan.content_hash
        if anchor:
            mapping[str(anchor)] = str(content_hash)
    return mapping


def _diff_hash_maps(old_map: dict[str, str], new_map: dict[str, str], *, missing_lineage: bool) -> DiffStats:
    old_keys = set(old_map)
    new_keys = set(new_map)
    common = old_keys.intersection(new_keys)
    changed = sum(1 for key in common if old_map[key] != new_map[key])
    unchanged = len(common) - changed
    return DiffStats(
        added=len(new_keys - old_keys),
        removed=len(old_keys - new_keys),
        changed=changed,
        unchanged=unchanged,
        missing_lineage=missing_lineage,
    )


def _missing_lineage(old_chunks: list[RagChunk], new_plans: list[ChunkPlan], key: str) -> bool:
    if not old_chunks or not new_plans:
        return False
    return any(not (chunk.metadata_ or {}).get(key) for chunk in old_chunks) or any(
        not plan.metadata.get(key) for plan in new_plans
    )


def _metadata_changed_fields(source: RagSource | None, catalog_source: CatalogSource) -> list[str]:
    if source is None:
        return []
    comparisons = {
        "title": (source.title, catalog_source.title),
        "category": (source.category, catalog_source.category),
        "tags": (list(source.tags or []), catalog_source.tags),
        "license": (source.license, catalog_source.license_value),
        "source_grade": (source.source_grade, catalog_source.source_grade),
        "source_type": (source.source_type, catalog_source.source_type),
        "language": (source.language, catalog_source.language),
        "author_or_org": (source.author_or_org, catalog_source.author_or_org),
        "refresh_policy": (source.refresh_policy, catalog_source.refresh_policy),
        "refresh_interval_hours": (source.refresh_interval_hours, catalog_source.refresh_interval_hours),
    }
    return [field for field, (left, right) in comparisons.items() if left != right]


def _catalog_status(source: RagSource | None, metadata_changed_fields: list[str]) -> str:
    if source is None:
        return "missing"
    if metadata_changed_fields:
        return "metadata_changed"
    return "matched"


def _quality_warnings(parser_confidence: float, plans: list[ChunkPlan], section_diff: DiffStats, settings: Settings) -> list[str]:
    warnings: list[str] = []
    if parser_confidence < settings.RAG_PARSER_CONFIDENCE_THRESHOLD:
        warnings.append("low_parser_confidence")
    if not plans:
        warnings.append("empty_chunk_plan")
    if section_diff.missing_lineage:
        warnings.append("anchor_lineage_missing")
    return warnings


def _source_catalog_key(source: RagSource) -> str | None:
    metadata = source.metadata_ or {}
    fetch_metadata = metadata.get("fetch_metadata") if isinstance(metadata, dict) else None
    if isinstance(fetch_metadata, dict):
        value = fetch_metadata.get("catalog_key")
        return str(value) if value else None
    return None


def _metadata_changed(previous: object, current: object) -> bool:
    if previous in {None, ""} and current in {None, ""}:
        return False
    return previous != current


def _optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)


def _optional_str(value: object) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _escape_pipe(value: str) -> str:
    return value.replace("|", "\\|")
