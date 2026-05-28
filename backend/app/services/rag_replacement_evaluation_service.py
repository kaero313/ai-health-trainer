from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.rag import RagChunk, RagSource, RagSourceReplacementCandidate, RagSourceReplacementEvaluation
from app.services.rag_replacement_candidate_service import STATUS_PREVIEW_SUCCEEDED


STATUS_READY = "ready_for_activation"
STATUS_MANUAL_REVIEW = "needs_manual_review"
STATUS_REJECTED = "rejected"

RECOMMEND_READY = "candidate_ready_for_activation"
RECOMMEND_REVIEW = "manual_review_before_activation"
RECOMMEND_REJECT = "reject_candidate"

DEFAULT_MIN_COVERAGE_SCORE = 0.6
DEFAULT_MIN_READINESS_SCORE = 0.7

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "guideline",
    "guidelines",
    "official",
    "page",
    "sheet",
    "source",
    "the",
    "this",
    "with",
}


class RAGReplacementEvaluationService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    async def evaluate(
        self,
        *,
        candidate_id: int,
        report_path: str | Path | None = None,
        min_coverage_score: float = DEFAULT_MIN_COVERAGE_SCORE,
        min_readiness_score: float = DEFAULT_MIN_READINESS_SCORE,
    ) -> dict[str, Any]:
        candidate = await self.db.get(RagSourceReplacementCandidate, candidate_id)
        if candidate is None:
            return {"status": "not_found", "candidate_id": candidate_id}

        source = await self.db.get(RagSource, candidate.source_id) if candidate.source_id else None
        source_chunks = await self._source_chunks(candidate.source_id)

        required_terms = _required_terms(candidate, source_chunks)
        evidence_terms = _evidence_terms(candidate)
        matched_terms = sorted(required_terms & evidence_terms)
        missing_terms = sorted(required_terms - evidence_terms)
        coverage_score = _ratio(len(matched_terms), len(required_terms))
        parser_score = _parser_score(candidate)
        metadata_score = _metadata_score(candidate)
        readiness_score = round(coverage_score * 0.55 + parser_score * 0.25 + metadata_score * 0.20, 4)

        blocking_reasons: list[str] = []
        quality_warnings = list(candidate.quality_warnings or [])
        if candidate.status != STATUS_PREVIEW_SUCCEEDED:
            blocking_reasons.append("candidate_preview_not_succeeded")
        if parser_score < 0.7:
            blocking_reasons.append("parser_or_chunk_quality_below_threshold")
        if coverage_score < min_coverage_score:
            quality_warnings.append("coverage_below_threshold")
        if readiness_score < min_readiness_score:
            quality_warnings.append("readiness_below_threshold")
        if metadata_score < 0.6:
            quality_warnings.append("metadata_incomplete_or_low_grade")

        if blocking_reasons or coverage_score < 0.25:
            status = STATUS_REJECTED
            recommendation = RECOMMEND_REJECT
            risk_level = "high"
        elif (
            coverage_score >= min_coverage_score
            and readiness_score >= min_readiness_score
            and metadata_score >= 0.6
            and candidate.status == STATUS_PREVIEW_SUCCEEDED
        ):
            status = STATUS_READY
            recommendation = RECOMMEND_READY
            risk_level = "low" if readiness_score >= 0.85 else "medium"
        else:
            status = STATUS_MANUAL_REVIEW
            recommendation = RECOMMEND_REVIEW
            risk_level = "medium"

        evaluation = RagSourceReplacementEvaluation(
            candidate_id=candidate.id,
            source_id=candidate.source_id,
            catalog_key=candidate.catalog_key,
            candidate_url=candidate.candidate_url,
            status=status,
            readiness_score=readiness_score,
            coverage_score=coverage_score,
            metadata_score=metadata_score,
            parser_score=parser_score,
            risk_level=risk_level,
            recommendation=recommendation,
            blocking_reasons=sorted(set(blocking_reasons)),
            quality_warnings=sorted(set(quality_warnings)),
            required_terms=sorted(required_terms),
            matched_terms=matched_terms,
            missing_terms=missing_terms,
            context={
                "candidate_status": candidate.status,
                "candidate_parser_type": candidate.parser_type,
                "candidate_parser_confidence": candidate.parser_confidence,
                "candidate_chunk_count": candidate.chunk_count,
                "candidate_source_grade": candidate.source_grade,
                "catalog_title": _candidate_context(candidate).get("catalog_title"),
                "catalog_category": _candidate_context(candidate).get("catalog_category"),
                "catalog_tags": _candidate_context(candidate).get("catalog_tags") or [],
                "source_id": source.id if source else None,
                "source_title": source.title if source else None,
                "source_chunk_count": len(source_chunks),
                "thresholds": {
                    "min_coverage_score": min_coverage_score,
                    "min_readiness_score": min_readiness_score,
                },
                "no_mutation_performed": True,
            },
            report_path=str(report_path) if report_path else None,
        )
        self.db.add(evaluation)
        await self.db.flush()
        result = self._evaluation_summary(evaluation)
        await self.db.commit()
        if report_path:
            self.write_evaluation_report(result, Path(report_path))
        return result

    async def _source_chunks(self, source_id: int | None) -> list[RagChunk]:
        if source_id is None:
            return []
        rows = await self.db.execute(
            select(RagChunk)
            .where(RagChunk.source_id == source_id, RagChunk.status == "active")
            .order_by(RagChunk.chunk_index.asc())
        )
        return list(rows.scalars().all())

    @staticmethod
    def _evaluation_summary(evaluation: RagSourceReplacementEvaluation) -> dict[str, Any]:
        return {
            "id": evaluation.id,
            "candidate_id": evaluation.candidate_id,
            "source_id": evaluation.source_id,
            "catalog_key": evaluation.catalog_key,
            "candidate_url": evaluation.candidate_url,
            "status": evaluation.status,
            "readiness_score": evaluation.readiness_score,
            "coverage_score": evaluation.coverage_score,
            "metadata_score": evaluation.metadata_score,
            "parser_score": evaluation.parser_score,
            "risk_level": evaluation.risk_level,
            "recommendation": evaluation.recommendation,
            "blocking_reasons": evaluation.blocking_reasons,
            "quality_warnings": evaluation.quality_warnings,
            "required_terms": evaluation.required_terms,
            "matched_terms": evaluation.matched_terms,
            "missing_terms": evaluation.missing_terms,
            "context": evaluation.context,
            "report_path": evaluation.report_path,
            "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
        }

    @staticmethod
    def write_evaluation_report(result: dict[str, Any], report_path: Path) -> None:
        lines = [
            "# RAG Replacement Candidate Evaluation",
            "",
            "> This report is coverage/readiness audit only. No RAG source, chunk, embedding, OpenSearch index, or catalog JSON mutation was performed.",
            "",
            "## Summary",
            "",
            f"- evaluation_id: {result.get('id')}",
            f"- candidate_id: {result.get('candidate_id')}",
            f"- catalog_key: {result.get('catalog_key') or ''}",
            f"- status: {result.get('status')}",
            f"- recommendation: {result.get('recommendation')}",
            f"- risk_level: {result.get('risk_level')}",
            "",
            "## Scores",
            "",
            f"- readiness_score: {result.get('readiness_score')}",
            f"- coverage_score: {result.get('coverage_score')}",
            f"- parser_score: {result.get('parser_score')}",
            f"- metadata_score: {result.get('metadata_score')}",
            "",
            "## Coverage Terms",
            "",
            f"- required_terms: {', '.join(result.get('required_terms') or [])}",
            f"- matched_terms: {', '.join(result.get('matched_terms') or [])}",
            f"- missing_terms: {', '.join(result.get('missing_terms') or [])}",
            "",
            "## Quality And Blocking Signals",
            "",
            f"- blocking_reasons: {', '.join(result.get('blocking_reasons') or [])}",
            f"- quality_warnings: {', '.join(result.get('quality_warnings') or [])}",
            "",
            "## Context",
            "",
            f"- candidate_url: {result.get('candidate_url')}",
            f"- source_id: {result.get('source_id') or ''}",
            f"- source_title: {(result.get('context') or {}).get('source_title') or ''}",
            f"- source_chunk_count: {(result.get('context') or {}).get('source_chunk_count')}",
            f"- candidate_status: {(result.get('context') or {}).get('candidate_status')}",
            f"- candidate_parser_type: {(result.get('context') or {}).get('candidate_parser_type') or ''}",
            f"- candidate_chunk_count: {(result.get('context') or {}).get('candidate_chunk_count')}",
            "",
        ]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _candidate_context(candidate: RagSourceReplacementCandidate) -> dict[str, Any]:
    context = candidate.context if isinstance(candidate.context, dict) else {}
    return context


def _required_terms(candidate: RagSourceReplacementCandidate, source_chunks: list[RagChunk]) -> set[str]:
    context = _candidate_context(candidate)
    source_values: list[Any] = [
        context.get("catalog_title"),
        context.get("catalog_category"),
        " ".join(context.get("catalog_tags") or []),
        candidate.catalog_key,
    ]
    terms = _tokens(" ".join(str(value or "") for value in source_values))
    if len(terms) < 4 and source_chunks:
        for chunk in source_chunks[:3]:
            source_values.append(chunk.title)
        terms = _tokens(" ".join(str(value or "") for value in source_values))
    if len(terms) > 12:
        title_terms = _tokens(
            " ".join(
                str(value or "")
                for value in [
                    context.get("catalog_title"),
                    context.get("catalog_category"),
                    " ".join(context.get("catalog_tags") or []),
                ]
            )
        )
        prioritized = [term for term in sorted(terms) if term in title_terms]
        remainder = [term for term in sorted(terms) if term not in title_terms]
        return set((prioritized + remainder)[:12])
    return terms


def _evidence_terms(candidate: RagSourceReplacementCandidate) -> set[str]:
    context = _candidate_context(candidate)
    values: list[Any] = []
    for item in context.get("chunk_preview") or []:
        if isinstance(item, dict):
            values.append(item.get("preview"))
    return _tokens(" ".join(str(value or "") for value in values))


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(value.lower().replace("_", " "))
        if len(token) >= 3 and not token.isdigit() and token not in _STOPWORDS
    }


def _ratio(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total, 4)


def _parser_score(candidate: RagSourceReplacementCandidate) -> float:
    confidence = float(candidate.parser_confidence or 0.0)
    chunk_component = min(float(candidate.chunk_count or 0) / 3.0, 1.0)
    return round(confidence * 0.7 + chunk_component * 0.3, 4)


def _metadata_score(candidate: RagSourceReplacementCandidate) -> float:
    score = 0.0
    if (candidate.source_grade or "").upper() in {"A", "B"}:
        score += 0.35
    elif candidate.source_grade:
        score += 0.15
    if candidate.license:
        score += 0.2
    if candidate.author_or_org:
        score += 0.2
    if candidate.content_type:
        score += 0.1
    if _candidate_context(candidate).get("final_url"):
        score += 0.15
    return round(min(score, 1.0), 4)
