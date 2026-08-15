"""scrub legacy AI query text copies

Revision ID: a8192a3b4c5d
Revises: f708192a3b4c
Create Date: 2026-07-12 16:00:00.000000

Redacted text is intentionally not recoverable on downgrade.
"""

import hashlib
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8192a3b4c5d"
down_revision: Union[str, Sequence[str], None] = "f708192a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    decision_rows = connection.execute(
        sa.text(
            "SELECT id, context->>'query' AS query_text "
            "FROM rag_pipeline_decisions "
            "WHERE context ? 'query' ORDER BY id"
        )
    ).mappings().all()
    for row in decision_rows:
        query_text = str(row["query_text"] or "")
        legacy_hash = hashlib.sha256(
            f"legacy-redacted\0{query_text}".encode("utf-8")
        ).hexdigest()
        connection.execute(
            sa.text(
                "UPDATE rag_pipeline_decisions SET context = "
                "(context - 'query') || jsonb_build_object("
                "'query_hash', CAST(:query_hash AS text), "
                "'query_summary', CAST(:query_summary AS text), "
                "'query_policy_version', 'legacy-redaction-v1', "
                "'query_key_version', 'legacy-unkeyed-v1') "
                "WHERE id = :decision_id"
            ),
            {
                "decision_id": row["id"],
                "query_hash": legacy_hash,
                "query_summary": (
                    f"type=legacy;category=unknown;chars={len(query_text)};"
                    "terms=unknown;raw_stored=false"
                ),
            },
        )

    recommendation_rows = connection.execute(
        sa.text(
            "SELECT id, context_summary FROM ai_recommendations "
            "WHERE context_summary LIKE '% 채팅:%' ORDER BY id"
        )
    ).mappings().all()
    for row in recommendation_rows:
        context_summary = str(row["context_summary"] or "")
        context_type = context_summary.split(" 채팅:", 1)[0].strip() or "general"
        connection.execute(
            sa.text(
                "UPDATE ai_recommendations "
                "SET context_summary = :summary WHERE id = :recommendation_id"
            ),
            {
                "recommendation_id": row["id"],
                "summary": f"{context_type} 채팅 요청 (내용 비저장)",
            },
        )


def downgrade() -> None:
    pass
