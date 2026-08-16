"""add AI quota reservation audit fields

Revision ID: d5e6f708192a
Revises: c4d5e6f70819
Create Date: 2026-07-12 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e6f708192a"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f70819"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_generation_traces",
        sa.Column(
            "quota_policy_version",
            sa.String(length=50),
            server_default="daily-logical-request-v1",
            nullable=False,
        ),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column(
            "quota_status",
            sa.String(length=20),
            server_default="not_checked",
            nullable=False,
        ),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("quota_bucket", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("quota_timezone", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("quota_limit", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("quota_position", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("quota_reserved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ai_generation_traces",
        sa.Column("quota_finalized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_ai_generation_traces_quota_status",
        "ai_generation_traces",
        "quota_status IN ('not_checked', 'reserved', 'consumed', 'released', 'rejected', 'error')",
    )
    op.create_index(
        "ix_ai_generation_traces_user_quota_bucket",
        "ai_generation_traces",
        ["user_id", "quota_bucket", "quota_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_generation_traces_user_quota_bucket",
        table_name="ai_generation_traces",
    )
    op.drop_constraint(
        "ck_ai_generation_traces_quota_status",
        "ai_generation_traces",
        type_="check",
    )
    op.drop_column("ai_generation_traces", "quota_finalized_at")
    op.drop_column("ai_generation_traces", "quota_reserved_at")
    op.drop_column("ai_generation_traces", "quota_position")
    op.drop_column("ai_generation_traces", "quota_limit")
    op.drop_column("ai_generation_traces", "quota_timezone")
    op.drop_column("ai_generation_traces", "quota_bucket")
    op.drop_column("ai_generation_traces", "quota_status")
    op.drop_column("ai_generation_traces", "quota_policy_version")
