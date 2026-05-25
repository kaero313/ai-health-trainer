from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.rag import RagCatalogPlanItem, RagChunk, RagIngestJob, RagReviewRun, RagSource
from app.services.rag_catalog_control_service import RAGCatalogControlService
from app.services.rag_pipeline import CHUNKER_VERSION, NORMALIZATION_VERSION
from app.services.rag_review_service import RAGReviewService
from app.services.rag_source_acquisition import FetchedUrlContent


def _embedding(value: float = 0.1) -> list[float]:
    return [value] * 3072


class FakeUrlFetcher:
    def __init__(self, *html_values: str, pdf_values: list[bytes] | None = None):
        self.html_values = list(html_values)
        self.pdf_values = list(pdf_values or [])

    async def fetch(self, url: str) -> FetchedUrlContent:
        if len(self.html_values) > 1:
            html = self.html_values.pop(0)
        else:
            html = self.html_values[0]
        return FetchedUrlContent(
            requested_url=url,
            final_url=url,
            content_type="text/html; charset=utf-8",
            etag='"v1"',
            last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
            fetched_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            raw_content=html.encode("utf-8"),
            text=html,
        )

    async def fetch_pdf(self, url: str) -> FetchedUrlContent:
        if len(self.pdf_values) > 1:
            pdf = self.pdf_values.pop(0)
        else:
            pdf = self.pdf_values[0]
        return FetchedUrlContent(
            requested_url=url,
            final_url=url,
            content_type="application/pdf",
            etag='"pdf-v1"',
            last_modified="Mon, 28 Oct 2024 22:44:41 GMT",
            fetched_at=datetime(2024, 10, 28, tzinfo=timezone.utc),
            raw_content=pdf,
            text="",
        )


class FailingUrlFetcher:
    async def fetch(self, url: str) -> FetchedUrlContent:
        raise RuntimeError("HTTP 403")

    async def fetch_pdf(self, url: str) -> FetchedUrlContent:
        raise RuntimeError("HTTP 403")


def _html(*section_bodies: str) -> str:
    sections = []
    for index, body in enumerate(section_bodies, start=1):
        sections.append(f"<h2>Section {index}</h2><p>{body}</p>")
    return "<html><body><main><h1>Guide</h1>" + "".join(sections) + "</main></body></html>"


def _catalog_file(tmp_path, *, url: str = "https://example.org/guide", title: str = "Official Guide"):
    path = tmp_path / "catalog.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "key": "official_guide",
                        "url": url,
                        "title": title,
                        "category": "exercise",
                        "tags": ["guideline"],
                        "source_type": "official_guideline",
                        "source_grade": "A",
                        "license": "official-webpage",
                        "language": "en",
                        "author_or_org": "Example Org",
                        "refresh_policy": "scheduled",
                        "refresh_interval_hours": 720,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _disabled_catalog_file(tmp_path):
    path = tmp_path / "disabled_catalog.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "key": "blocked_source",
                        "url": "https://example.org/blocked",
                        "title": "Blocked Source",
                        "category": "supplement",
                        "tags": ["blocked"],
                        "source_type": "official_guideline",
                        "source_grade": "A",
                        "license": "official-webpage",
                        "language": "en",
                        "author_or_org": "Example Org",
                        "refresh_policy": "scheduled",
                        "refresh_interval_hours": 720,
                        "enabled": False,
                        "failure_policy": "replacement_required",
                        "max_consecutive_failures": 2,
                        "disabled_reason": "HTTP 403 in backend runtime",
                        "manual_curation_fallback": "Use reviewed internal summary until replacement is active.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _failure_policy_catalog_file(tmp_path):
    path = tmp_path / "failure_policy_catalog.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "key": "blocked_source",
                        "url": "https://example.org/blocked",
                        "title": "Blocked Source",
                        "category": "supplement",
                        "tags": ["blocked"],
                        "source_type": "official_guideline",
                        "source_grade": "A",
                        "license": "official-webpage",
                        "language": "en",
                        "author_or_org": "Example Org",
                        "refresh_policy": "scheduled",
                        "refresh_interval_hours": 720,
                        "failure_policy": "replacement_required",
                        "max_consecutive_failures": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _pdf_catalog_file(tmp_path, *, url: str = "https://example.org/guide.pdf"):
    path = tmp_path / "pdf_catalog.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "key": "official_pdf",
                        "acquisition_type": "pdf_url",
                        "url": url,
                        "parser_type": "pdf_text",
                        "title": "Official PDF",
                        "category": "exercise",
                        "tags": ["guideline", "pdf"],
                        "source_type": "official_guideline",
                        "source_grade": "A",
                        "license": "official-pdf",
                        "language": "en",
                        "author_or_org": "Example Org",
                        "refresh_policy": "scheduled",
                        "refresh_interval_hours": 720,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _mixed_pdf_and_missing_file_catalog(tmp_path, *, url: str = "https://example.org/guide.pdf"):
    path = tmp_path / "mixed_catalog.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "key": "official_pdf",
                        "acquisition_type": "pdf_url",
                        "url": url,
                        "parser_type": "pdf_text",
                        "title": "Official PDF",
                        "category": "exercise",
                        "tags": ["guideline", "pdf"],
                        "source_type": "official_guideline",
                        "source_grade": "A",
                        "license": "official-pdf",
                        "language": "en",
                        "author_or_org": "Example Org",
                        "refresh_policy": "scheduled",
                        "refresh_interval_hours": 720,
                    },
                    {
                        "key": "missing_local_document",
                        "acquisition_type": "local_file",
                        "path": "missing.md",
                        "parser_type": "markdown",
                        "title": "Missing Local Document",
                        "category": "exercise",
                        "tags": ["missing"],
                        "source_type": "curated_internal_summary",
                        "source_grade": "B",
                        "license": "internal-summary",
                        "language": "ko",
                        "author_or_org": "AI Health Trainer",
                        "refresh_policy": "manual",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _document_catalog_file(tmp_path, *, file_name: str, parser_type: str = "markdown"):
    path = tmp_path / "document_catalog.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "key": "local_document",
                        "acquisition_type": "local_file",
                        "path": file_name,
                        "parser_type": parser_type,
                        "title": "Local Document",
                        "category": "nutrition",
                        "tags": ["local", "fixture"],
                        "source_type": "curated_internal_summary",
                        "source_grade": "B",
                        "license": "internal-summary",
                        "language": "en",
                        "author_or_org": "AI Health Trainer",
                        "curation_method": "internal fixture",
                        "reference_urls": ["https://example.org/reference"],
                        "refresh_policy": "manual",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _markdown_sections(*bodies: str) -> str:
    sections = []
    for index, body in enumerate(bodies, start=1):
        sections.append(f"## Section {index}\n\n{body}")
    return "# Local Guide\n\n" + "\n\n".join(sections)


def _synthetic_text_pdf(text_value: str) -> bytes:
    stream = f"BT\n/F1 12 Tf\n72 720 Td\n({text_value}) Tj\nET\n".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
    ]
    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    cursor = len(chunks[0])
    for index, obj in enumerate(objects, start=1):
        offsets.append(cursor)
        part = f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
        chunks.append(part)
        cursor += len(part)
    xref_offset = cursor
    xref = [b"xref\n", f"0 {len(objects) + 1}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer\n<< /Root 1 0 R /Size {len(objects) + 1} >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return b"".join(chunks + xref + [trailer])


async def _review_plan(db_session, plan_id: int) -> int:
    result = await RAGReviewService(db_session, get_settings()).review_catalog_plan(run_id=plan_id)
    return int(result["run"]["id"])


@pytest.mark.asyncio
async def test_catalog_plan_persists_missing_source_and_apply_creates_job(db_session, tmp_path):
    html = _html("Adults should move regularly for health.", "Strength training supports muscles.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html, html)
    service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    catalog_path = _catalog_file(tmp_path)

    plan = await service.create_plan(catalog_file=catalog_path)
    item = plan["items"][0]

    assert item["catalog_status"] == "missing"
    assert item["planned_action"] == "create_source"
    assert item["reason_code"] == "NEW_CATALOG_SOURCE"
    source_count = await db_session.scalar(select(func.count()).select_from(RagSource))
    job_count = await db_session.scalar(select(func.count()).select_from(RagIngestJob))

    assert source_count == 0
    assert job_count == 0

    review_id = await _review_plan(db_session, plan["run"]["id"])
    apply_result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)
    stored_item = (await db_session.execute(select(RagCatalogPlanItem))).scalar_one()
    source = (await db_session.execute(select(RagSource))).scalar_one()
    job = (await db_session.execute(select(RagIngestJob))).scalar_one()

    assert apply_result["applied"] == 1
    assert stored_item.apply_status == "applied"
    assert stored_item.applied_job_id == job.id
    assert stored_item.source_id == source.id
    assert source.metadata_["fetch_metadata"]["catalog_key"] == "official_guide"


@pytest.mark.asyncio
async def test_catalog_plan_skips_disabled_source_without_fetching(db_session, tmp_path):
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher()

    plan = await service.create_plan(catalog_file=_disabled_catalog_file(tmp_path))
    item = plan["items"][0]

    assert item["fetch_status"] == "skipped"
    assert item["planned_action"] == "manual_review_required"
    assert item["reason_code"] == "SOURCE_DISABLED"
    assert item["quality_warnings"] == ["source_disabled"]
    assert item["context"]["failure_lifecycle"]["enabled"] is False
    assert item["context"]["failure_lifecycle"]["disabled_reason"] == "HTTP 403 in backend runtime"


@pytest.mark.asyncio
async def test_catalog_plan_escalates_repeated_fetch_failures_to_replacement_required(db_session, tmp_path):
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FailingUrlFetcher()
    catalog_path = _failure_policy_catalog_file(tmp_path)

    first_plan = await service.create_plan(catalog_file=catalog_path)
    first_item = first_plan["items"][0]
    second_plan = await service.create_plan(catalog_file=catalog_path)
    second_item = second_plan["items"][0]

    assert first_item["reason_code"] == "FETCH_OR_PARSE_FAILED"
    assert first_item["context"]["failure_lifecycle"]["consecutive_failure_count"] == 1
    assert second_item["reason_code"] == "REPLACEMENT_REQUIRED"
    assert "replacement_required" in second_item["quality_warnings"]
    assert second_item["context"]["failure_lifecycle"]["previous_failure_count"] == 1
    assert second_item["context"]["failure_lifecycle"]["consecutive_failure_count"] == 2
    assert second_item["context"]["failure_lifecycle"]["threshold_reached"] is True


@pytest.mark.asyncio
async def test_pdf_url_catalog_plan_and_apply_create_source(db_session, tmp_path):
    pdf_bytes = _synthetic_text_pdf("Official PDF URL catalog fixture.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(pdf_values=[pdf_bytes, pdf_bytes])
    service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    catalog_path = _pdf_catalog_file(tmp_path)

    plan = await service.create_plan(catalog_file=catalog_path)
    item = plan["items"][0]
    review_id = await _review_plan(db_session, plan["run"]["id"])
    apply_result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)
    source = (await db_session.execute(select(RagSource))).scalar_one()
    chunk = (await db_session.execute(select(RagChunk))).scalar_one()

    assert item["acquisition_type"] == "pdf_url"
    assert item["parser_type"] == "pdf_text"
    assert item["planned_action"] == "create_source"
    assert item["context"]["origin_type"] == "url_pdf"
    assert item["context"]["content_length"] == len(pdf_bytes)
    assert item["context"]["etag"] == '"pdf-v1"'
    assert item["context"]["last_modified"] == "Mon, 28 Oct 2024 22:44:41 GMT"
    assert apply_result["applied"] == 1
    assert source.origin_type == "url_pdf"
    assert source.origin_uri == "https://example.org/guide.pdf"
    assert source.parser_type == "pdf_text"
    assert source.metadata_["fetch_metadata"]["content_type"] == "application/pdf"
    assert source.metadata_["fetch_metadata"]["content_length"] == len(pdf_bytes)
    assert chunk.metadata_["parser_type"] == "pdf_text"
    assert chunk.metadata_["source_url"] == "https://example.org/guide.pdf"
    assert chunk.title == "Official PDF page 1 (1/1)"
    assert chunk.chunk_strategy == "page_paragraph"


@pytest.mark.asyncio
async def test_catalog_apply_requires_explicit_review_run(db_session, tmp_path):
    html = _html("Adults should move regularly for health.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html)
    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    source_count_before = await db_session.scalar(select(func.count()).select_from(RagSource))
    job_count_before = await db_session.scalar(select(func.count()).select_from(RagIngestJob))

    result = await service.apply_run(run_id=plan["run"]["id"])
    stored_run = await db_session.get(RagCatalogPlanItem, plan["items"][0]["id"])
    source_count_after = await db_session.scalar(select(func.count()).select_from(RagSource))
    job_count_after = await db_session.scalar(select(func.count()).select_from(RagIngestJob))

    assert result["status"] == "approval_blocked"
    assert result["approval_error_code"] == "REVIEW_RUN_REQUIRED"
    assert stored_run is not None
    assert stored_run.apply_status == "pending"
    assert source_count_after == source_count_before
    assert job_count_after == job_count_before


@pytest.mark.asyncio
async def test_catalog_apply_blocks_unknown_review_run(db_session, tmp_path):
    html = _html("Adults should move regularly for health.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html)
    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))

    result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=99999)

    assert result["status"] == "approval_blocked"
    assert result["approval_error_code"] == "REVIEW_NOT_FOUND"


@pytest.mark.asyncio
async def test_catalog_apply_rejects_scheduler_review_scope(db_session, tmp_path):
    html = _html("Adults should move regularly for health.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html)
    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    review = RagReviewRun(
        review_type="scheduler_run",
        target_run_id=1,
        status="completed",
        requires_approval=False,
        recommended_action="no_action",
        risk_level="low",
    )
    db_session.add(review)
    await db_session.commit()

    result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review.id)

    assert result["status"] == "approval_blocked"
    assert result["approval_error_code"] == "REVIEW_SCOPE_MISMATCH"


@pytest.mark.asyncio
async def test_catalog_apply_rejects_review_for_different_plan(db_session, tmp_path):
    html = _html("Adults should move regularly for health.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html)
    first_plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    review_id = await _review_plan(db_session, first_plan["run"]["id"])
    second_plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))

    result = await service.apply_run(run_id=second_plan["run"]["id"], review_run_id=review_id)

    assert result["status"] == "approval_blocked"
    assert result["approval_error_code"] == "REVIEW_TARGET_MISMATCH"


@pytest.mark.asyncio
async def test_document_catalog_plan_persists_local_file_without_mutating_until_apply(db_session, tmp_path):
    source_file = tmp_path / "local-guide.md"
    source_file.write_text(
        _markdown_sections(
            "Protein guidance long enough to create a stable section chunk for local catalog testing.",
            "Meal timing guidance long enough to stay independent in the markdown chunker.",
        ),
        encoding="utf-8",
    )
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)

    plan = await service.create_plan(catalog_file=_document_catalog_file(tmp_path, file_name="local-guide.md"))
    item = plan["items"][0]
    source_count = await db_session.scalar(select(func.count()).select_from(RagSource))
    job_count = await db_session.scalar(select(func.count()).select_from(RagIngestJob))

    assert item["acquisition_type"] == "local_file"
    assert item["origin_uri"] == str(source_file.resolve())
    assert item["parser_type"] == "markdown"
    assert item["planned_action"] == "create_source"
    assert source_count == 0
    assert job_count == 0

    review_id = await _review_plan(db_session, plan["run"]["id"])
    apply_result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)
    source = (await db_session.execute(select(RagSource))).scalar_one()
    stored_item = (await db_session.execute(select(RagCatalogPlanItem))).scalar_one()

    assert apply_result["applied"] == 1
    assert source.origin_type == "file_markdown"
    assert source.parser_type == "markdown"
    assert source.source_url == "https://example.org/reference"
    assert source.metadata_["fetch_metadata"]["catalog_key"] == "local_document"
    assert source.metadata_["fetch_metadata"]["file_size"] == source_file.stat().st_size
    assert stored_item.applied_job_id is not None


@pytest.mark.asyncio
async def test_document_catalog_apply_blocks_stale_local_file(db_session, tmp_path):
    source_file = tmp_path / "local-guide.md"
    source_file.write_text(
        _markdown_sections("Original local content long enough for the catalog plan."),
        encoding="utf-8",
    )
    service = RAGCatalogControlService(db_session, get_settings())
    catalog_path = _document_catalog_file(tmp_path, file_name="local-guide.md")

    plan = await service.create_plan(catalog_file=catalog_path)
    source_file.write_text(
        _markdown_sections("Changed local content after the plan was saved."),
        encoding="utf-8",
    )
    review_id = await _review_plan(db_session, plan["run"]["id"])
    result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)
    item = (await db_session.execute(select(RagCatalogPlanItem))).scalar_one()
    source_count = await db_session.scalar(select(func.count()).select_from(RagSource))

    assert result["stale"] == 1
    assert item.apply_status == "stale"
    assert item.apply_error_code == "PLAN_STALE"
    assert source_count == 0


@pytest.mark.asyncio
async def test_catalog_apply_blocks_review_recommendation_without_mutating(db_session, tmp_path):
    service = RAGCatalogControlService(db_session, get_settings())
    plan = await service.create_plan(catalog_file=_document_catalog_file(tmp_path, file_name="missing.md"))
    review_id = await _review_plan(db_session, plan["run"]["id"])
    source_count_before = await db_session.scalar(select(func.count()).select_from(RagSource))
    job_count_before = await db_session.scalar(select(func.count()).select_from(RagIngestJob))

    result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)
    item = (await db_session.execute(select(RagCatalogPlanItem))).scalar_one()
    source_count_after = await db_session.scalar(select(func.count()).select_from(RagSource))
    job_count_after = await db_session.scalar(select(func.count()).select_from(RagIngestJob))

    assert result["status"] == "approval_blocked"
    assert result["approval_error_code"] == "REVIEW_BLOCKED"
    assert item.apply_status == "pending"
    assert source_count_after == source_count_before
    assert job_count_after == job_count_before


@pytest.mark.asyncio
async def test_catalog_apply_approved_only_applies_safe_pdf_and_skips_blocked_item(db_session, tmp_path):
    pdf_bytes = _synthetic_text_pdf("Official PDF approved-only fixture.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(pdf_values=[pdf_bytes, pdf_bytes])
    service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    plan = await service.create_plan(catalog_file=_mixed_pdf_and_missing_file_catalog(tmp_path))
    review_id = await _review_plan(db_session, plan["run"]["id"])

    result = await service.apply_run(
        run_id=plan["run"]["id"],
        review_run_id=review_id,
        apply_approved_only=True,
    )
    items = (
        await db_session.execute(select(RagCatalogPlanItem).order_by(RagCatalogPlanItem.catalog_key.asc()))
    ).scalars().all()
    source = (await db_session.execute(select(RagSource))).scalar_one()
    job_count = await db_session.scalar(select(func.count()).select_from(RagIngestJob))

    assert result["status"] == "partially_applied"
    assert result["approval_status"] == "partially_applied"
    assert result["applied"] == 1
    assert result["skipped_blocked"] == 1
    assert source.origin_type == "url_pdf"
    assert job_count == 1
    assert {item.catalog_key: item.apply_status for item in items} == {
        "missing_local_document": "skipped_blocked",
        "official_pdf": "applied",
    }
    assert items[0].apply_error_code == "REVIEW_BLOCKED_ITEM"

    second_result = await service.apply_run(
        run_id=plan["run"]["id"],
        review_run_id=review_id,
        apply_approved_only=True,
    )

    assert second_result["status"] == "already_applied"


@pytest.mark.asyncio
async def test_catalog_apply_approved_only_blocks_when_no_items_are_eligible(db_session, tmp_path):
    service = RAGCatalogControlService(db_session, get_settings())
    plan = await service.create_plan(catalog_file=_document_catalog_file(tmp_path, file_name="missing.md"))
    review_id = await _review_plan(db_session, plan["run"]["id"])

    result = await service.apply_run(
        run_id=plan["run"]["id"],
        review_run_id=review_id,
        apply_approved_only=True,
    )
    item = (await db_session.execute(select(RagCatalogPlanItem))).scalar_one()
    source_count = await db_session.scalar(select(func.count()).select_from(RagSource))

    assert result["status"] == "approval_blocked"
    assert result["approval_error_code"] == "NO_APPROVED_ITEMS_TO_APPLY"
    assert result["skipped_blocked"] == 1
    assert item.apply_status == "skipped_blocked"
    assert source_count == 0


@pytest.mark.asyncio
async def test_document_catalog_detects_partial_local_file_change(db_session, tmp_path):
    original = _markdown_sections(
        "Stable section one content with enough text to remain as its own chunk for diffing.",
        "Stable section two content with enough text to remain as its own chunk for diffing.",
        "Stable section three content with enough text to remain as its own chunk for diffing.",
        "Stable section four content with enough text to remain as its own chunk for diffing.",
    )
    changed = _markdown_sections(
        "Changed section one content with updated guidance and enough text to remain its own chunk.",
        "Stable section two content with enough text to remain as its own chunk for diffing.",
        "Stable section three content with enough text to remain as its own chunk for diffing.",
        "Stable section four content with enough text to remain as its own chunk for diffing.",
    )
    source_file = tmp_path / "local-guide.md"
    source_file.write_text(original, encoding="utf-8")
    catalog_path = _document_catalog_file(tmp_path, file_name="local-guide.md")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    initial_plan_id = (await service.create_plan(catalog_file=catalog_path))["run"]["id"]
    initial_review_id = await _review_plan(db_session, initial_plan_id)
    await service.apply_run(run_id=initial_plan_id, review_run_id=initial_review_id)

    source_file.write_text(changed, encoding="utf-8")
    plan = await service.create_plan(catalog_file=catalog_path)
    item = plan["items"][0]

    assert item["catalog_status"] == "matched"
    assert item["planned_action"] == "partial_refresh"
    assert item["sections"]["changed"] == 1
    assert item["sections"]["change_ratio"] == 0.25


@pytest.mark.asyncio
async def test_catalog_apply_does_not_apply_same_run_twice(db_session, tmp_path):
    html = _html("Adults should move regularly for health.", "Strength training supports muscles.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html, html)
    service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    review_id = await _review_plan(db_session, plan["run"]["id"])
    first_result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)
    job_count_after_first = await db_session.scalar(select(func.count()).select_from(RagIngestJob))

    second_result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)
    job_count_after_second = await db_session.scalar(select(func.count()).select_from(RagIngestJob))

    assert first_result["applied"] == 1
    assert second_result["status"] == "already_applied"
    assert job_count_after_second == job_count_after_first


@pytest.mark.asyncio
async def test_document_catalog_marks_missing_local_file_for_manual_review(db_session, tmp_path):
    service = RAGCatalogControlService(db_session, get_settings())

    plan = await service.create_plan(catalog_file=_document_catalog_file(tmp_path, file_name="missing.md"))
    item = plan["items"][0]

    assert item["fetch_status"] == "failed"
    assert item["planned_action"] == "manual_review_required"
    assert item["reason_code"] == "FETCH_OR_PARSE_FAILED"


@pytest.mark.asyncio
async def test_catalog_plan_detects_partial_chunk_change(db_session, tmp_path):
    original = _html(
        "Stable section one content.",
        "Stable section two content.",
        "Stable section three content.",
        "Stable section four content.",
    )
    changed = _html(
        "Changed section one content with updated guidance.",
        "Stable section two content.",
        "Stable section three content.",
        "Stable section four content.",
    )
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(original, changed)
    service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    await service.rag_service.register_url(
        url="https://example.org/guide",
        title="Official Guide",
        category="exercise",
        tags=["guideline"],
        license_value="official-webpage",
        author_or_org="Example Org",
        catalog_key="official_guide",
    )

    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    item = plan["items"][0]

    assert item["catalog_status"] == "matched"
    assert item["planned_action"] == "partial_refresh"
    assert item["sections"]["changed"] == 1
    assert item["sections"]["change_ratio"] == 0.25


@pytest.mark.asyncio
async def test_catalog_plan_marks_metadata_changed_separately(db_session, tmp_path):
    html = _html("Stable section one content.", "Stable section two content.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html, html)
    service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    await service.rag_service.register_url(
        url="https://example.org/guide",
        title="Official Guide",
        category="exercise",
        tags=["guideline"],
        license_value="official-webpage",
        author_or_org="Example Org",
        catalog_key="official_guide",
    )

    plan = await service.create_plan(
        catalog_file=_catalog_file(tmp_path, title="Official Guide Revised")
    )
    item = plan["items"][0]

    assert plan["run"]["matched_count"] == 1
    assert plan["run"]["metadata_changed_count"] == 1
    assert item["catalog_status"] == "metadata_changed"
    assert item["metadata_changed_fields"] == ["title"]
    assert item["planned_action"] == "partial_refresh"
    assert item["reason_code"] == "METADATA_CHANGED"


@pytest.mark.asyncio
async def test_catalog_plan_marks_orphaned_db_source_for_manual_review(db_session, tmp_path):
    db_session.add(
        RagSource(
            title="Removed Catalog Source",
            source_type="official_guideline",
            source_url="https://example.org/orphaned",
            origin_type="url_html",
            origin_uri="https://example.org/orphaned",
            ingest_method="cli",
            parser_type="html",
            parser_version="html-parser-v1",
            chunk_strategy="hybrid_evidence",
            chunker_version=CHUNKER_VERSION,
            normalization_version=NORMALIZATION_VERSION,
            refresh_policy="scheduled",
            refresh_interval_hours=720,
            source_grade="A",
            license="official-webpage",
            category="exercise",
            tags=["guideline"],
            language="en",
            author_or_org="Example Org",
            status="active",
            version=1,
            content_hash="orphaned-hash",
            metadata_={"fetch_metadata": {"catalog_key": "orphaned_source"}},
        )
    )
    await db_session.commit()
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(_html("Catalog source content."))

    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    orphan = next(item for item in plan["items"] if item["catalog_status"] == "orphaned")

    assert plan["run"]["orphaned_count"] == 1
    assert orphan["planned_action"] == "manual_review_required"
    assert orphan["reason_code"] == "ORPHANED_SOURCE"
    assert "orphaned_source" in orphan["quality_warnings"]


@pytest.mark.asyncio
async def test_catalog_plan_defers_when_embedding_budget_is_exceeded(db_session, tmp_path):
    original = _html("Stable section one content.", "Stable section two content.")
    changed = _html("Changed section one content.", "Stable section two content.")
    bootstrap_service = RAGCatalogControlService(db_session, get_settings())
    bootstrap_service.rag_service.url_fetcher = FakeUrlFetcher(original)
    bootstrap_service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    bootstrap_service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    await bootstrap_service.rag_service.register_url(
        url="https://example.org/guide",
        title="Official Guide",
        category="exercise",
        tags=["guideline"],
        license_value="official-webpage",
        author_or_org="Example Org",
        catalog_key="official_guide",
    )

    settings = get_settings().model_copy(update={"RAG_ALLOWED_REEMBEDDING_SECONDS": 0.0})
    service = RAGCatalogControlService(db_session, settings)
    service.rag_service.url_fetcher = FakeUrlFetcher(changed)
    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    item = plan["items"][0]

    assert item["planned_action"] == "defer_reembedding"
    assert item["reason_code"] == "EMBEDDING_BUDGET_EXCEEDED"


@pytest.mark.asyncio
async def test_catalog_plan_blocks_low_confidence_missing_source(db_session, tmp_path):
    low_confidence_html = "<html><body><main><p>Short unstructured text.</p></main></body></html>"
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(low_confidence_html)

    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    item = plan["items"][0]

    assert item["catalog_status"] == "missing"
    assert item["planned_action"] == "manual_review_required"
    assert item["reason_code"] == "QUALITY_GATE_FAILED"
    assert "low_parser_confidence" in item["quality_warnings"]


@pytest.mark.asyncio
async def test_catalog_plan_requires_full_reindex_when_anchor_lineage_is_missing(db_session, tmp_path):
    html = _html("Stable official content.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html)
    fetched = await service.rag_service.url_fetcher.fetch("https://example.org/guide")
    parsed = service.rag_service._parse_fetched_url(
        fetched,
        title="Official Guide",
        extra_metadata={"catalog_key": "official_guide"},
    )

    source = RagSource(
        title="Official Guide",
        source_type="official_guideline",
        source_url="https://example.org/guide",
        origin_type="url_html",
        origin_uri="https://example.org/guide",
        ingest_method="cli",
        parser_type="html",
        parser_version="html-parser-v1",
        chunk_strategy="hybrid_evidence",
        chunker_version=CHUNKER_VERSION,
        normalization_version=NORMALIZATION_VERSION,
        refresh_policy="scheduled",
        refresh_interval_hours=720,
        source_grade="A",
        license="official-webpage",
        category="exercise",
        tags=["guideline"],
        language="en",
        author_or_org="Example Org",
        status="active",
        version=1,
        content_hash=parsed.content_hash,
        metadata_={"fetch_metadata": {"catalog_key": "official_guide"}},
    )
    db_session.add(source)
    await db_session.flush()
    db_session.add(
        RagChunk(
            source_id=source.id,
            chunk_index=0,
            title="Official Guide",
            content=parsed.sections[0].text,
            content_hash=parsed.sections[0].chunk_content_hash or parsed.content_hash,
            anchor_hash="legacy-anchor",
            embedding_input_hash="legacy-embedding-input",
            index_payload_hash="legacy-index-payload",
            category="exercise",
            tags=["guideline"],
            embedding=_embedding(),
            embedding_model="gemini-embedding-001",
            embedding_dim=3072,
            index_status="indexed",
            source_version=1,
            chunk_strategy="hybrid_evidence",
            chunk_anchor="legacy",
            metadata_={},
            status="active",
        )
    )
    await db_session.commit()

    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    item = plan["items"][0]

    assert item["planned_action"] == "full_reindex"
    assert item["reason_code"] == "ANCHOR_LINEAGE_MISSING"
    assert "anchor_lineage_missing" in item["quality_warnings"]


@pytest.mark.asyncio
async def test_catalog_apply_requires_confirmation_for_full_reindex(db_session, tmp_path):
    source_file = tmp_path / "local-guide.md"
    source_file.write_text(
        _markdown_sections("Original local content long enough for the catalog plan."),
        encoding="utf-8",
    )
    catalog_path = _document_catalog_file(tmp_path, file_name="local-guide.md")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    initial_plan = await service.create_plan(catalog_file=catalog_path)
    initial_review_id = await _review_plan(db_session, initial_plan["run"]["id"])
    await service.apply_run(run_id=initial_plan["run"]["id"], review_run_id=initial_review_id)
    source = (await db_session.execute(select(RagSource))).scalar_one()
    source.parser_version = "legacy-parser-v0"
    await db_session.commit()

    full_plan = await service.create_plan(catalog_file=catalog_path)
    item = full_plan["items"][0]
    review_id = await _review_plan(db_session, full_plan["run"]["id"])
    blocked = await service.apply_run(run_id=full_plan["run"]["id"], review_run_id=review_id)
    unconfirmed = await service.apply_run(
        run_id=full_plan["run"]["id"],
        review_run_id=review_id,
        apply_approved_only=True,
    )
    applied = await service.apply_run(
        run_id=full_plan["run"]["id"],
        review_run_id=review_id,
        confirm_full_reindex=True,
        apply_approved_only=True,
    )

    assert item["planned_action"] == "full_reindex"
    assert blocked["status"] == "approval_blocked"
    assert blocked["approval_error_code"] == "FULL_REINDEX_CONFIRMATION_REQUIRED"
    assert unconfirmed["status"] == "approval_blocked"
    assert unconfirmed["approval_error_code"] == "NO_APPROVED_ITEMS_TO_APPLY"
    assert unconfirmed["skipped_unconfirmed"] == 1
    assert applied["applied"] == 1
    assert applied["approval_status"] == "approved"


@pytest.mark.asyncio
async def test_catalog_apply_blocks_stale_review_item_snapshot(db_session, tmp_path):
    html = _html("Adults should move regularly for health.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html)
    plan = await service.create_plan(catalog_file=_catalog_file(tmp_path))
    review_id = await _review_plan(db_session, plan["run"]["id"])
    item = (await db_session.execute(select(RagCatalogPlanItem))).scalar_one()
    item.reason_code = "CHANGED_AFTER_REVIEW"
    await db_session.commit()

    result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)

    assert result["status"] == "approval_blocked"
    assert result["approval_error_code"] == "REVIEW_STALE"


@pytest.mark.asyncio
async def test_catalog_apply_blocks_stale_plan(db_session, tmp_path):
    planned = _html("Planned content for the official source.")
    stale = _html("Remote content changed after the plan was saved.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(planned, stale)
    catalog_path = _catalog_file(tmp_path)

    plan = await service.create_plan(catalog_file=catalog_path)
    review_id = await _review_plan(db_session, plan["run"]["id"])
    result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)
    item = (await db_session.execute(select(RagCatalogPlanItem))).scalar_one()

    assert result["stale"] == 1
    assert item.apply_status == "stale"
    assert item.apply_error_code == "PLAN_STALE"


@pytest.mark.asyncio
async def test_pdf_url_catalog_apply_blocks_stale_plan(db_session, tmp_path):
    planned_pdf = _synthetic_text_pdf("Planned official PDF content.")
    changed_pdf = _synthetic_text_pdf("Changed official PDF content.")
    service = RAGCatalogControlService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(pdf_values=[planned_pdf, changed_pdf])
    catalog_path = _pdf_catalog_file(tmp_path)

    plan = await service.create_plan(catalog_file=catalog_path)
    review_id = await _review_plan(db_session, plan["run"]["id"])
    result = await service.apply_run(run_id=plan["run"]["id"], review_run_id=review_id)
    item = (await db_session.execute(select(RagCatalogPlanItem))).scalar_one()
    source_count = await db_session.scalar(select(func.count()).select_from(RagSource))

    assert result["stale"] == 1
    assert item.apply_status == "stale"
    assert item.apply_error_code == "PLAN_STALE"
    assert source_count == 0


def test_catalog_plan_report_writer_preserves_utf8_and_lf(tmp_path):
    report_path = tmp_path / "catalog-plan.md"
    plan = {
        "run": {
            "id": 1,
            "status": "succeeded",
            "mode": "live_fetch",
            "total_sources": 1,
            "planned_create_count": 0,
            "planned_skip_count": 1,
            "planned_partial_count": 0,
            "planned_full_count": 0,
            "planned_manual_count": 0,
            "planned_defer_count": 0,
        },
        "items": [
            {
                "title": "공식 영양 가이드",
                "catalog_status": "matched",
                "planned_action": "skip_refresh",
                "reason_code": "SOURCE_UNCHANGED",
                "sections": {"change_ratio": 0.0},
                "chunks": {"change_ratio": 0.0},
                "quality_warnings": [],
            }
        ],
    }

    RAGCatalogControlService.write_plan_report(plan, report_path)

    data = report_path.read_bytes()
    assert b"\r\n" not in data
    assert "공식 영양 가이드".encode("utf-8") in data
