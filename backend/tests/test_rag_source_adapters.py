import json

import pytest

from app.services.rag_pipeline import RAGDocumentParser
from app.services.rag_source_adapters import (
    ACQUISITION_LOCAL_FILE,
    ACQUISITION_URL_HTML,
    CatalogSource,
    LocalFileSourceAdapter,
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
