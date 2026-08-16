"""minimize retrieval query traces

Revision ID: e6f708192a3b
Revises: d5e6f708192a
Create Date: 2026-07-12 15:00:00.000000

Raw retrieval queries are intentionally not recoverable on downgrade.
"""

from datetime import timedelta
import hashlib
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f708192a3b"
down_revision: Union[str, Sequence[str], None] = "d5e6f708192a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rag_retrieval_traces",
        sa.Column("query_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "rag_retrieval_traces",
        sa.Column("query_summary", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "rag_retrieval_traces",
        sa.Column("query_policy_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "rag_retrieval_traces",
        sa.Column("query_retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "rag_retrieval_traces",
        sa.Column("query_redacted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("rag_retrieval_traces", "query_text", nullable=True)

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, query_text, created_at "
            "FROM rag_retrieval_traces ORDER BY id"
        )
    ).mappings().all()
    for row in rows:
        query_text = str(row["query_text"] or "")
        created_at = row["created_at"]
        legacy_hash = hashlib.sha256(
            f"legacy-redacted\0{query_text}".encode("utf-8")
        ).hexdigest()
        connection.execute(
            sa.text(
                "UPDATE rag_retrieval_traces SET "
                "query_text = NULL, query_hash = :query_hash, "
                "query_summary = :query_summary, "
                "query_policy_version = 'legacy-redaction-v1', "
                "query_retention_until = :retention_until, "
                "query_redacted_at = now() WHERE id = :trace_id"
            ),
            {
                "trace_id": row["id"],
                "query_hash": legacy_hash,
                "query_summary": (
                    f"type=legacy;category=unknown;chars={len(query_text)};"
                    "terms=unknown;raw_stored=false"
                ),
                "retention_until": created_at + timedelta(days=90),
            },
        )

    op.alter_column("rag_retrieval_traces", "query_hash", nullable=False)
    op.alter_column("rag_retrieval_traces", "query_summary", nullable=False)
    op.alter_column("rag_retrieval_traces", "query_policy_version", nullable=False)
    op.alter_column("rag_retrieval_traces", "query_retention_until", nullable=False)
    op.alter_column("rag_retrieval_traces", "query_redacted_at", nullable=False)
    op.create_check_constraint(
        "ck_rag_retrieval_traces_query_text_redacted",
        "rag_retrieval_traces",
        "query_text IS NULL",
    )
    op.create_index(
        "ix_rag_retrieval_traces_query_hash",
        "rag_retrieval_traces",
        ["query_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rag_retrieval_traces_query_hash",
        table_name="rag_retrieval_traces",
    )
    op.drop_constraint(
        "ck_rag_retrieval_traces_query_text_redacted",
        "rag_retrieval_traces",
        type_="check",
    )
    op.execute(
        "UPDATE rag_retrieval_traces "
        "SET query_text = '[redacted] ' || query_summary "
        "WHERE query_text IS NULL"
    )
    op.alter_column("rag_retrieval_traces", "query_text", nullable=False)
    op.drop_column("rag_retrieval_traces", "query_redacted_at")
    op.drop_column("rag_retrieval_traces", "query_retention_until")
    op.drop_column("rag_retrieval_traces", "query_policy_version")
    op.drop_column("rag_retrieval_traces", "query_summary")
    op.drop_column("rag_retrieval_traces", "query_hash")
