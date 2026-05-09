"""add rag scheduler runs

Revision ID: c9d8e7f6a501
Revises: a8c4d2e6f901
Create Date: 2026-05-09 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a501"
down_revision: Union[str, Sequence[str], None] = "a8c4d2e6f901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_scheduler_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="running", nullable=False),
        sa.Column("mode", sa.String(length=30), server_default="plan_only", nullable=False),
        sa.Column("target_catalogs", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("force_plan", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("report_path", sa.String(length=1000), nullable=True),
        sa.Column("catalog_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("due_catalog_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("plan_run_ids", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("approval_required_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("no_change_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_scheduler_runs")),
    )
    op.create_index("ix_rag_scheduler_runs_created_at", "rag_scheduler_runs", ["created_at"], unique=False)
    op.create_index("ix_rag_scheduler_runs_status", "rag_scheduler_runs", ["status"], unique=False)

    op.create_table(
        "rag_scheduler_run_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("catalog_file", sa.String(length=1000), nullable=False),
        sa.Column("catalog_version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("due_status", sa.String(length=50), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=True),
        sa.Column("plan_run_id", sa.Integer(), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("total_sources", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("due_source_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_create_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_skip_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_partial_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_full_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_manual_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_defer_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["plan_run_id"], ["rag_catalog_plan_runs.id"], name=op.f("fk_rag_scheduler_run_items_plan_run_id_rag_catalog_plan_runs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["rag_scheduler_runs.id"], name=op.f("fk_rag_scheduler_run_items_run_id_rag_scheduler_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_scheduler_run_items")),
    )
    op.create_index("ix_rag_scheduler_run_items_plan_run_id", "rag_scheduler_run_items", ["plan_run_id"], unique=False)
    op.create_index("ix_rag_scheduler_run_items_run_id", "rag_scheduler_run_items", ["run_id"], unique=False)
    op.create_index("ix_rag_scheduler_run_items_status", "rag_scheduler_run_items", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rag_scheduler_run_items_status", table_name="rag_scheduler_run_items")
    op.drop_index("ix_rag_scheduler_run_items_run_id", table_name="rag_scheduler_run_items")
    op.drop_index("ix_rag_scheduler_run_items_plan_run_id", table_name="rag_scheduler_run_items")
    op.drop_table("rag_scheduler_run_items")
    op.drop_index("ix_rag_scheduler_runs_status", table_name="rag_scheduler_runs")
    op.drop_index("ix_rag_scheduler_runs_created_at", table_name="rag_scheduler_runs")
    op.drop_table("rag_scheduler_runs")
