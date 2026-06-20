import json
from argparse import Namespace

import pytest

from app.cli.rag import (
    _catalog_replace_source,
    _load_replacement_activation_metadata,
    _update_catalog_source_failure_state,
)
from app.models.rag import RagSourceReplacementCandidate, RagSourceReplacementEvaluation
from app.services.rag_replacement_candidate_service import STATUS_FETCH_FAILED, STATUS_PREVIEW_SUCCEEDED
from app.services.rag_replacement_evaluation_service import RECOMMEND_READY, STATUS_MANUAL_REVIEW, STATUS_READY, STATUS_REJECTED


async def _candidate(db_session, *, key: str = "nih", url: str = "https://example.org/new", status: str = STATUS_PREVIEW_SUCCEEDED):
    candidate = RagSourceReplacementCandidate(
        catalog_key=key,
        original_url="https://example.org/old",
        candidate_url=url,
        acquisition_type="url_html",
        status=status,
        parser_type="html",
        parser_confidence=0.95 if status == STATUS_PREVIEW_SUCCEEDED else None,
        content_hash="a" * 64 if status == STATUS_PREVIEW_SUCCEEDED else None,
        raw_content_hash="b" * 64 if status == STATUS_PREVIEW_SUCCEEDED else None,
        content_type="text/html",
        content_length=1024,
        section_count=3,
        chunk_count=3,
        source_grade="A",
        license="official-webpage",
        author_or_org="Example Org",
        quality_warnings=[] if status == STATUS_PREVIEW_SUCCEEDED else ["candidate_fetch_failed"],
        context={"no_mutation_performed": True},
    )
    db_session.add(candidate)
    await db_session.flush()
    return candidate


async def _evaluation(
    db_session,
    *,
    candidate: RagSourceReplacementCandidate,
    key: str = "nih",
    url: str = "https://example.org/new",
    status: str = STATUS_READY,
    recommendation: str = RECOMMEND_READY,
) -> RagSourceReplacementEvaluation:
    evaluation = RagSourceReplacementEvaluation(
        candidate_id=candidate.id,
        catalog_key=key,
        candidate_url=url,
        status=status,
        readiness_score=0.91,
        coverage_score=0.82,
        metadata_score=1.0,
        parser_score=0.95,
        risk_level="low",
        recommendation=recommendation,
        blocking_reasons=[],
        quality_warnings=[],
        required_terms=["exercise"],
        matched_terms=["exercise"],
        missing_terms=[],
        context={"no_mutation_performed": True},
    )
    db_session.add(evaluation)
    await db_session.flush()
    return evaluation


def _catalog_file(tmp_path):
    path = tmp_path / "catalog.json"
    payload = {
        "sources": [
            {
                "key": "nih",
                "url": "https://example.org/old",
                "category": "supplement",
                "enabled": False,
                "disabled_reason": "HTTP 403",
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_catalog_replace_source_activate_requires_evaluation_id(tmp_path):
    catalog_path = _catalog_file(tmp_path)
    before = catalog_path.read_text(encoding="utf-8")

    with pytest.raises(SystemExit, match="--evaluation-id is required"):
        await _catalog_replace_source(
            Namespace(
                file=str(catalog_path),
                key="nih",
                replacement_url="https://example.org/new",
                activate=True,
                evaluation_id=None,
            )
        )

    assert catalog_path.read_text(encoding="utf-8") == before


@pytest.mark.asyncio
async def test_replacement_activation_metadata_allows_ready_candidate_and_catalog_update(db_session, tmp_path):
    candidate = await _candidate(db_session)
    evaluation = await _evaluation(db_session, candidate=candidate)

    metadata = await _load_replacement_activation_metadata(
        db_session,
        key="nih",
        replacement_url="https://example.org/new",
        evaluation_id=evaluation.id,
    )
    catalog_path = _catalog_file(tmp_path)
    result = _update_catalog_source_failure_state(
        catalog_path,
        key="nih",
        updates={
            "url": "https://example.org/new",
            "enabled": True,
            "disabled_reason": None,
            "disabled_at": None,
            "replacement_activated_at": "2026-06-20T00:00:00+00:00",
            **metadata,
        },
        activate_replacement=True,
    )

    source = result["source"]
    assert source["url"] == "https://example.org/new"
    assert source["reference_urls"] == ["https://example.org/old"]
    assert source["replacement_evaluation_id"] == evaluation.id
    assert source["replacement_candidate_id"] == candidate.id
    assert source["replacement_readiness_score"] == 0.91
    assert source["replacement_coverage_score"] == 0.82


@pytest.mark.asyncio
async def test_replacement_activation_blocks_rejected_or_manual_review_evaluation(db_session):
    candidate = await _candidate(db_session)
    rejected = await _evaluation(db_session, candidate=candidate, status=STATUS_REJECTED, recommendation="reject_candidate")
    manual = await _evaluation(
        db_session,
        candidate=candidate,
        status=STATUS_MANUAL_REVIEW,
        recommendation="manual_review_before_activation",
    )

    with pytest.raises(SystemExit, match="not ready for activation"):
        await _load_replacement_activation_metadata(
            db_session,
            key="nih",
            replacement_url="https://example.org/new",
            evaluation_id=rejected.id,
        )
    with pytest.raises(SystemExit, match="not ready for activation"):
        await _load_replacement_activation_metadata(
            db_session,
            key="nih",
            replacement_url="https://example.org/new",
            evaluation_id=manual.id,
        )


@pytest.mark.asyncio
async def test_replacement_activation_blocks_url_and_key_mismatch(db_session):
    candidate = await _candidate(db_session)
    evaluation = await _evaluation(db_session, candidate=candidate)

    with pytest.raises(SystemExit, match="catalog key mismatch"):
        await _load_replacement_activation_metadata(
            db_session,
            key="cdc",
            replacement_url="https://example.org/new",
            evaluation_id=evaluation.id,
        )
    with pytest.raises(SystemExit, match="candidate URL does not match"):
        await _load_replacement_activation_metadata(
            db_session,
            key="nih",
            replacement_url="https://example.org/other",
            evaluation_id=evaluation.id,
        )


@pytest.mark.asyncio
async def test_replacement_activation_blocks_non_successful_candidate_preview(db_session):
    candidate = await _candidate(db_session, status=STATUS_FETCH_FAILED)
    evaluation = await _evaluation(db_session, candidate=candidate)

    with pytest.raises(SystemExit, match="candidate preview is not successful"):
        await _load_replacement_activation_metadata(
            db_session,
            key="nih",
            replacement_url="https://example.org/new",
            evaluation_id=evaluation.id,
        )
