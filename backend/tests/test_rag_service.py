from unittest.mock import AsyncMock
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.rag import RagChunk, RagEmbeddingCache, RagIngestJob, RagPipelineDecision, RagRetrievalTrace, RagSource
from app.models.user import User
from app.services.rag_index_service import RAGIndexError
from app.services.rag_service import RAGService
from app.services.rag_source_acquisition import FetchedUrlContent


def _embedding(value: float = 0.1) -> list[float]:
    return [value] * 3072


class FakeUrlFetcher:
    def __init__(self, *html_values: str, etag: str | None = '"v1"', last_modified: str | None = "Mon, 01 Jan 2024 00:00:00 GMT"):
        self.html_values = list(html_values)
        self.etag = etag
        self.last_modified = last_modified
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchedUrlContent:
        self.calls.append(url)
        if len(self.html_values) > 1:
            html = self.html_values.pop(0)
        else:
            html = self.html_values[0]
        return FetchedUrlContent(
            requested_url=url,
            final_url=url,
            content_type="text/html; charset=utf-8",
            etag=self.etag,
            last_modified=self.last_modified,
            fetched_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            raw_content=html.encode("utf-8"),
            text=html,
        )


def _html_source(*section_bodies: str) -> str:
    sections = []
    for index, body in enumerate(section_bodies, start=1):
        sections.append(f"<h2>Section {index}</h2><p>{body}</p>")
    return "<html><head><title>Official Source</title></head><body><main><h1>Guide</h1>" + "".join(sections) + "</main></body></html>"


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


async def _create_rag_chunk(db_session, *, title: str, content: str, category: str = "nutrition") -> RagChunk:
    source = RagSource(
        title=f"{title} source",
        source_type="internal_policy",
        source_grade="B",
        category=category,
        tags=["test"],
        language="ko",
        status="active",
        version=1,
        content_hash=f"{title}-source-hash",
    )
    db_session.add(source)
    await db_session.flush()

    chunk = RagChunk(
        source_id=source.id,
        chunk_index=1,
        title=title,
        content=content,
        content_hash=f"{title}-chunk-hash",
        category=category,
        tags=["test"],
        embedding=_embedding(),
        embedding_model="gemini-embedding-001",
        embedding_dim=3072,
        opensearch_index="rag_chunks_v1",
        opensearch_document_id=None,
        index_status="indexed",
        status="active",
        version=1,
    )
    db_session.add(chunk)
    await db_session.commit()
    return chunk


@pytest.mark.asyncio
async def test_ingest_document_creates_source_chunks_and_job(db_session):
    service = RAGService(db_session, get_settings())
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.index_chunk = AsyncMock(return_value=None)

    chunk_count = await service.ingest_document(
        title="Protein Basics",
        content="단백질은 근육 회복과 성장에 중요합니다.\n\n목표와 체중에 맞춰 섭취량을 조정합니다.",
        category="nutrition",
        source="internal://protein-basics",
        tags=["protein", "nutrition"],
    )

    assert chunk_count == 1
    source = (await db_session.execute(select(RagSource))).scalar_one()
    chunk = (await db_session.execute(select(RagChunk))).scalar_one()
    job = (await db_session.execute(select(RagIngestJob))).scalar_one()

    assert source.title == "Protein Basics"
    assert source.category == "nutrition"
    assert chunk.source_id == source.id
    assert chunk.index_status == "indexed"
    assert chunk.opensearch_document_id == str(chunk.id)
    assert job.status == "succeeded"
    assert job.chunks_succeeded == 1
    assert job.indexed_succeeded == 1
    assert job.pipeline_stage == "finished"
    assert job.reembedding_count == 1
    decision = (await db_session.execute(select(RagPipelineDecision))).scalar_one()
    assert decision.selected_action == "create_source"
    assert decision.source_id == source.id
    assert chunk.anchor_hash
    assert chunk.embedding_input_hash
    assert chunk.index_payload_hash
    assert chunk.metadata_["metadata_schema_version"] == 1


@pytest.mark.asyncio
async def test_ingest_document_reuses_embedding_cache(db_session):
    service = RAGService(db_session, get_settings())
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.index_chunk = AsyncMock(return_value=None)

    await service.ingest_document(
        title="Cache Guide A",
        content="repeatable content for embedding cache",
        category="nutrition",
        tags=["cache"],
    )
    await service.ingest_document(
        title="Cache Guide B",
        content="repeatable content for embedding cache",
        category="nutrition",
        tags=["cache"],
    )

    cache = (await db_session.execute(select(RagEmbeddingCache))).scalar_one()
    jobs = (await db_session.execute(select(RagIngestJob).order_by(RagIngestJob.id))).scalars().all()

    assert service.get_embedding.await_count == 1
    assert cache.usage_count == 2
    assert jobs[0].reembedding_count == 1
    assert jobs[1].embedding_reuse_count == 1


@pytest.mark.asyncio
async def test_hybrid_search_merges_keyword_and_vector_hits(db_session, monkeypatch):
    settings = get_settings()
    service = RAGService(db_session, settings)
    chunk_a = await _create_rag_chunk(db_session, title="protein guide", content="단백질 섭취 기준")
    chunk_b = await _create_rag_chunk(db_session, title="diet guide", content="다이어트 단백질 전략")

    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.keyword_search = AsyncMock(
        return_value=[
            {"_id": str(chunk_a.id), "_score": 8.0, "_source": {"chunk_id": str(chunk_a.id)}},
            {"_id": str(chunk_b.id), "_score": 3.0, "_source": {"chunk_id": str(chunk_b.id)}},
        ]
    )
    service.index_service.vector_search = AsyncMock(
        return_value=[
            {"_id": str(chunk_b.id), "_score": 9.0, "_source": {"chunk_id": str(chunk_b.id)}},
        ]
    )

    results = await service.search("다이어트 단백질", category="nutrition", top_k=2)

    assert [item["chunk_id"] for item in results] == [chunk_b.id, chunk_a.id]
    assert results[0]["search_backend"] == "opensearch"
    assert results[0]["search_mode"] == "hybrid"


@pytest.mark.asyncio
async def test_search_falls_back_to_pgvector_when_opensearch_fails(db_session):
    settings = get_settings()
    service = RAGService(db_session, settings)
    chunk = await _create_rag_chunk(db_session, title="fallback guide", content="fallback content")

    service.get_embedding = AsyncMock(return_value=_embedding())

    async def _raise(*args, **kwargs):
        raise RAGIndexError("OpenSearch unavailable")

    service._search_opensearch = _raise

    results = await service.search("fallback", category="nutrition", top_k=1)

    assert len(results) == 1
    assert results[0]["chunk_id"] == chunk.id
    assert results[0]["tags"] == ["test"]
    assert results[0]["source_grade"] == "B"
    assert results[0]["search_backend"] == "pgvector_fallback"
    assert results[0]["search_mode"] == "vector"
    decision = (await db_session.execute(select(RagPipelineDecision))).scalar_one()
    assert decision.selected_action == "pgvector_fallback"
    assert decision.reason_code == "OPENSEARCH_UNAVAILABLE"


@pytest.mark.asyncio
async def test_search_writes_retrieval_trace(db_session):
    user = User(email="rag-trace@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    chunk = await _create_rag_chunk(db_session, title="trace guide", content="trace content")

    service = RAGService(db_session, get_settings())
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.keyword_search = AsyncMock(
        return_value=[{"_id": str(chunk.id), "_score": 4.0, "_source": {"chunk_id": str(chunk.id)}}]
    )
    service.index_service.vector_search = AsyncMock(return_value=[])

    results = await service.search(
        "trace",
        category="nutrition",
        top_k=1,
        user_id=user.id,
        request_type="diet",
        trace_group_id="trace-group-id",
    )

    assert results[0]["rag_trace_group_id"] == "trace-group-id"
    traces = (await db_session.execute(select(RagRetrievalTrace))).scalars().all()
    assert len(traces) == 1
    assert traces[0].chunk_id == chunk.id
    assert traces[0].search_backend == "opensearch"
    assert traces[0].search_mode == "hybrid"


@pytest.mark.asyncio
async def test_refresh_source_skips_when_source_hash_is_unchanged(db_session, tmp_path):
    source_file = tmp_path / "guide.txt"
    source_file.write_text("stable paragraph for refresh policy", encoding="utf-8")

    service = RAGService(db_session, get_settings())
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.index_chunk = AsyncMock(return_value=None)
    service.index_service.delete_chunk = AsyncMock(return_value=None)

    created = await service.register_source(
        file_path=source_file,
        title="Stable Guide",
        category="nutrition",
        tags=["stable"],
    )
    refreshed = await service.refresh_source(int(created["source_id"]))

    jobs = (await db_session.execute(select(RagIngestJob).order_by(RagIngestJob.id))).scalars().all()
    decisions = (await db_session.execute(select(RagPipelineDecision).order_by(RagPipelineDecision.id))).scalars().all()

    assert refreshed["decision"] == "skip_refresh"
    assert jobs[-1].status == "skipped"
    assert jobs[-1].skipped_reason == "SOURCE_HASH_UNCHANGED"
    assert decisions[-1].selected_action == "skip_refresh"


@pytest.mark.asyncio
async def test_fetch_preview_url_returns_html_acquisition_and_hybrid_chunk_metadata(db_session):
    html = _html_source(
        "Adults should combine aerobic movement with muscle-strengthening activity for general health.",
        "Safety guidance should be reviewed when symptoms or medical concerns are present.",
    )
    service = RAGService(db_session, get_settings())
    service.url_fetcher = FakeUrlFetcher(html)

    result = await service.fetch_preview_url("https://example.org/official-guide")

    assert result["final_url"] == "https://example.org/official-guide"
    assert result["content_type"] == "text/html; charset=utf-8"
    assert result["parser_type"] == "html"
    assert result["child_chunks_total"] >= 2
    assert result["parent_sections_total"] >= 2
    first_chunk = result["child_chunks"][0]
    assert first_chunk["chunk_strategy"] == "hybrid_evidence"
    assert first_chunk["parent_section_hash"]


@pytest.mark.asyncio
async def test_register_url_persists_source_fetch_metadata_and_parent_lineage(db_session):
    html = _html_source(
        "A source grade A guideline paragraph long enough to create an evidence chunk for retrieval and tracing.",
        "A second guideline paragraph keeps parent section lineage visible in chunk metadata.",
    )
    service = RAGService(db_session, get_settings())
    service.url_fetcher = FakeUrlFetcher(html)
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.index_chunk = AsyncMock(return_value=None)

    result = await service.register_url(
        url="https://example.org/official-guide",
        title=None,
        category="exercise",
        tags=["guideline", "official"],
        license_value="official-webpage",
        author_or_org="Example Health Agency",
        catalog_key="example_official_guide",
    )

    source = await db_session.get(RagSource, int(result["source_id"]))
    chunks = (await db_session.execute(select(RagChunk).order_by(RagChunk.id))).scalars().all()
    decision = (await db_session.execute(select(RagPipelineDecision))).scalar_one()

    assert source is not None
    assert source.origin_type == "url_html"
    assert source.parser_type == "html"
    assert source.chunk_strategy == "hybrid_evidence"
    assert source.source_grade == "A"
    assert source.external_etag == '"v1"'
    assert source.external_last_modified is not None
    assert source.metadata_["fetch_metadata"]["catalog_key"] == "example_official_guide"
    assert source.metadata_["parent_section_count"] >= 2
    assert chunks[0].chunk_strategy == "hybrid_evidence"
    assert chunks[0].metadata_["chunk_role"] == "child_evidence"
    assert chunks[0].metadata_["parent_section_hash"]
    assert decision.context["total_section_count"] >= 2


@pytest.mark.asyncio
async def test_refresh_url_records_skip_and_partial_section_change_context(db_session):
    original = _html_source(
        "Stable section one content.",
        "Stable section two content.",
        "Stable section three content.",
        "Stable section four content.",
    )
    changed = _html_source(
        "Changed section one content with updated operational guidance.",
        "Stable section two content.",
        "Stable section three content.",
        "Stable section four content.",
    )
    service = RAGService(db_session, get_settings())
    service.url_fetcher = FakeUrlFetcher(original, original, changed)
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.index_chunk = AsyncMock(return_value=None)
    service.index_service.delete_chunk = AsyncMock(return_value=None)

    created = await service.register_url(
        url="https://example.org/refreshable-guide",
        title="Refreshable Guide",
        category="exercise",
        tags=["refresh"],
        license_value="official-webpage",
    )
    skipped = await service.refresh_source(int(created["source_id"]))
    partial = await service.refresh_source(int(created["source_id"]))

    decisions = (await db_session.execute(select(RagPipelineDecision).order_by(RagPipelineDecision.id))).scalars().all()
    assert skipped["decision"] == "skip_refresh"
    assert partial["decision"] == "partial_refresh"
    assert decisions[-1].context["changed_section_count"] == 1
    assert decisions[-1].context["total_section_count"] == 4
    assert decisions[-1].context["section_change_ratio"] == 0.25


@pytest.mark.asyncio
async def test_register_url_requires_manual_review_for_low_quality_html(db_session):
    service = RAGService(db_session, get_settings())
    service.url_fetcher = FakeUrlFetcher("<html><body><main><p>too short</p></main></body></html>")
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.index_chunk = AsyncMock(return_value=None)

    result = await service.register_url(
        url="https://example.org/low-quality",
        title="Low Quality",
        category="exercise",
        tags=["low-quality"],
    )
    decisions = (await db_session.execute(select(RagPipelineDecision))).scalars().all()

    assert result["decision"] == "manual_review_required"
    assert result["source_id"] is None
    assert decisions[0].reason_code == "LOW_PARSER_CONFIDENCE"


@pytest.mark.asyncio
async def test_register_text_source_records_file_parser_metadata(db_session, tmp_path):
    source_file = tmp_path / "text-guide.txt"
    source_file.write_text(
        "First paragraph about warmups and safe preparation before training. "
        "It is intentionally long enough to stay as its own chunk.\n\n"
        "Second paragraph about progressive overload and recovery planning. "
        "It is intentionally long enough to keep paragraph metadata.",
        encoding="utf-8",
    )

    service = RAGService(db_session, get_settings())
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.index_chunk = AsyncMock(return_value=None)

    result = await service.register_source(
        file_path=source_file,
        title="Text Fixture",
        category="exercise",
        tags=["text", "parser"],
        parser_type="text",
    )

    source = await db_session.get(RagSource, int(result["source_id"]))
    chunks = (await db_session.execute(select(RagChunk).order_by(RagChunk.id))).scalars().all()
    decision = (await db_session.execute(select(RagPipelineDecision))).scalar_one()

    assert source is not None
    assert source.origin_type == "file_text"
    assert source.parser_type == "text"
    assert source.chunk_strategy == "paragraph"
    assert chunks[0].chunk_strategy == "paragraph"
    assert chunks[0].metadata_["parser_type"] == "text"
    assert "paragraph_range" in chunks[0].metadata_
    assert decision.source_id == source.id


@pytest.mark.asyncio
async def test_register_pdf_source_records_page_anchor_metadata(db_session, tmp_path):
    source_file = tmp_path / "pdf-guide.pdf"
    source_file.write_bytes(_synthetic_text_pdf("Protein PDF parser fixture for RAG validation."))

    service = RAGService(db_session, get_settings())
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.index_chunk = AsyncMock(return_value=None)

    result = await service.register_source(
        file_path=source_file,
        title="PDF Fixture",
        category="nutrition",
        tags=["pdf", "parser"],
        parser_type="pdf_text",
    )

    source = await db_session.get(RagSource, int(result["source_id"]))
    chunk = (await db_session.execute(select(RagChunk))).scalar_one()

    assert source is not None
    assert source.origin_type == "file_pdf"
    assert source.parser_type == "pdf_text"
    assert source.metadata_["parser_confidence"] == 0.95
    assert chunk.chunk_strategy == "page_paragraph"
    assert chunk.page_number == 1
    assert chunk.metadata_["parser_type"] == "pdf_text"
    assert chunk.metadata_["page_number"] == 1
