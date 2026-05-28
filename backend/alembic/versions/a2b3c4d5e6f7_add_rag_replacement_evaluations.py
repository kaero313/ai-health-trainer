"""add rag replacement evaluations

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-05-28 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_source_replacement_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("catalog_key", sa.String(length=200), nullable=True),
        sa.Column("candidate_url", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("readiness_score", sa.Float(), nullable=False),
        sa.Column("coverage_score", sa.Float(), nullable=False),
        sa.Column("metadata_score", sa.Float(), nullable=False),
        sa.Column("parser_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("recommendation", sa.String(length=100), nullable=False),
        sa.Column(
            "blocking_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "quality_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "required_terms",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "matched_terms",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "missing_terms",
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
        sa.Column("report_path", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('ready_for_activation', 'needs_manual_review', 'rejected')",
            name=op.f("ck_rag_source_replacement_evaluations_status"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["rag_source_replacement_candidates.id"],
            name=op.f("fk_rag_source_replacement_evaluations_candidate_id_rag_source_replacement_candidates"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["rag_sources.id"],
            name=op.f("fk_rag_source_replacement_evaluations_source_id_rag_sources"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_source_replacement_evaluations")),
    )
    op.create_index(
        "ix_rag_source_replacement_evaluations_candidate_id",
        "rag_source_replacement_evaluations",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_source_replacement_evaluations_catalog_key",
        "rag_source_replacement_evaluations",
        ["catalog_key"],
        unique=False,
    )
    op.create_index(
        "ix_rag_source_replacement_evaluations_created_at",
        "rag_source_replacement_evaluations",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_source_replacement_evaluations_source_id",
        "rag_source_replacement_evaluations",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_source_replacement_evaluations_status",
        "rag_source_replacement_evaluations",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rag_source_replacement_evaluations_status", table_name="rag_source_replacement_evaluations")
    op.drop_index("ix_rag_source_replacement_evaluations_source_id", table_name="rag_source_replacement_evaluations")
    op.drop_index("ix_rag_source_replacement_evaluations_created_at", table_name="rag_source_replacement_evaluations")
    op.drop_index("ix_rag_source_replacement_evaluations_catalog_key", table_name="rag_source_replacement_evaluations")
    op.drop_index("ix_rag_source_replacement_evaluations_candidate_id", table_name="rag_source_replacement_evaluations")
    op.drop_table("rag_source_replacement_evaluations")
