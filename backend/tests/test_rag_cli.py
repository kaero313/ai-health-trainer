from app.cli.rag import _write_v1_validation_report


def test_v1_validation_report_writer_preserves_utf8_and_lf(tmp_path):
    report_path = tmp_path / "report.md"
    report = {
        "evaluation": {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "pass_rate": 1.0,
            "fallback_count": 0,
            "safety_source_hit_count": 0,
            "source_grade_hit_count": 1,
            "results": [
                {
                    "query": "단백질 식단 추천",
                    "passed": True,
                    "category_matched": True,
                    "tag_matched": True,
                    "source_matched": True,
                    "fallback_used": False,
                    "top_titles": ["단백질이 부족한 날의 원칙"],
                }
            ],
        },
        "db_counts": {"rag_sources": 1, "rag_chunks_active": 1},
        "decision_summary": [
            {"selected_action": "create_source", "reason_code": "NEW_SOURCE", "count": 1}
        ],
        "recent_jobs": [
            {
                "id": 1,
                "job_type": "create",
                "source_id": 1,
                "status": "succeeded",
                "pipeline_stage": "finished",
                "change_ratio": 1.0,
                "chunks_total": 1,
                "chunks_succeeded": 1,
                "embedding_reuse_count": 0,
                "reembedding_count": 1,
                "index_skip_count": 0,
            }
        ],
        "index_status": {
            "index": "rag_chunks_v1",
            "alias": "rag_chunks_current",
            "exists": True,
            "alias_exists": True,
            "docs_count": 1,
        },
    }

    _write_v1_validation_report(report, report_path)

    data = report_path.read_bytes()
    assert b"\r\n" not in data
    assert "단백질 식단 추천".encode("utf-8") in data
    assert "단백질이 부족한 날의 원칙".encode("utf-8") in data
