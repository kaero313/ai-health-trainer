from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.rag import RagSource, RagSourceReplacementCandidate
from app.services.rag_pipeline import CHUNKER_VERSION, NORMALIZATION_VERSION, ParsedDocument
from app.services.rag_service import RAGService
from app.services.rag_source_acquisition import FetchedUrlContent
from app.services.rag_source_adapters import (
    ACQUISITION_PDF_URL,
    ACQUISITION_URL_HTML,
    CatalogSource,
    load_catalog_sources,
)


STATUS_PREVIEW_SUCCEEDED = "preview_succeeded"
STATUS_FETCH_FAILED = "fetch_failed"
STATUS_PARSE_FAILED = "parse_failed"
STATUS_MANUAL_REVIEW = "manual_review_required"


class RAGReplacementCandidateService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        self.rag_service = RAGService(db, settings)

    async def preview(
        self,
        *,
        catalog_file: str | Path,
        key: str,
        candidate_url: str,
        acquisition_type: str = "auto",
        title: str | None = None,
        source_grade: str | None = None,
        license_value: str | None = None,
        author_or_org: str | None = None,
        report_path: str | Path | None = None,
    ) -> dict[str, Any]:
        catalog_path = Path(catalog_file)
        catalog_source = _load_catalog_source_by_key(catalog_path, key)
        if catalog_source is None:
            return {"status": "not_found", "catalog_file": str(catalog_path), "catalog_key": key}

        existing_source = await self._find_existing_source(catalog_source)
        resolved_acquisition_type = _resolve_acquisition_type(acquisition_type, candidate_url)
        candidate_source = _candidate_catalog_source(
            catalog_source,
            candidate_url=candidate_url,
            acquisition_type=resolved_acquisition_type,
            title=title,
            source_grade=source_grade,
            license_value=license_value,
            author_or_org=author_or_org,
        )

        candidate = RagSourceReplacementCandidate(
            source_id=existing_source.id if existing_source else None,
            catalog_key=catalog_source.key,
            original_url=catalog_source.url or (existing_source.origin_uri if existing_source else None),
            candidate_url=candidate_url,
            acquisition_type=resolved_acquisition_type,
            status=STATUS_FETCH_FAILED,
            source_grade=candidate_source.source_grade,
            license=candidate_source.license_value,
            author_or_org=candidate_source.author_or_org,
            report_path=str(report_path) if report_path else None,
            context={
                "catalog_file": str(catalog_path),
                "catalog_title": catalog_source.title,
                "catalog_category": catalog_source.category,
                "catalog_tags": catalog_source.tags,
                "existing_source_id": existing_source.id if existing_source else None,
                "no_mutation_performed": True,
            },
        )

        try:
            fetched = await self._fetch_candidate(candidate_source)
        except Exception as exc:
            candidate.status = STATUS_FETCH_FAILED
            candidate.quality_warnings = ["candidate_fetch_failed"]
            candidate.context = {**candidate.context, "error": str(exc)}
            return await self._persist_and_report(candidate, report_path)

        _apply_fetched_metadata(candidate, fetched)
        try:
            parsed = self._parse_candidate(candidate_source, fetched)
            plans = self.rag_service._build_chunk_plans(
                parsed,
                source_title=title or candidate_source.title or parsed.title,
                category=candidate_source.category,
                tags=candidate_source.tags,
                source_grade=candidate_source.source_grade,
                source_version=(existing_source.version + 1) if existing_source else 1,
            )
        except Exception as exc:
            candidate.status = STATUS_PARSE_FAILED
            candidate.quality_warnings = ["candidate_parse_failed"]
            candidate.context = {**candidate.context, "error": str(exc)}
            return await self._persist_and_report(candidate, report_path)

        warnings = _quality_warnings(parsed, len(plans), self.settings)
        candidate.status = STATUS_MANUAL_REVIEW if warnings else STATUS_PREVIEW_SUCCEEDED
        candidate.parser_type = parsed.parser_type
        candidate.parser_confidence = parsed.parser_confidence
        candidate.content_hash = parsed.content_hash
        candidate.section_count = len(parsed.sections)
        candidate.chunk_count = len(plans)
        candidate.quality_warnings = warnings
        candidate.context = {
            **candidate.context,
            "final_url": fetched.final_url,
            "parser_version": parsed.parser_version,
            "chunker_version": CHUNKER_VERSION,
            "normalization_version": NORMALIZATION_VERSION,
            "source_title": title or candidate_source.title or parsed.title,
            "chunk_preview": [
                {
                    "chunk_index": plan.chunk_index,
                    "title": plan.title,
                    "content_hash": plan.content_hash,
                    "token_count": plan.token_count,
                    "preview": plan.content[:240],
                }
                for plan in plans[:10]
            ],
            "no_mutation_performed": True,
        }
        return await self._persist_and_report(candidate, report_path)

    async def _persist_and_report(
        self,
        candidate: RagSourceReplacementCandidate,
        report_path: str | Path | None,
    ) -> dict[str, Any]:
        self.db.add(candidate)
        await self.db.flush()
        result = self._candidate_summary(candidate)
        await self.db.commit()
        if report_path:
            self.write_preview_report(result, Path(report_path))
        return result

    async def _find_existing_source(self, catalog_source: CatalogSource) -> RagSource | None:
        rows = (
            await self.db.execute(
                select(RagSource)
                .where(RagSource.status == "active")
                .order_by(RagSource.id.asc())
            )
        ).scalars().all()
        for source in rows:
            metadata = source.metadata_ or {}
            fetch_metadata = metadata.get("fetch_metadata") if isinstance(metadata, dict) else None
            if isinstance(fetch_metadata, dict) and fetch_metadata.get("catalog_key") == catalog_source.key:
                return source
        for source in rows:
            if catalog_source.url and catalog_source.url in {source.origin_uri, source.source_url}:
                return source
        return None

    async def _fetch_candidate(self, candidate_source: CatalogSource) -> FetchedUrlContent:
        if candidate_source.acquisition_type == ACQUISITION_PDF_URL:
            return await self.rag_service.url_fetcher.fetch_pdf(candidate_source.url or "")
        return await self.rag_service.url_fetcher.fetch(candidate_source.url or "")

    def _parse_candidate(self, candidate_source: CatalogSource, fetched: FetchedUrlContent) -> ParsedDocument:
        if candidate_source.acquisition_type == ACQUISITION_PDF_URL:
            temp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_file.write(fetched.raw_content)
                    temp_path = Path(temp_file.name)
                parsed = self.rag_service.parser.parse_file(temp_path, parser_type="pdf_text")
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
            title = candidate_source.title or parsed.title
            return replace(
                parsed,
                title=title,
                source_uri=fetched.final_url,
                sections=[
                    replace(
                        section,
                        title=f"{title} page {section.page_number}" if section.page_number else title,
                        source_url=fetched.final_url,
                        source_content_type=fetched.content_type,
                    )
                    for section in parsed.sections
                ],
                fetch_metadata={
                    **fetched.metadata(),
                    "parser_type": parsed.parser_type,
                    "origin_type": "url_pdf",
                },
            )
        return self.rag_service._parse_fetched_url(fetched, title=candidate_source.title)

    @staticmethod
    def _candidate_summary(candidate: RagSourceReplacementCandidate) -> dict[str, Any]:
        return {
            "id": candidate.id,
            "source_id": candidate.source_id,
            "catalog_key": candidate.catalog_key,
            "original_url": candidate.original_url,
            "candidate_url": candidate.candidate_url,
            "acquisition_type": candidate.acquisition_type,
            "status": candidate.status,
            "parser_type": candidate.parser_type,
            "parser_confidence": candidate.parser_confidence,
            "content_hash": candidate.content_hash,
            "raw_content_hash": candidate.raw_content_hash,
            "content_type": candidate.content_type,
            "content_length": candidate.content_length,
            "etag": candidate.etag,
            "last_modified": candidate.last_modified,
            "section_count": candidate.section_count,
            "chunk_count": candidate.chunk_count,
            "source_grade": candidate.source_grade,
            "license": candidate.license,
            "author_or_org": candidate.author_or_org,
            "quality_warnings": candidate.quality_warnings,
            "context": candidate.context,
            "report_path": candidate.report_path,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        }

    @staticmethod
    def write_preview_report(result: dict[str, Any], report_path: Path) -> None:
        lines = [
            "# RAG Replacement Candidate Preview",
            "",
            "> This report is preview/audit only. No RAG source, chunk, embedding, OpenSearch index, or catalog JSON mutation was performed.",
            "",
            "## Summary",
            "",
            f"- candidate_id: {result.get('id')}",
            f"- catalog_key: {result.get('catalog_key')}",
            f"- status: {result.get('status')}",
            f"- acquisition_type: {result.get('acquisition_type')}",
            f"- source_id: {result.get('source_id')}",
            "",
            "## Original Source",
            "",
            f"- original_url: {result.get('original_url') or ''}",
            "",
            "## Candidate Source",
            "",
            f"- candidate_url: {result.get('candidate_url')}",
            f"- final_url: {(result.get('context') or {}).get('final_url') or ''}",
            f"- content_type: {result.get('content_type') or ''}",
            f"- content_length: {result.get('content_length') or ''}",
            f"- etag: {result.get('etag') or ''}",
            f"- last_modified: {result.get('last_modified') or ''}",
            f"- raw_content_hash: {result.get('raw_content_hash') or ''}",
            f"- content_hash: {result.get('content_hash') or ''}",
            "",
            "## Parser And Chunk Preview",
            "",
            f"- parser_type: {result.get('parser_type') or ''}",
            f"- parser_confidence: {result.get('parser_confidence') if result.get('parser_confidence') is not None else ''}",
            f"- section_count: {result.get('section_count')}",
            f"- chunk_count: {result.get('chunk_count')}",
            f"- quality_warnings: {', '.join(result.get('quality_warnings') or [])}",
            "",
            "## Chunk Samples",
            "",
        ]
        for item in (result.get("context") or {}).get("chunk_preview", []):
            lines.extend(
                [
                    f"### {item.get('title')}",
                    "",
                    f"- chunk_index: {item.get('chunk_index')}",
                    f"- content_hash: {item.get('content_hash')}",
                    f"- token_count: {item.get('token_count')}",
                    "",
                    str(item.get("preview") or ""),
                    "",
                ]
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _load_catalog_source_by_key(catalog_path: Path, key: str) -> CatalogSource | None:
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    for source in load_catalog_sources(payload):
        if source.key == key:
            return source
    return None


def _candidate_catalog_source(
    source: CatalogSource,
    *,
    candidate_url: str,
    acquisition_type: str,
    title: str | None,
    source_grade: str | None,
    license_value: str | None,
    author_or_org: str | None,
) -> CatalogSource:
    return CatalogSource(
        key=source.key,
        acquisition_type=acquisition_type,
        url=candidate_url,
        path=None,
        parser_type="pdf_text" if acquisition_type == ACQUISITION_PDF_URL else "html",
        title=title or source.title,
        category=source.category,
        tags=source.tags,
        source_type=source.source_type,
        source_grade=source_grade or source.source_grade,
        license_value=license_value if license_value is not None else source.license_value,
        language=source.language,
        author_or_org=author_or_org if author_or_org is not None else source.author_or_org,
        refresh_policy=source.refresh_policy,
        refresh_interval_hours=source.refresh_interval_hours,
        curation_method=source.curation_method,
        reference_urls=[candidate_url],
    )


def _resolve_acquisition_type(acquisition_type: str, candidate_url: str) -> str:
    if acquisition_type != "auto":
        return acquisition_type
    path = urlparse(candidate_url).path.lower()
    return ACQUISITION_PDF_URL if path.endswith(".pdf") else ACQUISITION_URL_HTML


def _apply_fetched_metadata(candidate: RagSourceReplacementCandidate, fetched: FetchedUrlContent) -> None:
    metadata = fetched.metadata()
    candidate.raw_content_hash = str(metadata["raw_content_hash"])
    candidate.content_type = str(metadata["content_type"]) if metadata.get("content_type") else None
    candidate.content_length = int(metadata["content_length"])
    candidate.etag = str(metadata["etag"]) if metadata.get("etag") else None
    candidate.last_modified = str(metadata["last_modified"]) if metadata.get("last_modified") else None
    candidate.context = {
        **candidate.context,
        "requested_url": metadata["requested_url"],
        "final_url": metadata["final_url"],
        "fetched_at": metadata["fetched_at"],
    }


def _quality_warnings(parsed: ParsedDocument, chunk_count: int, settings: Settings) -> list[str]:
    warnings: list[str] = []
    if parsed.parser_confidence < settings.RAG_PARSER_CONFIDENCE_THRESHOLD:
        warnings.append("low_parser_confidence")
    if chunk_count == 0:
        warnings.append("empty_chunk_plan")
    return warnings
