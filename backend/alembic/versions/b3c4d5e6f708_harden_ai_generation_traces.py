"""harden ai generation and retrieval traces

Revision ID: b3c4d5e6f708
Revises: a2b3c4d5e6f7
Create Date: 2026-07-11 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b3c4d5e6f708"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rag_retrieval_traces",
        sa.Column("used_in_response", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    op.add_column(
        "ai_generation_traces",
        sa.Column("status", sa.String(length=20), server_default="succeeded", nullable=False),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("provider_invoked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("response_schema_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("provider_response_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("raw_response_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("error_stage", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column(
            "trace_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_ai_generation_traces_status",
        "ai_generation_traces",
        "status IN ('succeeded', 'failed', 'blocked', 'skipped')",
    )

    # Existing rows were only written after a successful provider response.
    op.execute("UPDATE ai_generation_traces SET provider_invoked = true")


def downgrade() -> None:
    op.drop_constraint("ck_ai_generation_traces_status", "ai_generation_traces", type_="check")
    op.drop_column("ai_generation_traces", "trace_metadata")
    op.drop_column("ai_generation_traces", "error_stage")
    op.drop_column("ai_generation_traces", "raw_response_hash")
    op.drop_column("ai_generation_traces", "retry_count")
    op.drop_column("ai_generation_traces", "provider_response_id")
    op.drop_column("ai_generation_traces", "response_schema_version")
    op.drop_column("ai_generation_traces", "provider_invoked")
    op.drop_column("ai_generation_traces", "status")
    op.drop_column("rag_retrieval_traces", "used_in_response")
