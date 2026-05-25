import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.rag_pipeline import RAGDocumentParser, hash_text
from app.services.rag_source_acquisition import FetchedUrlContent
from app.services.rag_source_adapters import (
    ACQUISITION_LOCAL_FILE,
    ACQUISITION_PDF_URL,
    ACQUISITION_URL_HTML,
    CatalogSource,
    LocalFileSourceAdapter,
    PdfUrlSourceAdapter,
    load_catalog_sources,
)


def _catalog_source(*, path: str, parser_type: str) -> CatalogSource:
    return CatalogSource(
        key="local_fixture",
        acquisition_type=ACQUISITION_LOCAL_FILE,
        url=None,
        path=path,
        parser_type=parser_type,
        title="Local Fixture",
        category="nutrition",
        tags=["fixture"],
        source_type="curated_internal_summary",
        source_grade="B",
        license_value="internal-summary",
        language="en",
        author_or_org="AI Health Trainer",
        refresh_policy="manual",
        refresh_interval_hours=None,
        curation_method="internal fixture",
        reference_urls=["https://example.org/reference"],
    )


def _pdf_url_catalog_source() -> CatalogSource:
    return CatalogSource(
        key="official_pdf",
        acquisition_type=ACQUISITION_PDF_URL,
        url="https://example.org/guide.pdf",
        path=None,
        parser_type="pdf_text",
        title="Official PDF",
        category="exercise",
        tags=["pdf", "official"],
        source_type="official_guideline",
        source_grade="A",
        license_value="public-sector-official-pdf",
        language="en",
        author_or_org="Example Agency",
        refresh_policy="scheduled",
        refresh_interval_hours=720,
        curation_method=None,
        reference_urls=["https://example.org/guide.pdf"],
    )


class FakePdfUrlFetcher:
    def __init__(self, content: bytes):
        self.content = content

    async def fetch_pdf(self, url: str) -> FetchedUrlContent:
        return FetchedUrlContent(
            requested_url=url,
            final_url=url,
            content_type="application/pdf",
            etag='"pdf-etag"',
            last_modified="Mon, 28 Oct 2024 22:44:41 GMT",
            fetched_at=datetime.now(timezone.utc),
            raw_content=self.content,
            text="",
        )


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


def test_load_catalog_sources_keeps_url_backward_compatibility():
    payload = {
        "sources": [
            {
                "key": "official_url",
                "url": "https://example.org/guide",
                "title": "Official URL",
                "category": "exercise",
                "tags": ["official"],
            }
        ]
    }

    source = load_catalog_sources(payload)[0]

    assert source.acquisition_type == ACQUISITION_URL_HTML
    assert source.parser_type == "html"
    assert source.reference_urls == ["https://example.org/guide"]


def test_load_catalog_sources_supports_pdf_url_defaults():
    payload = {
        "sources": [
            {
                "key": "official_pdf",
                "acquisition_type": "pdf_url",
                "url": "https://example.org/guide.pdf",
                "title": "Official PDF",
                "category": "exercise",
                "tags": ["pdf"],
            }
        ]
    }

    source = load_catalog_sources(payload)[0]

    assert source.acquisition_type == ACQUISITION_PDF_URL
    assert source.parser_type == "pdf_text"
    assert source.source_grade == "A"
    assert source.refresh_policy == "scheduled"
    assert source.reference_urls == ["https://example.org/guide.pdf"]


def test_load_catalog_sources_supports_failure_lifecycle_metadata():
    payload = {
        "sources": [
            {
                "key": "blocked_official_source",
                "url": "https://example.org/blocked",
                "title": "Blocked Official Source",
                "category": "supplement",
                "enabled": False,
                "failure_policy": "replacement_required",
                "replacement_url": "https://example.org/replacement",
                "manual_curation_fallback": "Use reviewed internal summary until replacement is active.",
                "max_consecutive_failures": 2,
                "disabled_reason": "HTTP 403 in backend runtime",
            }
        ]
    }

    source = load_catalog_sources(payload)[0]

    assert source.enabled is False
    assert source.failure_policy == "replacement_required"
    assert source.replacement_url == "https://example.org/replacement"
    assert source.manual_curation_fallback == "Use reviewed internal summary until replacement is active."
    assert source.max_consecutive_failures == 2
    assert source.disabled_reason == "HTTP 403 in backend runtime"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "parser_type", "content"),
    [
        ("fixture.md", "markdown", "# Protein\n\nProtein supports recovery."),
        ("fixture.txt", "text", "First paragraph.\n\nSecond paragraph."),
    ],
)
async def test_local_file_adapter_records_text_file_fingerprint(tmp_path, filename, parser_type, content):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(json.dumps({"sources": []}), encoding="utf-8")
    source_file = tmp_path / filename
    source_file.write_text(content, encoding="utf-8")
    adapter = LocalFileSourceAdapter(RAGDocumentParser())

    acquired = await adapter.acquire(
        _catalog_source(path=filename, parser_type=parser_type),
        catalog_file=catalog_file,
    )

    assert acquired.origin_type in {"file_markdown", "file_text"}
    assert acquired.origin_uri == str(source_file.resolve())
    assert acquired.parsed.parser_type == parser_type
    assert acquired.acquisition_metadata["file_size"] == source_file.stat().st_size
    assert acquired.acquisition_metadata["mtime"]
    assert acquired.acquisition_metadata["reference_urls"] == ["https://example.org/reference"]


@pytest.mark.asyncio
async def test_local_file_adapter_records_pdf_fingerprint(tmp_path):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(json.dumps({"sources": []}), encoding="utf-8")
    source_file = tmp_path / "fixture.pdf"
    source_file.write_bytes(_synthetic_text_pdf("Protein PDF adapter fixture."))
    adapter = LocalFileSourceAdapter(RAGDocumentParser())

    acquired = await adapter.acquire(
        _catalog_source(path="fixture.pdf", parser_type="pdf_text"),
        catalog_file=catalog_file,
    )

    assert acquired.origin_type == "file_pdf"
    assert acquired.parsed.parser_type == "pdf_text"
    assert acquired.acquisition_metadata["file_extension"] == ".pdf"
    assert acquired.acquisition_metadata["raw_content_hash"] == acquired.parsed.raw_content_hash


@pytest.mark.asyncio
async def test_pdf_url_adapter_records_binary_fetch_metadata(tmp_path):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(json.dumps({"sources": []}), encoding="utf-8")
    pdf_bytes = _synthetic_text_pdf("Official PDF URL adapter fixture.")
    rag_service = SimpleNamespace(
        url_fetcher=FakePdfUrlFetcher(pdf_bytes),
        parser=RAGDocumentParser(),
    )
    adapter = PdfUrlSourceAdapter(rag_service)

    acquired = await adapter.acquire(_pdf_url_catalog_source(), catalog_file=catalog_file)

    assert acquired.origin_type == "url_pdf"
    assert acquired.origin_uri == "https://example.org/guide.pdf"
    assert acquired.source_url == "https://example.org/guide.pdf"
    assert acquired.parsed.parser_type == "pdf_text"
    assert acquired.parsed.source_uri == "https://example.org/guide.pdf"
    assert acquired.parsed.sections[0].title == "Official PDF page 1"
    assert acquired.parsed.sections[0].source_url == "https://example.org/guide.pdf"
    assert acquired.acquisition_metadata["content_type"] == "application/pdf"
    assert acquired.acquisition_metadata["content_length"] == len(pdf_bytes)
    assert acquired.acquisition_metadata["raw_content_hash"] == hash_text(pdf_bytes)
    assert acquired.acquisition_metadata["parser_type"] == "pdf_text"
    assert acquired.acquisition_metadata["origin_type"] == "url_pdf"
