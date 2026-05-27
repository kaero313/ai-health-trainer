"""add rag source replacement candidates

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c113
Create Date: 2026-05-27 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c113"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_source_replacement_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("catalog_key", sa.String(length=200), nullable=True),
        sa.Column("original_url", sa.String(length=1000), nullable=True),
        sa.Column("candidate_url", sa.String(length=1000), nullable=False),
        sa.Column("acquisition_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("parser_type", sa.String(length=50), nullable=True),
        sa.Column("parser_confidence", sa.Float(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("raw_content_hash", sa.String(length=64), nullable=True),
        sa.Column("content_type", sa.String(length=200), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("etag", sa.String(length=200), nullable=True),
        sa.Column("last_modified", sa.String(length=200), nullable=True),
        sa.Column("section_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("source_grade", sa.String(length=5), nullable=True),
        sa.Column("license", sa.String(length=200), nullable=True),
        sa.Column("author_or_org", sa.String(length=300), nullable=True),
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
        sa.Column("report_path", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('preview_succeeded', 'fetch_failed', 'parse_failed', 'manual_review_required')",
            name=op.f("ck_rag_source_replacement_candidates_status"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["rag_sources.id"],
            name=op.f("fk_rag_source_replacement_candidates_source_id_rag_sources"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_source_replacement_candidates")),
    )
    op.create_index(
        "ix_rag_source_replacement_candidates_catalog_key",
        "rag_source_replacement_candidates",
        ["catalog_key"],
        unique=False,
    )
    op.create_index(
        "ix_rag_source_replacement_candidates_created_at",
        "rag_source_replacement_candidates",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_source_replacement_candidates_source_id",
        "rag_source_replacement_candidates",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_source_replacement_candidates_status",
        "rag_source_replacement_candidates",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rag_source_replacement_candidates_status", table_name="rag_source_replacement_candidates")
    op.drop_index("ix_rag_source_replacement_candidates_source_id", table_name="rag_source_replacement_candidates")
    op.drop_index("ix_rag_source_replacement_candidates_created_at", table_name="rag_source_replacement_candidates")
    op.drop_index("ix_rag_source_replacement_candidates_catalog_key", table_name="rag_source_replacement_candidates")
    op.drop_table("rag_source_replacement_candidates")
