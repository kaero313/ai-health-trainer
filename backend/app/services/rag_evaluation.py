from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.rag_service import RAGService


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    query: str
    expected_categories: list[str]
    expected_tags: list[str]
    expected_source_keywords: list[str]
    category_filter: str | None = None


@dataclass(frozen=True)
class RetrievalEvaluationResult:
    query: str
    passed: bool
    category_matched: bool
    tag_matched: bool
    source_matched: bool
    top_titles: list[str]


def load_retrieval_cases(path: str | Path) -> list[RetrievalEvaluationCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    cases: list[RetrievalEvaluationCase] = []
    for item in raw_cases:
        cases.append(
            RetrievalEvaluationCase(
                query=str(item["query"]),
                expected_categories=[str(value) for value in item.get("expected_categories", [])],
                expected_tags=[str(value) for value in item.get("expected_tags", [])],
                expected_source_keywords=[
                    str(value).lower() for value in item.get("expected_source_keywords", [])
                ],
                category_filter=item.get("category_filter"),
            )
        )
    return cases


async def evaluate_retrieval(
    rag_service: RAGService,
    cases: list[RetrievalEvaluationCase],
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    results: list[RetrievalEvaluationResult] = []
    for case in cases:
        documents = await rag_service.search(
            case.query,
            category=case.category_filter,
            top_k=top_k,
            request_type="evaluation",
        )
        results.append(_evaluate_case(case, documents))

    passed = sum(1 for result in results if result.passed)
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "results": [
            {
                "query": result.query,
                "passed": result.passed,
                "category_matched": result.category_matched,
                "tag_matched": result.tag_matched,
                "source_matched": result.source_matched,
                "top_titles": result.top_titles,
            }
            for result in results
        ],
    }


def _evaluate_case(case: RetrievalEvaluationCase, documents: list[dict]) -> RetrievalEvaluationResult:
    categories = {str(document.get("category") or "") for document in documents}
    tags = {
        str(tag)
        for document in documents
        for tag in (document.get("tags") or [])
    }
    title_blob = "\n".join(
        str(document.get("title") or "") + "\n" + str(document.get("source_title") or "")
        for document in documents
    ).lower()

    category_matched = not case.expected_categories or bool(categories.intersection(case.expected_categories))
    tag_matched = not case.expected_tags or bool(tags.intersection(case.expected_tags))
    source_matched = not case.expected_source_keywords or any(
        keyword in title_blob for keyword in case.expected_source_keywords
    )

    return RetrievalEvaluationResult(
        query=case.query,
        passed=category_matched and tag_matched and source_matched,
        category_matched=category_matched,
        tag_matched=tag_matched,
        source_matched=source_matched,
        top_titles=[str(document.get("title") or "") for document in documents],
    )
