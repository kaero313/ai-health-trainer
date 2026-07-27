import argparse
from datetime import datetime, timedelta, timezone
import json

import pytest
from sqlalchemy import select

import app.cli.ai as ai_cli
from app.cli.ai import build_parser
from app.models.rag import RagRetrievalTrace


def test_ai_cli_exposes_lifecycle_commands():
    parser = build_parser()

    reconcile = parser.parse_args(["reconcile-stale", "--stale-minutes", "15"])
    trace = parser.parse_args(
        [
            "trace",
            "--request-id",
            "00000000-0000-0000-0000-000000000001",
        ]
    )
    privacy = parser.parse_args(["privacy-audit"])
    retention = parser.parse_args(
        ["retrieval-retention", "--limit-groups", "250", "--execute"]
    )
    validate = parser.parse_args(
        [
            "validate-integration",
            "--base-url",
            "http://127.0.0.1:8000/api/v1",
            "--image-path",
            "/tmp/meal.jpg",
            "--report-path",
            "/tmp/report.md",
        ]
    )
    validation_runs = parser.parse_args(["validation-runs", "--limit", "5"])
    validation_run = parser.parse_args(
        ["validation-run", "--run-id", "00000000-0000-0000-0000-000000000001"]
    )
    validation_cleanup = parser.parse_args(
        ["validation-cleanup", "--run-id", "00000000-0000-0000-0000-000000000001"]
    )

    assert reconcile.command == "reconcile-stale"
    assert reconcile.stale_minutes == 15
    assert trace.command == "trace"
    assert privacy.command == "privacy-audit"
    assert retention.command == "retrieval-retention"
    assert retention.limit_groups == 250
    assert retention.execute is True
    assert validate.command == "validate-integration"
    assert validate.image_path == "/tmp/meal.jpg"
    assert validation_runs.limit == 5
    assert validation_run.command == "validation-run"
    assert validation_cleanup.command == "validation-cleanup"


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args):
        return False


def _retrieval_trace(
    *,
    group_id: str,
    rank: int,
    retention_until: datetime,
) -> RagRetrievalTrace:
    return RagRetrievalTrace(
        user_id=None,
        request_type="chat",
        request_id=None,
        rag_trace_group_id=group_id,
        query_text=None,
        query_hash=(group_id.encode("utf-8").hex() + "0" * 64)[:64],
        query_summary="type=chat;category=all;chars=1;terms=1;raw_stored=false",
        query_policy_version="query-minimization-v1",
        query_key_version="v1",
        query_retention_until=retention_until,
        query_redacted_at=datetime.now(timezone.utc),
        category_filter=None,
        search_backend="opensearch",
        search_mode="hybrid",
        top_k=3,
        rank=rank,
        used_in_prompt=True,
        used_in_response=False,
    )


@pytest.mark.asyncio
async def test_retrieval_retention_deletes_complete_groups_only(
    db_session,
    monkeypatch,
    capsys,
):
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            _retrieval_trace(
                group_id="expired-group",
                rank=1,
                retention_until=now - timedelta(days=1),
            ),
            _retrieval_trace(
                group_id="expired-group",
                rank=2,
                retention_until=now - timedelta(days=1),
            ),
            _retrieval_trace(
                group_id="mixed-group",
                rank=1,
                retention_until=now - timedelta(days=1),
            ),
            _retrieval_trace(
                group_id="mixed-group",
                rank=2,
                retention_until=now + timedelta(days=1),
            ),
        ]
    )
    await db_session.commit()
    monkeypatch.setattr(
        ai_cli,
        "AsyncSessionLocal",
        lambda: _SessionContext(db_session),
    )

    await ai_cli._retrieval_retention(
        argparse.Namespace(execute=True, limit_groups=10)
    )

    payload = json.loads(capsys.readouterr().out)
    remaining_groups = set(
        (
            await db_session.execute(
                select(RagRetrievalTrace.rag_trace_group_id)
            )
        ).scalars()
    )
    assert payload["eligible_groups"] == 1
    assert payload["eligible_rows"] == 2
    assert payload["deleted_rows"] == 2
    assert remaining_groups == {"mixed-group"}
