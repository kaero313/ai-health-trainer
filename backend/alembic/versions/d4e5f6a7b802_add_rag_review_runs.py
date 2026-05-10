"""add rag review runs

Revision ID: d4e5f6a7b802
Revises: c9d8e7f6a501
Create Date: 2026-05-10 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b802"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a501"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_review_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_type", sa.String(length=50), nullable=False),
        sa.Column("target_run_id", sa.Integer(), nullable=False),
        sa.Column("catalog_plan_run_id", sa.Integer(), nullable=True),
        sa.Column("scheduler_run_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="completed", nullable=False),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("recommended_action", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("report_path", sa.String(length=1000), nullable=True),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalog_plan_run_id"],
            ["rag_catalog_plan_runs.id"],
            name=op.f("fk_rag_review_runs_catalog_plan_run_id_rag_catalog_plan_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scheduler_run_id"],
            ["rag_scheduler_runs.id"],
            name=op.f("fk_rag_review_runs_scheduler_run_id_rag_scheduler_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_review_runs")),
    )
    op.create_index("ix_rag_review_runs_created_at", "rag_review_runs", ["created_at"], unique=False)
    op.create_index("ix_rag_review_runs_status", "rag_review_runs", ["status"], unique=False)
    op.create_index("ix_rag_review_runs_type", "rag_review_runs", ["review_type"], unique=False)

    op.create_table(
        "rag_review_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_run_id", sa.Integer(), nullable=False),
        sa.Column("catalog_plan_run_id", sa.Integer(), nullable=True),
        sa.Column("catalog_plan_item_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("catalog_key", sa.String(length=200), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("acquisition_type", sa.String(length=50), nullable=True),
        sa.Column("source_grade", sa.String(length=5), nullable=True),
        sa.Column("planned_action", sa.String(length=50), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("review_decision", sa.String(length=100), nullable=False),
        sa.Column("operator_recommendation", sa.Text(), nullable=False),
        sa.Column("blocking_reason", sa.String(length=100), nullable=True),
        sa.Column("parser_confidence", sa.Float(), nullable=True),
        sa.Column("section_change_ratio", sa.Float(), nullable=True),
        sa.Column("chunk_change_ratio", sa.Float(), nullable=True),
        sa.Column("estimated_embedding_seconds", sa.Float(), nullable=True),
        sa.Column(
            "quality_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalog_plan_item_id"],
            ["rag_catalog_plan_items.id"],
            name=op.f("fk_rag_review_items_catalog_plan_item_id_rag_catalog_plan_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_plan_run_id"],
            ["rag_catalog_plan_runs.id"],
            name=op.f("fk_rag_review_items_catalog_plan_run_id_rag_catalog_plan_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["review_run_id"],
            ["rag_review_runs.id"],
            name=op.f("fk_rag_review_items_review_run_id_rag_review_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["rag_sources.id"],
            name=op.f("fk_rag_review_items_source_id_rag_sources"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_review_items")),
    )
    op.create_index("ix_rag_review_items_catalog_plan_run_id", "rag_review_items", ["catalog_plan_run_id"], unique=False)
    op.create_index("ix_rag_review_items_decision", "rag_review_items", ["review_decision"], unique=False)
    op.create_index("ix_rag_review_items_review_run_id", "rag_review_items", ["review_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rag_review_items_review_run_id", table_name="rag_review_items")
    op.drop_index("ix_rag_review_items_decision", table_name="rag_review_items")
    op.drop_index("ix_rag_review_items_catalog_plan_run_id", table_name="rag_review_items")
    op.drop_table("rag_review_items")
    op.drop_index("ix_rag_review_runs_type", table_name="rag_review_runs")
    op.drop_index("ix_rag_review_runs_status", table_name="rag_review_runs")
    op.drop_index("ix_rag_review_runs_created_at", table_name="rag_review_runs")
    op.drop_table("rag_review_runs")
