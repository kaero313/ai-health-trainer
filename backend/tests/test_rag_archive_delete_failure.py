"""RAG chunk archive 시 OpenSearch 삭제 실패 처리 계약 테스트.

계약(C1~C5)은 구현이 아니라 작업 지시에서 가져왔다.
- C1 archive_source: 삭제 실패 chunk는 archived/failed, 성공 chunk는 archived/deleted, 예외 없이 commit,
  반환에 기존 키(sources, chunks)와 delete_failed를 둔다.
- C2 refresh 경로에서 archive되는 chunk에도 C1의 chunk 단위 규칙을 적용하고, 삭제 실패로 job이 실패하지 않는다.
- C3 reindex는 archived/failed chunk의 삭제를 다시 시도하고 deleted/delete_failed를 센다.
  source status와 무관하되 source_id를 주면 그 source로 제한한다. archived chunk에는 index_chunk를 부르지 않는다.
- C4 이미 archived/deleted인 chunk는 reindex에서 건드리지 않는다.
- C5 OpenSearch가 archived chunk id를 돌려줘도 search() 결과에 나오지 않는다(회귀 방지).

OpenSearch는 테스트에서 네트워크가 차단되므로 index_service 메서드는 모두 대역이다.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.rag import RagChunk, RagIngestJob, RagSource
from app.services.rag_index_service import RAGIndexError
from app.services.rag_service import RAGService
from app.services.rag_source_acquisition import FetchedUrlContent


# ── 대역·조회 도우미 ─────────────────────────────────────────────────────────
# _embedding·FakeUrlFetcher·_html_source는 test_rag_service.py와 같은 방식이다.
# tests가 패키지가 아니어서 import 대신 옮겨 둔다.


def _embedding(value: float = 0.1) -> list[float]:
    return [value] * 3072


class FakeUrlFetcher:
    def __init__(self, *html_values: str):
        self.html_values = list(html_values)
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchedUrlContent:
        self.calls.append(url)
        html = self.html_values.pop(0) if len(self.html_values) > 1 else self.html_values[0]
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


def _html_source(*section_bodies: str) -> str:
    sections = [f"<h2>Section {index}</h2><p>{body}</p>" for index, body in enumerate(section_bodies, start=1)]
    return (
        "<html><head><title>Official Source</title></head><body><main><h1>Guide</h1>"
        + "".join(sections)
        + "</main></body></html>"
    )


def _delete_mock(*failing_ids: int) -> AsyncMock:
    """failing_ids에 대해서만 RAGIndexError를 내는 delete_chunk 대역."""
    failing = set(failing_ids)

    async def _delete(chunk_id: int) -> None:
        if chunk_id in failing:
            raise RAGIndexError("OpenSearch delete failed")

    return AsyncMock(side_effect=_delete)


def _always_failing_delete_mock() -> AsyncMock:
    return AsyncMock(side_effect=RAGIndexError("OpenSearch delete failed"))


def _deleted_ids(mock: AsyncMock) -> list[int]:
    ids: list[int] = []
    for call in mock.await_args_list:
        ids.append(int(call.args[0]) if call.args else int(call.kwargs["chunk_id"]))
    return ids


def _indexed_chunk_ids(mock: AsyncMock) -> list[int]:
    ids: list[int] = []
    for call in mock.await_args_list:
        chunk = call.args[0] if call.args else call.kwargs["chunk"]
        ids.append(int(chunk.id))
    return ids


async def _committed_chunk_states(db_session: AsyncSession, chunk_ids: list[int]) -> dict[int, tuple[str, str]]:
    """서비스 세션과 분리된 새 세션으로 commit된 (status, index_status)를 읽는다."""
    async with AsyncSession(bind=db_session.bind) as fresh:
        rows = (
            await fresh.execute(
                select(RagChunk.id, RagChunk.status, RagChunk.index_status).where(RagChunk.id.in_(chunk_ids))
            )
        ).all()
    return {int(row.id): (row.status, row.index_status) for row in rows}


async def _create_source(db_session: AsyncSession, *, name: str, status: str = "active") -> RagSource:
    source = RagSource(
        title=f"{name} source",
        source_type="internal_policy",
        source_grade="B",
        category="nutrition",
        tags=["test"],
        language="ko",
        status=status,
        version=1,
        content_hash=f"{name}-source-hash",
    )
    db_session.add(source)
    await db_session.flush()
    return source


async def _create_chunk(
    db_session: AsyncSession,
    source: RagSource,
    *,
    name: str,
    chunk_index: int,
    status: str = "active",
    index_status: str = "indexed",
) -> RagChunk:
    chunk = RagChunk(
        source_id=source.id,
        chunk_index=chunk_index,
        title=name,
        content=f"{name} content",
        content_hash=f"{name}-chunk-hash",
        category=source.category,
        tags=["test"],
        embedding=_embedding(),
        embedding_model="gemini-embedding-001",
        embedding_dim=3072,
        opensearch_index="rag_chunks_v1",
        opensearch_document_id=None,
        index_status=index_status,
        status=status,
        version=1,
    )
    db_session.add(chunk)
    await db_session.flush()
    chunk.opensearch_document_id = str(chunk.id)
    return chunk


def _service(db_session: AsyncSession) -> RAGService:
    service = RAGService(db_session, get_settings())
    service.get_embedding = AsyncMock(return_value=_embedding())
    service.index_service.ensure_index = AsyncMock(return_value=True)
    service.index_service.index_chunk = AsyncMock(return_value=None)
    service.index_service.delete_chunk = AsyncMock(return_value=None)
    return service


async def _active_chunk_ids(db_session: AsyncSession, source_id: int) -> list[int]:
    async with AsyncSession(bind=db_session.bind) as fresh:
        rows = (
            await fresh.execute(
                select(RagChunk.id)
                .where(RagChunk.source_id == source_id, RagChunk.status == "active")
                .order_by(RagChunk.id.asc())
            )
        ).scalars().all()
    return [int(value) for value in rows]


# ── C1 archive_source ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_c1_archive_source_marks_delete_failure_per_chunk_and_commits(db_session):
    source = await _create_source(db_session, name="archive-mixed")
    ok_chunk = await _create_chunk(db_session, source, name="archive-ok", chunk_index=1)
    fail_chunk = await _create_chunk(db_session, source, name="archive-fail", chunk_index=2)
    await db_session.commit()
    ok_id, fail_id = ok_chunk.id, fail_chunk.id

    service = _service(db_session)
    service.index_service.delete_chunk = _delete_mock(fail_id)

    result = await service.archive_source(source.id)

    assert sorted(_deleted_ids(service.index_service.delete_chunk)) == sorted([ok_id, fail_id])
    states = await _committed_chunk_states(db_session, [ok_id, fail_id])
    assert states[ok_id] == ("archived", "deleted")
    assert states[fail_id] == ("archived", "failed")
    assert result["sources"] == 1
    assert result["chunks"] == 2
    assert result["delete_failed"] == 1


@pytest.mark.asyncio
async def test_c1_archive_source_all_deletes_fail_does_not_raise(db_session):
    source = await _create_source(db_session, name="archive-all-fail")
    first = await _create_chunk(db_session, source, name="all-fail-1", chunk_index=1)
    second = await _create_chunk(db_session, source, name="all-fail-2", chunk_index=2)
    await db_session.commit()
    ids = [first.id, second.id]

    service = _service(db_session)
    service.index_service.delete_chunk = _always_failing_delete_mock()

    result = await service.archive_source(source.id)

    states = await _committed_chunk_states(db_session, ids)
    assert states == {chunk_id: ("archived", "failed") for chunk_id in ids}
    async with AsyncSession(bind=db_session.bind) as fresh:
        committed_source = await fresh.get(RagSource, source.id)
    assert committed_source is not None
    assert committed_source.status == "archived"
    assert result == {"sources": 1, "chunks": 2, "delete_failed": 2}


@pytest.mark.asyncio
async def test_c1_archive_source_reports_zero_delete_failed_when_all_deletes_succeed(db_session):
    source = await _create_source(db_session, name="archive-all-ok")
    chunk = await _create_chunk(db_session, source, name="all-ok-1", chunk_index=1)
    await db_session.commit()

    service = _service(db_session)

    result = await service.archive_source(source.id)

    states = await _committed_chunk_states(db_session, [chunk.id])
    assert states[chunk.id] == ("archived", "deleted")
    assert result == {"sources": 1, "chunks": 1, "delete_failed": 0}


# ── C2 refresh 경로 ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_c2_partial_refresh_marks_replaced_chunk_delete_failure(db_session):
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
    service = _service(db_session)
    service.url_fetcher = FakeUrlFetcher(original, changed)

    created = await service.register_url(
        url="https://example.org/archive-partial",
        title="Archive Partial Guide",
        category="exercise",
        tags=["refresh"],
        license_value="official-webpage",
    )
    source_id = int(created["source_id"])
    old_ids = await _active_chunk_ids(db_session, source_id)
    assert len(old_ids) >= 2, "partial refresh 준비: 섹션별 chunk가 여러 개여야 한다"

    service.index_service.delete_chunk = _always_failing_delete_mock()
    refreshed = await service.refresh_source(source_id)

    assert refreshed["decision"] == "partial_refresh"
    states = await _committed_chunk_states(db_session, old_ids)
    archived = {chunk_id: state for chunk_id, state in states.items() if state[0] == "archived"}
    assert archived, "partial refresh 준비: 바뀐 섹션의 옛 chunk가 archive되어야 한다"
    assert all(index_status == "failed" for _, index_status in archived.values()), archived

    # 삭제 실패로 refresh job이 실패하지 않는다.
    assert refreshed["status"] == "succeeded"
    job = await db_session.get(RagIngestJob, int(refreshed["job_id"]))
    assert job is not None
    assert job.status == "succeeded"


@pytest.mark.asyncio
async def test_c2_full_reindex_refresh_records_per_chunk_delete_outcome(db_session):
    html = _html_source(
        "First full reindex section content for archive delete outcome.",
        "Second full reindex section content for archive delete outcome.",
        "Third full reindex section content for archive delete outcome.",
    )
    service = _service(db_session)
    service.url_fetcher = FakeUrlFetcher(html)

    created = await service.register_url(
        url="https://example.org/archive-full",
        title="Archive Full Guide",
        category="exercise",
        tags=["refresh"],
        license_value="official-webpage",
    )
    source_id = int(created["source_id"])
    old_ids = await _active_chunk_ids(db_session, source_id)
    assert len(old_ids) >= 2, "full reindex 준비: 옛 chunk가 여러 개여야 한다"
    fail_id = old_ids[0]

    service.index_service.delete_chunk = _delete_mock(fail_id)
    refreshed = await service.refresh_source(source_id, force_full_reindex=True)

    assert refreshed["decision"] == "full_reindex"
    assert sorted(_deleted_ids(service.index_service.delete_chunk)) == sorted(old_ids)
    states = await _committed_chunk_states(db_session, old_ids)
    assert states[fail_id] == ("archived", "failed")
    for chunk_id in old_ids[1:]:
        assert states[chunk_id] == ("archived", "deleted")

    assert refreshed["status"] == "succeeded"
    job = await db_session.get(RagIngestJob, int(refreshed["job_id"]))
    assert job is not None
    assert job.status == "succeeded"


# ── C3·C4 reindex 재시도 ────────────────────────────────────────────────────


async def _reindex_fixture(db_session: AsyncSession) -> dict[str, int]:
    """reindex 재시도 대상과 비대상을 섞어 만든다."""
    archived_source = await _create_source(db_session, name="reindex-archived-source", status="archived")
    active_source = await _create_source(db_session, name="reindex-active-source")

    retry_ok = await _create_chunk(
        db_session, archived_source, name="retry-ok", chunk_index=1, status="archived", index_status="failed"
    )
    retry_fail = await _create_chunk(
        db_session, archived_source, name="retry-fail", chunk_index=2, status="archived", index_status="failed"
    )
    already_deleted = await _create_chunk(
        db_session, archived_source, name="already-deleted", chunk_index=3, status="archived", index_status="deleted"
    )
    # refresh로 archive됐지만 source는 active인 경우
    retry_under_active = await _create_chunk(
        db_session, active_source, name="retry-under-active", chunk_index=1, status="archived", index_status="failed"
    )
    active_pending = await _create_chunk(
        db_session, active_source, name="active-pending", chunk_index=2, status="active", index_status="pending"
    )
    await db_session.commit()
    return {
        "archived_source": archived_source.id,
        "active_source": active_source.id,
        "retry_ok": retry_ok.id,
        "retry_fail": retry_fail.id,
        "already_deleted": already_deleted.id,
        "retry_under_active": retry_under_active.id,
        "active_pending": active_pending.id,
    }


@pytest.mark.asyncio
async def test_c3_reindex_retries_archived_delete_failures_regardless_of_source_status(db_session):
    ids = await _reindex_fixture(db_session)
    service = _service(db_session)
    service.index_service.delete_chunk = _delete_mock(ids["retry_fail"])

    result = await service.reindex()

    deleted_calls = _deleted_ids(service.index_service.delete_chunk)
    assert sorted(deleted_calls) == sorted([ids["retry_ok"], ids["retry_fail"], ids["retry_under_active"]])

    states = await _committed_chunk_states(db_session, list(ids.values()))
    assert states[ids["retry_ok"]] == ("archived", "deleted")
    assert states[ids["retry_under_active"]] == ("archived", "deleted")
    assert states[ids["retry_fail"]] == ("archived", "failed")
    assert states[ids["active_pending"]] == ("active", "indexed")

    assert result["deleted"] == 2
    assert result["delete_failed"] == 1
    # 기존 키는 active chunk만 센다.
    assert result["indexed"] == 1
    assert result["failed"] == 0
    assert result["skipped"] == 0


@pytest.mark.asyncio
async def test_c3_reindex_never_indexes_archived_chunks(db_session):
    ids = await _reindex_fixture(db_session)
    service = _service(db_session)
    service.index_service.delete_chunk = _delete_mock(ids["retry_fail"])

    await service.reindex()

    assert _indexed_chunk_ids(service.index_service.index_chunk) == [ids["active_pending"]]


@pytest.mark.asyncio
async def test_c3_reindex_with_source_id_limits_delete_retry_to_that_source(db_session):
    ids = await _reindex_fixture(db_session)
    service = _service(db_session)

    result = await service.reindex(source_id=ids["archived_source"])

    assert sorted(_deleted_ids(service.index_service.delete_chunk)) == sorted([ids["retry_ok"], ids["retry_fail"]])
    states = await _committed_chunk_states(db_session, list(ids.values()))
    assert states[ids["retry_ok"]] == ("archived", "deleted")
    assert states[ids["retry_fail"]] == ("archived", "deleted")
    # 다른 source의 chunk는 건드리지 않는다.
    assert states[ids["retry_under_active"]] == ("archived", "failed")
    assert states[ids["active_pending"]] == ("active", "pending")
    service.index_service.index_chunk.assert_not_awaited()
    assert result["deleted"] == 2
    assert result["delete_failed"] == 0
    assert result["indexed"] == 0
    assert result["failed"] == 0
    assert result["skipped"] == 0


@pytest.mark.asyncio
async def test_c3_reindex_keeps_failed_when_delete_retry_fails_again(db_session):
    ids = await _reindex_fixture(db_session)
    service = _service(db_session)
    service.index_service.delete_chunk = _always_failing_delete_mock()

    result = await service.reindex(source_id=ids["archived_source"])

    states = await _committed_chunk_states(db_session, [ids["retry_ok"], ids["retry_fail"]])
    assert states[ids["retry_ok"]] == ("archived", "failed")
    assert states[ids["retry_fail"]] == ("archived", "failed")
    assert result["deleted"] == 0
    assert result["delete_failed"] == 2


@pytest.mark.asyncio
async def test_c4_reindex_does_not_touch_already_deleted_archived_chunks(db_session):
    source = await _create_source(db_session, name="c4-source", status="archived")
    chunk = await _create_chunk(
        db_session, source, name="c4-deleted", chunk_index=1, status="archived", index_status="deleted"
    )
    await db_session.commit()

    service = _service(db_session)
    result = await service.reindex()

    service.index_service.delete_chunk.assert_not_awaited()
    service.index_service.index_chunk.assert_not_awaited()
    states = await _committed_chunk_states(db_session, [chunk.id])
    assert states[chunk.id] == ("archived", "deleted")
    assert result["deleted"] == 0
    assert result["delete_failed"] == 0


# ── C5 검색 회귀 방지 ───────────────────────────────────────────────────────


async def _archived_and_active_chunks(db_session: AsyncSession) -> tuple[int, int]:
    """source는 active이고, 한 chunk는 삭제 실패로 archived/failed에 남은 상태."""
    source = await _create_source(db_session, name="c5-source")
    stale = await _create_chunk(
        db_session, source, name="c5-stale", chunk_index=1, status="archived", index_status="failed"
    )
    active = await _create_chunk(db_session, source, name="c5-active", chunk_index=2)
    await db_session.commit()
    return stale.id, active.id


def _hit(chunk_id: int, score: float) -> dict:
    return {"_id": str(chunk_id), "_score": score, "_source": {"chunk_id": str(chunk_id)}}


@pytest.mark.asyncio
async def test_c5_hybrid_search_excludes_archived_chunk_returned_by_opensearch(db_session):
    stale_id, active_id = await _archived_and_active_chunks(db_session)
    service = _service(db_session)
    service.index_service.keyword_search = AsyncMock(return_value=[_hit(stale_id, 9.0), _hit(active_id, 2.0)])
    service.index_service.vector_search = AsyncMock(return_value=[_hit(stale_id, 9.0)])

    results = await service.search("c5 content", category="nutrition", top_k=5)

    assert [item["chunk_id"] for item in results] == [active_id]
    assert results[0]["search_backend"] == "opensearch"


@pytest.mark.asyncio
async def test_c5_keyword_fallback_search_excludes_archived_chunk_returned_by_opensearch(db_session):
    stale_id, active_id = await _archived_and_active_chunks(db_session)
    service = _service(db_session)
    service.get_embedding = AsyncMock(side_effect=RuntimeError("embedding unavailable"))
    service.index_service.keyword_search = AsyncMock(return_value=[_hit(stale_id, 9.0), _hit(active_id, 2.0)])

    results = await service.search("c5 content", category="nutrition", top_k=5)

    assert [item["chunk_id"] for item in results] == [active_id]
    assert results[0]["search_backend"] == "opensearch_keyword_fallback"
