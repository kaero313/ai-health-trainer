from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.rag import RagChunk, RagSource, RagSourceReplacementCandidate
from app.services.rag_replacement_candidate_service import RAGReplacementCandidateService
from app.services.rag_source_acquisition import FetchedUrlContent


class FakeUrlFetcher:
    def __init__(self, *, html: str | None = None, pdf: bytes | None = None, fail: bool = False):
        self.html = html
        self.pdf = pdf
        self.fail = fail

    async def fetch(self, url: str) -> FetchedUrlContent:
        if self.fail:
            raise RuntimeError("HTTP 403")
        content = self.html or _html("Candidate replacement content with enough detail for parser confidence.")
        return FetchedUrlContent(
            requested_url=url,
            final_url=url,
            content_type="text/html; charset=utf-8",
            etag='"candidate-etag"',
            last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
            fetched_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            raw_content=content.encode("utf-8"),
            text=content,
        )

    async def fetch_pdf(self, url: str) -> FetchedUrlContent:
        if self.fail:
            raise RuntimeError("HTTP 403")
        content = self.pdf or _synthetic_text_pdf("Official replacement PDF candidate.")
        return FetchedUrlContent(
            requested_url=url,
            final_url=url,
            content_type="application/pdf",
            etag='"candidate-pdf-etag"',
            last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
            fetched_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            raw_content=content,
            text="",
        )


def _html(body: str) -> str:
    return (
        "<html><body><main><h1>Replacement Guide</h1>"
        f"<h2>Evidence</h2><p>{body}</p>"
        "</main></body></html>"
    )


def _catalog_file(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "key": "blocked_source",
                        "url": "https://example.org/original",
                        "title": "Blocked Source",
                        "category": "supplement",
                        "tags": ["supplement", "safety"],
                        "source_type": "official_guideline",
                        "source_grade": "A",
                        "license": "official-webpage",
                        "language": "en",
                        "author_or_org": "Example Org",
                        "enabled": False,
                        "failure_policy": "replacement_required",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


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


async def _counts(db_session) -> tuple[int, int]:
    source_count = await db_session.scalar(select(func.count()).select_from(RagSource))
    chunk_count = await db_session.scalar(select(func.count()).select_from(RagChunk))
    return int(source_count), int(chunk_count)


@pytest.mark.asyncio
async def test_replacement_preview_persists_html_candidate_without_mutating_rag_data(db_session, tmp_path):
    service = RAGReplacementCandidateService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(
        html=_html("Candidate official source content. " * 20),
    )
    service.rag_service.index_service.index_chunk = AsyncMock()
    before_counts = await _counts(db_session)

    result = await service.preview(
        catalog_file=_catalog_file(tmp_path),
        key="blocked_source",
        candidate_url="https://example.org/replacement",
    )

    after_counts = await _counts(db_session)
    stored = (await db_session.execute(select(RagSourceReplacementCandidate))).scalar_one()
    assert result["status"] == "preview_succeeded"
    assert result["parser_type"] == "html"
    assert result["chunk_count"] > 0
    assert result["quality_warnings"] == []
    assert stored.candidate_url == "https://example.org/replacement"
    assert after_counts == before_counts
    service.rag_service.index_service.index_chunk.assert_not_called()


@pytest.mark.asyncio
async def test_replacement_preview_supports_pdf_candidate(db_session, tmp_path):
    service = RAGReplacementCandidateService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(pdf=_synthetic_text_pdf("PDF replacement candidate."))

    result = await service.preview(
        catalog_file=_catalog_file(tmp_path),
        key="blocked_source",
        candidate_url="https://example.org/replacement.pdf",
    )

    assert result["status"] == "preview_succeeded"
    assert result["acquisition_type"] == "pdf_url"
    assert result["parser_type"] == "pdf_text"
    assert result["chunk_count"] > 0


@pytest.mark.asyncio
async def test_replacement_preview_records_fetch_failure(db_session, tmp_path):
    service = RAGReplacementCandidateService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(fail=True)

    result = await service.preview(
        catalog_file=_catalog_file(tmp_path),
        key="blocked_source",
        candidate_url="https://example.org/blocked",
    )

    assert result["status"] == "fetch_failed"
    assert result["quality_warnings"] == ["candidate_fetch_failed"]
    assert result["context"]["error"] == "HTTP 403"


@pytest.mark.asyncio
async def test_replacement_preview_marks_low_confidence_candidate_for_manual_review(db_session, tmp_path):
    service = RAGReplacementCandidateService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html="<html><body><p>short</p></body></html>")

    result = await service.preview(
        catalog_file=_catalog_file(tmp_path),
        key="blocked_source",
        candidate_url="https://example.org/low-confidence",
    )

    assert result["status"] == "manual_review_required"
    assert "low_parser_confidence" in result["quality_warnings"]


@pytest.mark.asyncio
async def test_replacement_preview_report_preserves_utf8_and_lf(db_session, tmp_path):
    service = RAGReplacementCandidateService(db_session, get_settings())
    service.rag_service.url_fetcher = FakeUrlFetcher(html=_html("공식 후보 문서 내용입니다. " * 20))
    report_path = tmp_path / "replacement-report.md"

    await service.preview(
        catalog_file=_catalog_file(tmp_path),
        key="blocked_source",
        candidate_url="https://example.org/replacement",
        report_path=report_path,
    )

    data = report_path.read_bytes()
    assert b"\r\n" not in data
    assert b"No RAG source, chunk, embedding, OpenSearch index, or catalog JSON mutation" in data
    assert "공식 후보 문서 내용입니다".encode("utf-8") in data
