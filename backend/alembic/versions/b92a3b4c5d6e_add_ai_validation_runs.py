"""add AI integration validation runs

Revision ID: b92a3b4c5d6e
Revises: a8192a3b4c5d
Create Date: 2026-07-12 17:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b92a3b4c5d6e"
down_revision: Union[str, Sequence[str], None] = "a8192a3b4c5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_validation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(length=20), server_default="live_api", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="started", nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("validation_user_id", sa.Integer(), nullable=True),
        sa.Column("expected_checks", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("passed_checks", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_checks", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("skipped_checks", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cleanup_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("report_path", sa.String(length=1000), nullable=True),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("mode IN ('live_api', 'mock')", name="ck_ai_validation_runs_mode"),
        sa.CheckConstraint(
            "status IN ('started', 'succeeded', 'failed', 'partial', 'abandoned')",
            name="ck_ai_validation_runs_status",
        ),
        sa.CheckConstraint(
            "cleanup_status IN ('pending', 'succeeded', 'failed', 'not_required')",
            name="ck_ai_validation_runs_cleanup_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_ai_validation_runs_run_id"),
    )
    op.create_index(
        "ix_ai_validation_runs_status_created",
        "ai_validation_runs",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "ai_validation_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("validation_run_id", sa.Integer(), nullable=False),
        sa.Column("check_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="started", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "category IN ('setup', 'api', 'ai', 'trace', 'privacy', 'cleanup', 'ui')",
            name="ck_ai_validation_items_category",
        ),
        sa.CheckConstraint(
            "status IN ('started', 'passed', 'failed', 'skipped')",
            name="ck_ai_validation_items_status",
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["ai_validation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "validation_run_id",
            "check_name",
            name="uq_ai_validation_items_run_check",
        ),
    )
    op.create_index(
        "ix_ai_validation_items_run_status",
        "ai_validation_items",
        ["validation_run_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_validation_items_run_status", table_name="ai_validation_items")
    op.drop_table("ai_validation_items")
    op.drop_index("ix_ai_validation_runs_status_created", table_name="ai_validation_runs")
    op.drop_table("ai_validation_runs")
