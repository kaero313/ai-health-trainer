from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.rag import RagChunk, RagIngestJob, RagRetrievalTrace, RagSource
from app.models.user import User
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
