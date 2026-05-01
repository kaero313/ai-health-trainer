from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.rag import RagChunk, RagIngestJob, RagSource
from app.services.rag_index_service import RAGIndexError
from app.services.rag_service import RAGService


def _embedding(value: float = 0.1) -> list[float]:
    return [value] * 3072


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
        content="Protein supports recovery and muscle growth.\n\nTargets should be adjusted by body weight.",
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


@pytest.mark.asyncio
async def test_hybrid_search_merges_keyword_and_vector_hits(db_session, monkeypatch):
    settings = get_settings()
    service = RAGService(db_session, settings)
    chunk_a = await _create_rag_chunk(db_session, title="protein guide", content="protein target")
    chunk_b = await _create_rag_chunk(db_session, title="diet guide", content="diet protein strategy")

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

    results = await service.search("diet protein", category="nutrition", top_k=2)

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
