"""add rag apply approval gate

Revision ID: e7f8a9b0c113
Revises: d4e5f6a7b802
Create Date: 2026-05-19 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c113"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b802"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rag_catalog_plan_runs", sa.Column("approved_review_run_id", sa.Integer(), nullable=True))
    op.add_column("rag_catalog_plan_runs", sa.Column("approval_status", sa.String(length=50), nullable=True))
    op.add_column("rag_catalog_plan_runs", sa.Column("approval_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rag_catalog_plan_runs", sa.Column("approval_error_code", sa.String(length=100), nullable=True))
    op.add_column("rag_catalog_plan_runs", sa.Column("approval_error_message", sa.Text(), nullable=True))
    op.create_foreign_key(
        op.f("fk_rag_catalog_plan_runs_approved_review_run_id_rag_review_runs"),
        "rag_catalog_plan_runs",
        "rag_review_runs",
        ["approved_review_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_rag_catalog_plan_runs_approved_review",
        "rag_catalog_plan_runs",
        ["approved_review_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_catalog_plan_runs_approval_status",
        "rag_catalog_plan_runs",
        ["approval_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rag_catalog_plan_runs_approval_status", table_name="rag_catalog_plan_runs")
    op.drop_index("ix_rag_catalog_plan_runs_approved_review", table_name="rag_catalog_plan_runs")
    op.drop_constraint(
        op.f("fk_rag_catalog_plan_runs_approved_review_run_id_rag_review_runs"),
        "rag_catalog_plan_runs",
        type_="foreignkey",
    )
    op.drop_column("rag_catalog_plan_runs", "approval_error_message")
    op.drop_column("rag_catalog_plan_runs", "approval_error_code")
    op.drop_column("rag_catalog_plan_runs", "approval_checked_at")
    op.drop_column("rag_catalog_plan_runs", "approval_status")
    op.drop_column("rag_catalog_plan_runs", "approved_review_run_id")
