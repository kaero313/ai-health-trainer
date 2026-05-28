import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.rag import RagChunk, RagSource, RagSourceReplacementCandidate, RagSourceReplacementEvaluation
from app.services.rag_replacement_candidate_service import STATUS_FETCH_FAILED, STATUS_PREVIEW_SUCCEEDED
from app.services.rag_replacement_evaluation_service import RAGReplacementEvaluationService


def _embedding() -> list[float]:
    return [0.0] * 3072


async def _source(db_session) -> RagSource:
    source = RagSource(
        title="NIH ODS Dietary Supplements for Exercise and Athletic Performance Fact Sheet",
        source_type="official_guideline",
        source_url="https://example.org/original",
        origin_type="url_html",
        origin_uri="https://example.org/original",
        ingest_method="catalog",
        parser_type="html",
        content_hash="a" * 64,
        source_grade="A",
        license="official-webpage",
        category="supplement",
        tags=["supplement", "exercise", "performance"],
        language="en",
        author_or_org="NIH ODS",
        metadata_={"fetch_metadata": {"catalog_key": "nih_ods_exercise_athletic_performance_fact_sheet"}},
    )
    db_session.add(source)
    await db_session.flush()
    db_session.add(
        RagChunk(
            source_id=source.id,
            chunk_index=0,
            title="Dietary supplements for exercise and athletic performance",
            content=(
                "Dietary supplements for exercise and athletic performance include caffeine, creatine, "
                "protein, safety considerations, and evidence quality for athletes."
            ),
            content_hash="b" * 64,
            anchor_hash="anchor",
            embedding_input_hash="c" * 64,
            index_payload_hash="d" * 64,
            category="supplement",
            tags=["supplement", "exercise", "performance"],
            embedding=_embedding(),
            embedding_model="gemini-embedding-001",
            index_status="indexed",
            status="active",
        )
    )
    await db_session.flush()
    return source


async def _candidate(
    db_session,
    *,
    source: RagSource | None,
    status: str = STATUS_PREVIEW_SUCCEEDED,
    content: str,
    source_grade: str = "A",
) -> RagSourceReplacementCandidate:
    candidate = RagSourceReplacementCandidate(
        source_id=source.id if source else None,
        catalog_key="nih_ods_exercise_athletic_performance_fact_sheet",
        original_url="https://example.org/original",
        candidate_url="https://example.org/replacement",
        acquisition_type="url_html",
        status=status,
        parser_type="html",
        parser_confidence=0.95 if status == STATUS_PREVIEW_SUCCEEDED else None,
        content_hash="e" * 64 if status == STATUS_PREVIEW_SUCCEEDED else None,
        raw_content_hash="f" * 64 if status == STATUS_PREVIEW_SUCCEEDED else None,
        content_type="text/html",
        content_length=2048,
        section_count=3 if status == STATUS_PREVIEW_SUCCEEDED else 0,
        chunk_count=3 if status == STATUS_PREVIEW_SUCCEEDED else 0,
        source_grade=source_grade,
        license="official-webpage",
        author_or_org="NIH ODS",
        quality_warnings=[] if status == STATUS_PREVIEW_SUCCEEDED else ["candidate_fetch_failed"],
        context={
            "catalog_title": "NIH ODS Dietary Supplements for Exercise and Athletic Performance Fact Sheet",
            "catalog_category": "supplement",
            "catalog_tags": ["supplement", "exercise", "performance"],
            "final_url": "https://example.org/replacement",
            "source_title": "NIH ODS Dietary Supplements for Exercise and Athletic Performance Fact Sheet",
            "chunk_preview": [
                {
                    "title": "Dietary supplements for exercise and athletic performance",
                    "preview": content,
                }
            ],
            "no_mutation_performed": True,
        },
    )
    db_session.add(candidate)
    await db_session.flush()
    return candidate


async def _counts(db_session) -> tuple[int, int]:
    source_count = await db_session.scalar(select(func.count()).select_from(RagSource))
    chunk_count = await db_session.scalar(select(func.count()).select_from(RagChunk))
    return int(source_count), int(chunk_count)


@pytest.mark.asyncio
async def test_replacement_evaluation_marks_candidate_ready_without_mutating_rag_data(db_session):
    source = await _source(db_session)
    candidate = await _candidate(
        db_session,
        source=source,
        content=(
            "NIH ODS dietary supplements for exercise and athletic performance cover caffeine, creatine, "
            "protein, safety, evidence, and performance considerations for athletes."
        ),
    )
    before_counts = await _counts(db_session)

    result = await RAGReplacementEvaluationService(db_session, get_settings()).evaluate(candidate_id=candidate.id)

    after_counts = await _counts(db_session)
    stored = (await db_session.execute(select(RagSourceReplacementEvaluation))).scalar_one()
    assert result["status"] == "ready_for_activation"
    assert result["recommendation"] == "candidate_ready_for_activation"
    assert result["coverage_score"] >= 0.6
    assert "exercise" in result["matched_terms"]
    assert stored.candidate_id == candidate.id
    assert after_counts == before_counts


@pytest.mark.asyncio
async def test_replacement_evaluation_rejects_semantic_mismatch(db_session):
    source = await _source(db_session)
    candidate = await _candidate(
        db_session,
        source=source,
        content="Vegetable intake, fruit portions, hydration, food groups, and general nutrition guidance.",
    )

    result = await RAGReplacementEvaluationService(db_session, get_settings()).evaluate(candidate_id=candidate.id)

    assert result["status"] == "rejected"
    assert result["recommendation"] == "reject_candidate"
    assert "coverage_below_threshold" in result["quality_warnings"]


@pytest.mark.asyncio
async def test_replacement_evaluation_rejects_non_successful_candidate_preview(db_session):
    source = await _source(db_session)
    candidate = await _candidate(
        db_session,
        source=source,
        status=STATUS_FETCH_FAILED,
        content="",
    )

    result = await RAGReplacementEvaluationService(db_session, get_settings()).evaluate(candidate_id=candidate.id)

    assert result["status"] == "rejected"
    assert "candidate_preview_not_succeeded" in result["blocking_reasons"]


@pytest.mark.asyncio
async def test_replacement_evaluation_report_preserves_utf8_and_lf(db_session, tmp_path):
    source = await _source(db_session)
    source.title = "공식 대체 후보 검증"
    await db_session.flush()
    candidate = await _candidate(
        db_session,
        source=source,
        content="NIH ODS supplement exercise performance safety evidence. 공식 대체 후보 검증.",
    )
    report_path = tmp_path / "replacement-evaluation.md"

    await RAGReplacementEvaluationService(db_session, get_settings()).evaluate(
        candidate_id=candidate.id,
        report_path=report_path,
    )

    data = report_path.read_bytes()
    assert b"\r\n" not in data
    assert b"RAG Replacement Candidate Evaluation" in data
    assert b"No RAG source, chunk, embedding, OpenSearch index, or catalog JSON mutation" in data
    assert "공식 대체 후보 검증".encode("utf-8") in data
