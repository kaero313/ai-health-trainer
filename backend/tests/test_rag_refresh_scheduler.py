import json
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.rag import RagCatalogPlanRun, RagChunk, RagSchedulerRun, RagSchedulerRunItem, RagSource
from app.services.rag_catalog_control_service import RAGCatalogControlService
from app.services.rag_refresh_scheduler import RAGRefreshSchedulerService


def _embedding(value: float = 0.1) -> list[float]:
    return [value] * 3072


def _markdown_sections(*bodies: str) -> str:
    sections = []
    for index, body in enumerate(bodies, start=1):
        sections.append(f"## Section {index}\n\n{body}")
    return "# Local Guide\n\n" + "\n\n".join(sections)


def _document_catalog_file(tmp_path, *, file_name: str):
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
                        "parser_type": "markdown",
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


def test_scheduler_models_are_exported():
    from app.models import RagSchedulerRun as ExportedRun
    from app.models import RagSchedulerRunItem as ExportedRunItem

    assert ExportedRun is RagSchedulerRun
    assert ExportedRunItem is RagSchedulerRunItem


async def _apply_local_catalog(db_session, catalog_path):
    catalog_service = RAGCatalogControlService(db_session, get_settings())
    catalog_service.rag_service.get_embedding = AsyncMock(return_value=_embedding())
    catalog_service.rag_service.index_service.index_chunk = AsyncMock(return_value=None)
    plan = await catalog_service.create_plan(catalog_file=catalog_path)
    await catalog_service.apply_run(run_id=plan["run"]["id"])


@pytest.mark.asyncio
async def test_scheduler_skips_when_no_due_sources(db_session, tmp_path):
    source_file = tmp_path / "local-guide.md"
    source_file.write_text(
        _markdown_sections("Stable local content long enough for a chunk."),
        encoding="utf-8",
    )
    catalog_path = _document_catalog_file(tmp_path, file_name="local-guide.md")
    await _apply_local_catalog(db_session, catalog_path)
    plan_count_before = await db_session.scalar(select(func.count()).select_from(RagCatalogPlanRun))

    result = await RAGRefreshSchedulerService(db_session, get_settings()).run(catalog_files=[catalog_path])
    item = result["items"][0]
    plan_count_after = await db_session.scalar(select(func.count()).select_from(RagCatalogPlanRun))

    assert result["run"]["status"] == "no_due_sources"
    assert item["status"] == "no_due_sources"
    assert item["due_status"] == "not_due"
    assert item["plan_run_id"] is None
    assert plan_count_after == plan_count_before


@pytest.mark.asyncio
async def test_scheduler_force_plan_creates_no_change_plan(db_session, tmp_path):
    source_file = tmp_path / "local-guide.md"
    source_file.write_text(
        _markdown_sections("Stable local content long enough for a chunk."),
        encoding="utf-8",
    )
    catalog_path = _document_catalog_file(tmp_path, file_name="local-guide.md")
    await _apply_local_catalog(db_session, catalog_path)

    result = await RAGRefreshSchedulerService(db_session, get_settings()).run(
        catalog_files=[catalog_path],
        force_plan=True,
    )
    item = result["items"][0]

    assert result["run"]["status"] == "no_change"
    assert result["run"]["plan_run_ids"]
    assert item["due_status"] == "forced"
    assert item["status"] == "no_change"
    assert item["planned_skip_count"] == 1
    assert item["requires_approval"] is False


@pytest.mark.asyncio
async def test_scheduler_local_change_creates_approval_required_plan_without_apply(db_session, tmp_path):
    source_file = tmp_path / "local-guide.md"
    original = _markdown_sections(
        "Stable section one content with enough text for diffing.",
        "Stable section two content with enough text for diffing.",
        "Stable section three content with enough text for diffing.",
        "Stable section four content with enough text for diffing.",
    )
    changed = _markdown_sections(
        "Changed section one content with enough text for diffing.",
        "Stable section two content with enough text for diffing.",
        "Stable section three content with enough text for diffing.",
        "Stable section four content with enough text for diffing.",
    )
    source_file.write_text(original, encoding="utf-8")
    catalog_path = _document_catalog_file(tmp_path, file_name="local-guide.md")
    await _apply_local_catalog(db_session, catalog_path)
    source_count_before = await db_session.scalar(select(func.count()).select_from(RagSource))
    chunk_count_before = await db_session.scalar(select(func.count()).select_from(RagChunk))

    source_file.write_text(changed, encoding="utf-8")
    result = await RAGRefreshSchedulerService(db_session, get_settings()).run(catalog_files=[catalog_path])
    item = result["items"][0]
    source_count_after = await db_session.scalar(select(func.count()).select_from(RagSource))
    chunk_count_after = await db_session.scalar(select(func.count()).select_from(RagChunk))

    assert result["run"]["status"] == "approval_required"
    assert item["status"] == "approval_required"
    assert item["due_status"] == "due"
    assert item["planned_partial_count"] == 1
    assert item["requires_approval"] is True
    assert source_count_after == source_count_before
    assert chunk_count_after == chunk_count_before


@pytest.mark.asyncio
async def test_scheduler_records_catalog_errors(db_session, tmp_path):
    missing_catalog = tmp_path / "missing-catalog.json"

    result = await RAGRefreshSchedulerService(db_session, get_settings()).run(catalog_files=[missing_catalog])
    stored_run = (await db_session.execute(select(RagSchedulerRun))).scalar_one()
    stored_item = (await db_session.execute(select(RagSchedulerRunItem))).scalar_one()

    assert result["run"]["status"] == "completed_with_errors"
    assert stored_run.error_count == 1
    assert stored_item.status == "completed_with_errors"
    assert stored_item.error_code == "CATALOG_CHECK_FAILED"
