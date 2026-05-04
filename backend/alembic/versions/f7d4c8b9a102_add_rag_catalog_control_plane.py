"""add rag catalog control plane

Revision ID: f7d4c8b9a102
Revises: e6b1d2a3c4f5
Create Date: 2026-05-04 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f7d4c8b9a102"
down_revision: Union[str, Sequence[str], None] = "e6b1d2a3c4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_catalog_plan_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("catalog_file", sa.String(length=1000), nullable=False),
        sa.Column("catalog_version", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(length=30), server_default="live_fetch", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="running", nullable=False),
        sa.Column("report_path", sa.String(length=1000), nullable=True),
        sa.Column("total_sources", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("missing_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("matched_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("orphaned_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("metadata_changed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("content_changed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("quality_warning_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_create_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_skip_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_partial_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_full_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_manual_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("planned_defer_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_catalog_plan_runs")),
    )
    op.create_index("ix_rag_catalog_plan_runs_created_at", "rag_catalog_plan_runs", ["created_at"], unique=False)
    op.create_index("ix_rag_catalog_plan_runs_status", "rag_catalog_plan_runs", ["status"], unique=False)

    op.create_table(
        "rag_catalog_plan_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("catalog_key", sa.String(length=200), nullable=True),
        sa.Column("catalog_url", sa.String(length=1000), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("license", sa.String(length=200), nullable=True),
        sa.Column("source_grade", sa.String(length=5), nullable=True),
        sa.Column("catalog_status", sa.String(length=50), nullable=False),
        sa.Column("fetch_status", sa.String(length=50), nullable=True),
        sa.Column("parser_confidence", sa.Float(), nullable=True),
        sa.Column("old_content_hash", sa.String(length=64), nullable=True),
        sa.Column("new_content_hash", sa.String(length=64), nullable=True),
        sa.Column("etag_changed", sa.Boolean(), nullable=True),
        sa.Column("last_modified_changed", sa.Boolean(), nullable=True),
        sa.Column("metadata_changed_fields", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("sections_added", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sections_removed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sections_changed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sections_unchanged", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunks_added", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunks_removed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunks_changed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunks_unchanged", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("section_change_ratio", sa.Float(), nullable=True),
        sa.Column("chunk_change_ratio", sa.Float(), nullable=True),
        sa.Column("estimated_embedding_seconds", sa.Float(), nullable=True),
        sa.Column("quality_warnings", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("planned_action", sa.String(length=50), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("apply_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("applied_job_id", sa.Integer(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("apply_error_code", sa.String(length=100), nullable=True),
        sa.Column("apply_error_message", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["applied_job_id"], ["rag_ingest_jobs.id"], name=op.f("fk_rag_catalog_plan_items_applied_job_id_rag_ingest_jobs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["rag_catalog_plan_runs.id"], name=op.f("fk_rag_catalog_plan_items_run_id_rag_catalog_plan_runs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["rag_sources.id"], name=op.f("fk_rag_catalog_plan_items_source_id_rag_sources"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_catalog_plan_items")),
    )
    op.create_index("ix_rag_catalog_plan_items_action", "rag_catalog_plan_items", ["planned_action"], unique=False)
    op.create_index("ix_rag_catalog_plan_items_apply_status", "rag_catalog_plan_items", ["apply_status"], unique=False)
    op.create_index("ix_rag_catalog_plan_items_run_id", "rag_catalog_plan_items", ["run_id"], unique=False)
    op.create_index("ix_rag_catalog_plan_items_source_id", "rag_catalog_plan_items", ["source_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rag_catalog_plan_items_source_id", table_name="rag_catalog_plan_items")
    op.drop_index("ix_rag_catalog_plan_items_run_id", table_name="rag_catalog_plan_items")
    op.drop_index("ix_rag_catalog_plan_items_apply_status", table_name="rag_catalog_plan_items")
    op.drop_index("ix_rag_catalog_plan_items_action", table_name="rag_catalog_plan_items")
    op.drop_table("rag_catalog_plan_items")
    op.drop_index("ix_rag_catalog_plan_runs_status", table_name="rag_catalog_plan_runs")
    op.drop_index("ix_rag_catalog_plan_runs_created_at", table_name="rag_catalog_plan_runs")
    op.drop_table("rag_catalog_plan_runs")
