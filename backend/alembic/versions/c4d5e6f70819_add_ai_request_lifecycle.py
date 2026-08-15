"""add AI request lifecycle and provider attempts

Revision ID: c4d5e6f70819
Revises: b3c4d5e6f708
Create Date: 2026-07-12 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c4d5e6f70819"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f708"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_ai_generation_traces_status",
        "ai_generation_traces",
        type_="check",
    )
    op.create_check_constraint(
        "ck_ai_generation_traces_status",
        "ai_generation_traces",
        "status IN ('started', 'succeeded', 'failed', 'blocked', 'skipped', 'abandoned')",
    )

    op.add_column(
        "ai_generation_traces",
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_ai_generation_traces_request_id",
        "ai_generation_traces",
        ["request_id"],
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column(
            "lifecycle_version",
            sa.String(length=50),
            server_default="request-lifecycle-v1",
            nullable=False,
        ),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE ai_generation_traces "
        "SET started_at = created_at, completed_at = created_at"
    )
    op.alter_column("ai_generation_traces", "started_at", nullable=False)
    op.create_index(
        "ix_ai_generation_traces_user_provider_created",
        "ai_generation_traces",
        ["user_id", "provider_invoked", "created_at"],
        unique=False,
    )

    op.create_table(
        "ai_generation_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("generation_trace_id", sa.Integer(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("attempt_kind", sa.String(length=30), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=50),
            server_default="google_gemini",
            nullable=False,
        ),
        sa.Column("model_used", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="started",
            nullable=False,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("finish_reason", sa.String(length=100), nullable=True),
        sa.Column("provider_response_id", sa.String(length=200), nullable=True),
        sa.Column("raw_response_hash", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_stage", sa.String(length=100), nullable=True),
        sa.Column(
            "attempt_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "attempt_kind IN ('initial', 'provider_retry', 'schema_repair')",
            name="ck_ai_generation_attempts_kind",
        ),
        sa.CheckConstraint(
            "status IN ('started', 'succeeded', 'failed', 'blocked', 'abandoned')",
            name="ck_ai_generation_attempts_status",
        ),
        sa.ForeignKeyConstraint(
            ["generation_trace_id"],
            ["ai_generation_traces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "generation_trace_id",
            "attempt_no",
            name="uq_ai_generation_attempt_trace_no",
        ),
    )
    op.create_index(
        "ix_ai_generation_attempts_trace",
        "ai_generation_attempts",
        ["generation_trace_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_generation_attempts_status_started",
        "ai_generation_attempts",
        ["status", "started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_generation_attempts_status_started",
        table_name="ai_generation_attempts",
    )
    op.drop_index(
        "ix_ai_generation_attempts_trace",
        table_name="ai_generation_attempts",
    )
    op.drop_table("ai_generation_attempts")

    op.drop_index(
        "ix_ai_generation_traces_user_provider_created",
        table_name="ai_generation_traces",
    )
    op.drop_column("ai_generation_traces", "deadline_at")
    op.drop_column("ai_generation_traces", "completed_at")
    op.drop_column("ai_generation_traces", "started_at")
    op.drop_column("ai_generation_traces", "lifecycle_version")
    op.drop_constraint(
        "uq_ai_generation_traces_request_id",
        "ai_generation_traces",
        type_="unique",
    )
    op.drop_column("ai_generation_traces", "request_id")

    op.drop_constraint(
        "ck_ai_generation_traces_status",
        "ai_generation_traces",
        type_="check",
    )
    op.create_check_constraint(
        "ck_ai_generation_traces_status",
        "ai_generation_traces",
        "status IN ('succeeded', 'failed', 'blocked', 'skipped')",
    )
