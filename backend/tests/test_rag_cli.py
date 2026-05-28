import json

from app.cli.rag import _update_catalog_source_failure_state, _write_v1_validation_report, build_parser


def test_rag_cli_exposes_url_acquisition_commands():
    parser = build_parser()

    assert parser.parse_args(["fetch-preview", "--url", "https://example.org"]).command == "fetch-preview"
    assert (
        parser.parse_args(
            [
                "register-url",
                "--url",
                "https://example.org",
                "--category",
                "exercise",
            ]
        ).command
        == "register-url"
    )
    assert parser.parse_args(["ingest-catalog", "--file", "rag_sources/catalog.json"]).command == "ingest-catalog"
    assert parser.parse_args(["catalog-plan", "--file", "rag_sources/catalog.json"]).command == "catalog-plan"
    assert parser.parse_args(["catalog-runs", "--limit", "5"]).command == "catalog-runs"
    assert parser.parse_args(["catalog-run", "--run-id", "1"]).command == "catalog-run"
    catalog_apply = parser.parse_args(["catalog-apply", "--run-id", "1", "--review-run-id", "2"])
    assert catalog_apply.command == "catalog-apply"
    assert catalog_apply.review_run_id == 2
    assert parser.parse_args(
        ["catalog-apply", "--run-id", "1", "--review-run-id", "2", "--confirm-full-reindex"]
    ).confirm_full_reindex is True
    assert parser.parse_args(
        ["catalog-apply", "--run-id", "1", "--review-run-id", "2", "--apply-approved-only"]
    ).apply_approved_only is True
    assert (
        parser.parse_args(
            [
                "catalog-disable-source",
                "--file",
                "rag_sources/catalog.json",
                "--key",
                "nih",
                "--reason",
                "HTTP 403",
            ]
        ).command
        == "catalog-disable-source"
    )
    assert (
        parser.parse_args(["catalog-enable-source", "--file", "rag_sources/catalog.json", "--key", "nih"]).command
        == "catalog-enable-source"
    )
    replace_source = parser.parse_args(
        [
            "catalog-replace-source",
            "--file",
            "rag_sources/catalog.json",
            "--key",
            "nih",
            "--replacement-url",
            "https://example.org/replacement",
            "--activate",
        ]
    )
    assert replace_source.command == "catalog-replace-source"
    assert replace_source.activate is True
    replacement_preview = parser.parse_args(
        [
            "replacement-preview",
            "--file",
            "rag_sources/catalog.json",
            "--key",
            "nih",
            "--candidate-url",
            "https://example.org/replacement",
            "--acquisition-type",
            "url_html",
            "--report-path",
            "replacement.md",
        ]
    )
    assert replacement_preview.command == "replacement-preview"
    assert replacement_preview.acquisition_type == "url_html"
    replacement_evaluate = parser.parse_args(
        [
            "replacement-evaluate",
            "--candidate-id",
            "7",
            "--min-coverage-score",
            "0.7",
            "--report-path",
            "replacement-eval.md",
        ]
    )
    assert replacement_evaluate.command == "replacement-evaluate"
    assert replacement_evaluate.candidate_id == 7
    assert replacement_evaluate.min_coverage_score == 0.7
    assert parser.parse_args(["scheduler-run", "--force-plan"]).command == "scheduler-run"
    assert parser.parse_args(["scheduler-runs", "--limit", "5"]).command == "scheduler-runs"
    assert parser.parse_args(["scheduler-run-detail", "--run-id", "1"]).command == "scheduler-run-detail"
    assert parser.parse_args(["catalog-review", "--run-id", "1"]).command == "catalog-review"
    assert parser.parse_args(["scheduler-review", "--run-id", "1"]).command == "scheduler-review"
    assert parser.parse_args(["review-runs", "--limit", "5"]).command == "review-runs"
    assert parser.parse_args(["review-run", "--run-id", "1"]).command == "review-run"


def test_catalog_source_failure_state_update_preserves_previous_url_on_activation(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "key": "nih",
                        "url": "https://example.org/old",
                        "category": "supplement",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = _update_catalog_source_failure_state(
        catalog_path,
        key="nih",
        updates={
            "url": "https://example.org/new",
            "replacement_url": "https://example.org/new",
            "enabled": True,
        },
        activate_replacement=True,
    )

    source = result["source"]
    assert source["url"] == "https://example.org/new"
    assert source["reference_urls"] == ["https://example.org/old"]


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
        "url_source_summary": {
            "url_source_count": 1,
            "pdf_url_source_count": 1,
            "local_file_source_count": 1,
            "catalog_source_count": 1,
            "catalog_pdf_url_source_count": 1,
            "catalog_local_file_source_count": 1,
            "html_parser_source_count": 1,
            "markdown_parser_source_count": 1,
            "text_parser_source_count": 0,
            "pdf_text_parser_source_count": 0,
            "source_grade_a_count": 1,
            "etag_present_count": 1,
            "last_modified_present_count": 1,
            "url_pdf_fingerprint_count": 1,
            "local_file_fingerprint_count": 1,
            "scheduled_refresh_count": 1,
            "stale_source_count": 0,
        },
        "catalog_failure_summary": {
            "latest_plan_id": 1,
            "failed_item_count": 1,
            "disabled_item_count": 1,
            "replacement_required_count": 1,
            "disabled_pending_review_count": 0,
            "manual_review_item_count": 1,
            "skipped_blocked_count": 1,
        },
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
        "latest_catalog_plan": {
            "id": 1,
            "status": "succeeded",
            "total_sources": 1,
            "planned_create_count": 0,
            "planned_skip_count": 1,
            "planned_partial_count": 0,
            "planned_full_count": 0,
            "planned_manual_count": 0,
            "planned_defer_count": 0,
            "created_at": "2026-05-04T00:00:00+00:00",
        },
        "latest_scheduler_run": {
            "id": 2,
            "status": "no_change",
            "mode": "plan_only",
            "catalog_count": 2,
            "due_catalog_count": 2,
            "approval_required_count": 0,
            "no_change_count": 2,
            "error_count": 0,
            "plan_run_ids": [1, 2],
            "created_at": "2026-05-09T00:00:00+00:00",
        },
        "latest_review_run": {
            "id": 3,
            "review_type": "scheduler_run",
            "target_run_id": 2,
            "status": "completed",
            "requires_approval": True,
            "recommended_action": "do_not_apply_until_resolved",
            "risk_level": "high",
            "created_at": "2026-05-10T00:00:00+00:00",
        },
        "latest_approval_gate": {
            "id": 4,
            "status": "approval_blocked",
            "approved_review_run_id": 3,
            "approval_status": "blocked",
            "approval_checked_at": "2026-05-19T00:00:00+00:00",
            "approval_error_code": "REVIEW_BLOCKED",
            "approval_error_message": "Review recommendation blocks apply until issues are resolved",
        },
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
    assert b"Source Acquisition Summary" in data
    assert b"Catalog Failure Lifecycle Summary" in data
    assert "단백질 식단 추천".encode("utf-8") in data
    assert "단백질이 부족한 날의 원칙".encode("utf-8") in data
    assert b"Latest Catalog Plan" in data
    assert b"Latest Scheduler Run" in data
    assert b"Latest Review Run" in data
    assert b"Latest Approval Gate" in data
