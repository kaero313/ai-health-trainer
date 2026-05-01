import json

import pytest

from app.services.rag_evaluation import RetrievalEvaluationCase, evaluate_retrieval, load_retrieval_cases


class FakeRAGService:
    def __init__(self, documents_by_query: dict[str, list[dict]]):
        self.documents_by_query = documents_by_query
        self.calls: list[dict] = []

    async def search(self, query: str, category: str | None = None, top_k: int = 3, **kwargs):
        self.calls.append(
            {
                "query": query,
                "category": category,
                "top_k": top_k,
                "request_type": kwargs.get("request_type"),
            }
        )
        return self.documents_by_query.get(query, [])[:top_k]


def test_load_retrieval_cases(tmp_path):
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "query": "protein query",
                    "expected_categories": ["nutrition"],
                    "expected_tags": ["protein"],
                    "expected_source_keywords": ["protein"],
                    "category_filter": "nutrition",
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_retrieval_cases(cases_path)

    assert len(cases) == 1
    assert cases[0].query == "protein query"
    assert cases[0].expected_categories == ["nutrition"]
    assert cases[0].expected_tags == ["protein"]
    assert cases[0].expected_source_keywords == ["protein"]
    assert cases[0].category_filter == "nutrition"


@pytest.mark.asyncio
async def test_evaluate_retrieval_scores_category_tag_and_source_matches():
    service = FakeRAGService(
        {
            "protein query": [
                {
                    "title": "Protein meal examples",
                    "source_title": "Protein source",
                    "category": "nutrition",
                    "tags": ["protein", "diet"],
                }
            ],
            "pain query": [
                {
                    "title": "Joint pain boundary",
                    "source_title": "Safety source",
                    "category": "safety",
                    "tags": ["pain"],
                }
            ],
        }
    )
    cases = [
        RetrievalEvaluationCase(
            query="protein query",
            expected_categories=["nutrition"],
            expected_tags=["protein"],
            expected_source_keywords=["protein"],
            category_filter="nutrition",
        ),
        RetrievalEvaluationCase(
            query="pain query",
            expected_categories=["safety"],
            expected_tags=["medical_referral"],
            expected_source_keywords=["safety"],
            category_filter="safety",
        ),
    ]

    result = await evaluate_retrieval(service, cases, top_k=2)

    assert result["total"] == 2
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["pass_rate"] == 0.5
    assert result["results"][0]["passed"] is True
    assert result["results"][1]["tag_matched"] is False
    assert service.calls == [
        {
            "query": "protein query",
            "category": "nutrition",
            "top_k": 2,
            "request_type": "evaluation",
        },
        {
            "query": "pain query",
            "category": "safety",
            "top_k": 2,
            "request_type": "evaluation",
        },
    ]
