"""add rag decision policy layer

Revision ID: e6b1d2a3c4f5
Revises: d4f2b8c9a731
Create Date: 2026-05-02 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e6b1d2a3c4f5"
down_revision: Union[str, Sequence[str], None] = "d4f2b8c9a731"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rag_sources", sa.Column("origin_type", sa.String(length=30), server_default="manual_text", nullable=False))
    op.add_column("rag_sources", sa.Column("origin_uri", sa.String(length=1000), nullable=True))
    op.add_column("rag_sources", sa.Column("ingest_method", sa.String(length=30), server_default="cli", nullable=False))
    op.add_column("rag_sources", sa.Column("parser_type", sa.String(length=50), server_default="text", nullable=False))
    op.add_column("rag_sources", sa.Column("parser_version", sa.String(length=50), server_default="text-parser-v1", nullable=False))
    op.add_column("rag_sources", sa.Column("chunk_strategy", sa.String(length=50), server_default="paragraph", nullable=False))
    op.add_column("rag_sources", sa.Column("chunker_version", sa.String(length=50), server_default="structure-chunker-v1", nullable=False))
    op.add_column("rag_sources", sa.Column("normalization_version", sa.String(length=50), server_default="chunk-normalize-v1", nullable=False))
    op.add_column("rag_sources", sa.Column("refresh_policy", sa.String(length=30), server_default="manual", nullable=False))
    op.add_column("rag_sources", sa.Column("refresh_interval_hours", sa.Integer(), nullable=True))
    op.add_column("rag_sources", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rag_sources", sa.Column("next_refresh_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rag_sources", sa.Column("external_etag", sa.String(length=200), nullable=True))
    op.add_column("rag_sources", sa.Column("external_last_modified", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rag_sources", sa.Column("last_refresh_status", sa.String(length=30), nullable=True))
    op.create_index("ix_rag_sources_refresh_due", "rag_sources", ["refresh_policy", "next_refresh_at"], unique=False)

    op.add_column("rag_chunks", sa.Column("anchor_hash", sa.String(length=64), server_default="", nullable=False))
    op.add_column("rag_chunks", sa.Column("embedding_input_hash", sa.String(length=64), server_default="", nullable=False))
    op.add_column("rag_chunks", sa.Column("index_payload_hash", sa.String(length=64), server_default="", nullable=False))
    op.add_column("rag_chunks", sa.Column("source_version", sa.Integer(), server_default=sa.text("1"), nullable=False))
    op.add_column("rag_chunks", sa.Column("chunk_strategy", sa.String(length=50), server_default="paragraph", nullable=False))
    op.add_column("rag_chunks", sa.Column("chunk_anchor", sa.String(length=1000), nullable=True))
    op.add_column("rag_chunks", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column(
        "rag_chunks",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index("ix_rag_chunks_anchor_hash", "rag_chunks", ["anchor_hash"], unique=False)
    op.create_index("ix_rag_chunks_embedding_input_hash", "rag_chunks", ["embedding_input_hash"], unique=False)
    op.create_index("ix_rag_chunks_index_payload_hash", "rag_chunks", ["index_payload_hash"], unique=False)

    op.add_column("rag_ingest_jobs", sa.Column("pipeline_stage", sa.String(length=50), server_default="created", nullable=False))
    op.add_column("rag_ingest_jobs", sa.Column("parser_confidence", sa.Float(), nullable=True))
    op.add_column("rag_ingest_jobs", sa.Column("change_ratio", sa.Float(), nullable=True))
    op.add_column("rag_ingest_jobs", sa.Column("embedding_reuse_count", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("rag_ingest_jobs", sa.Column("reembedding_count", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("rag_ingest_jobs", sa.Column("index_skip_count", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("rag_ingest_jobs", sa.Column("estimated_embedding_seconds", sa.Float(), nullable=True))
    op.add_column("rag_ingest_jobs", sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.add_column("rag_ingest_jobs", sa.Column("skipped_reason", sa.String(length=100), nullable=True))

    op.create_table(
        "rag_embedding_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("embedding_input_hash", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), server_default=sa.text("3072"), nullable=False),
        sa.Column("normalization_version", sa.String(length=50), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=3072), nullable=False),
        sa.Column("usage_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_embedding_cache")),
        sa.UniqueConstraint(
            "embedding_input_hash",
            "embedding_model",
            "embedding_dim",
            "normalization_version",
            name="uq_rag_embedding_cache_input",
        ),
    )
    op.create_index("ix_rag_embedding_cache_content_hash", "rag_embedding_cache", ["content_hash"], unique=False)

    op.create_table(
        "rag_pipeline_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("decision_type", sa.String(length=50), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=False),
        sa.Column("selected_action", sa.String(length=50), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("tradeoffs", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["rag_ingest_jobs.id"], name=op.f("fk_rag_pipeline_decisions_job_id_rag_ingest_jobs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["rag_sources.id"], name=op.f("fk_rag_pipeline_decisions_source_id_rag_sources"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_pipeline_decisions")),
    )
    op.create_index("ix_rag_pipeline_decisions_job_id", "rag_pipeline_decisions", ["job_id"], unique=False)
    op.create_index("ix_rag_pipeline_decisions_source_id", "rag_pipeline_decisions", ["source_id"], unique=False)
    op.create_index("ix_rag_pipeline_decisions_type", "rag_pipeline_decisions", ["decision_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rag_pipeline_decisions_type", table_name="rag_pipeline_decisions")
    op.drop_index("ix_rag_pipeline_decisions_source_id", table_name="rag_pipeline_decisions")
    op.drop_index("ix_rag_pipeline_decisions_job_id", table_name="rag_pipeline_decisions")
    op.drop_table("rag_pipeline_decisions")

    op.drop_index("ix_rag_embedding_cache_content_hash", table_name="rag_embedding_cache")
    op.drop_table("rag_embedding_cache")

    op.drop_column("rag_ingest_jobs", "skipped_reason")
    op.drop_column("rag_ingest_jobs", "latency_ms")
    op.drop_column("rag_ingest_jobs", "estimated_embedding_seconds")
    op.drop_column("rag_ingest_jobs", "index_skip_count")
    op.drop_column("rag_ingest_jobs", "reembedding_count")
    op.drop_column("rag_ingest_jobs", "embedding_reuse_count")
    op.drop_column("rag_ingest_jobs", "change_ratio")
    op.drop_column("rag_ingest_jobs", "parser_confidence")
    op.drop_column("rag_ingest_jobs", "pipeline_stage")

    op.drop_index("ix_rag_chunks_index_payload_hash", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_embedding_input_hash", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_anchor_hash", table_name="rag_chunks")
    op.drop_column("rag_chunks", "metadata")
    op.drop_column("rag_chunks", "page_number")
    op.drop_column("rag_chunks", "chunk_anchor")
    op.drop_column("rag_chunks", "chunk_strategy")
    op.drop_column("rag_chunks", "source_version")
    op.drop_column("rag_chunks", "index_payload_hash")
    op.drop_column("rag_chunks", "embedding_input_hash")
    op.drop_column("rag_chunks", "anchor_hash")

    op.drop_index("ix_rag_sources_refresh_due", table_name="rag_sources")
    op.drop_column("rag_sources", "last_refresh_status")
    op.drop_column("rag_sources", "external_last_modified")
    op.drop_column("rag_sources", "external_etag")
    op.drop_column("rag_sources", "next_refresh_at")
    op.drop_column("rag_sources", "last_checked_at")
    op.drop_column("rag_sources", "refresh_interval_hours")
    op.drop_column("rag_sources", "refresh_policy")
    op.drop_column("rag_sources", "normalization_version")
    op.drop_column("rag_sources", "chunker_version")
    op.drop_column("rag_sources", "chunk_strategy")
    op.drop_column("rag_sources", "parser_version")
    op.drop_column("rag_sources", "parser_type")
    op.drop_column("rag_sources", "ingest_method")
    op.drop_column("rag_sources", "origin_uri")
    op.drop_column("rag_sources", "origin_type")
