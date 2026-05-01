"""replace rag_documents with knowledge ops

Revision ID: d4f2b8c9a731
Revises: b7c2e91a4d3f
Create Date: 2026-05-01 20:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4f2b8c9a731"
down_revision: Union[str, Sequence[str], None] = "b7c2e91a4d3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_rag_documents_category", table_name="rag_documents")
    op.drop_table("rag_documents")

    op.create_table(
        "rag_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=50), server_default="internal_policy", nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("source_grade", sa.String(length=5), server_default="B", nullable=False),
        sa.Column("license", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("language", sa.String(length=10), server_default="ko", nullable=False),
        sa.Column("author_or_org", sa.String(length=300), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_sources")),
    )
    op.create_index("ix_rag_sources_category_status", "rag_sources", ["category", "status"], unique=False)
    op.create_index("ix_rag_sources_content_hash", "rag_sources", ["content_hash"], unique=False)

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=3072), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), server_default=sa.text("3072"), nullable=False),
        sa.Column("opensearch_index", sa.String(length=100), nullable=True),
        sa.Column("opensearch_document_id", sa.String(length=100), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("index_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["rag_sources.id"], name=op.f("fk_rag_chunks_source_id_rag_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_chunks")),
    )
    op.create_index("ix_rag_chunks_category_status", "rag_chunks", ["category", "status"], unique=False)
    op.create_index("ix_rag_chunks_content_hash", "rag_chunks", ["content_hash"], unique=False)
    op.create_index("ix_rag_chunks_index_status", "rag_chunks", ["index_status"], unique=False)
    op.create_index("ix_rag_chunks_source_index", "rag_chunks", ["source_id", "chunk_index"], unique=False)

    op.create_table(
        "rag_ingest_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("requested_by", sa.String(length=100), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("target_index", sa.String(length=100), nullable=True),
        sa.Column("chunks_total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunks_succeeded", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunks_failed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("indexed_total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("indexed_succeeded", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("indexed_failed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["rag_sources.id"], name=op.f("fk_rag_ingest_jobs_source_id_rag_sources"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_ingest_jobs")),
    )
    op.create_index("ix_rag_ingest_jobs_source_id", "rag_ingest_jobs", ["source_id"], unique=False)
    op.create_index("ix_rag_ingest_jobs_status", "rag_ingest_jobs", ["status"], unique=False)

    op.create_table(
        "rag_retrieval_traces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("request_type", sa.String(length=30), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=True),
        sa.Column("rag_trace_group_id", sa.String(length=36), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("category_filter", sa.String(length=100), nullable=True),
        sa.Column("search_backend", sa.String(length=30), nullable=False),
        sa.Column("search_mode", sa.String(length=30), nullable=False),
        sa.Column("index_name", sa.String(length=100), nullable=True),
        sa.Column("index_version", sa.String(length=50), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("keyword_score", sa.Float(), nullable=True),
        sa.Column("vector_score", sa.Float(), nullable=True),
        sa.Column("used_in_prompt", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["rag_chunks.id"], name=op.f("fk_rag_retrieval_traces_chunk_id_rag_chunks"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["rag_sources.id"], name=op.f("fk_rag_retrieval_traces_source_id_rag_sources"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_rag_retrieval_traces_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_retrieval_traces")),
    )
    op.create_index("ix_rag_retrieval_traces_chunk_id", "rag_retrieval_traces", ["chunk_id"], unique=False)
    op.create_index("ix_rag_retrieval_traces_group", "rag_retrieval_traces", ["rag_trace_group_id"], unique=False)
    op.create_index("ix_rag_retrieval_traces_user_request", "rag_retrieval_traces", ["user_id", "request_type"], unique=False)

    op.create_table(
        "ai_generation_traces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("recommendation_id", sa.Integer(), nullable=True),
        sa.Column("request_type", sa.String(length=30), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("rag_trace_group_id", sa.String(length=36), nullable=True),
        sa.Column("input_context_hash", sa.String(length=64), nullable=True),
        sa.Column("output_hash", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("finish_reason", sa.String(length=100), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["ai_recommendations.id"], name=op.f("fk_ai_generation_traces_recommendation_id_ai_recommendations"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_ai_generation_traces_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_generation_traces")),
    )
    op.create_index("ix_ai_generation_traces_rag_group", "ai_generation_traces", ["rag_trace_group_id"], unique=False)
    op.create_index("ix_ai_generation_traces_user_type", "ai_generation_traces", ["user_id", "request_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_generation_traces_user_type", table_name="ai_generation_traces")
    op.drop_index("ix_ai_generation_traces_rag_group", table_name="ai_generation_traces")
    op.drop_table("ai_generation_traces")

    op.drop_index("ix_rag_retrieval_traces_user_request", table_name="rag_retrieval_traces")
    op.drop_index("ix_rag_retrieval_traces_group", table_name="rag_retrieval_traces")
    op.drop_index("ix_rag_retrieval_traces_chunk_id", table_name="rag_retrieval_traces")
    op.drop_table("rag_retrieval_traces")

    op.drop_index("ix_rag_ingest_jobs_status", table_name="rag_ingest_jobs")
    op.drop_index("ix_rag_ingest_jobs_source_id", table_name="rag_ingest_jobs")
    op.drop_table("rag_ingest_jobs")

    op.drop_index("ix_rag_chunks_source_index", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_index_status", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_content_hash", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_category_status", table_name="rag_chunks")
    op.drop_table("rag_chunks")

    op.drop_index("ix_rag_sources_content_hash", table_name="rag_sources")
    op.drop_index("ix_rag_sources_category_status", table_name="rag_sources")
    op.drop_table("rag_sources")

    op.create_table(
        "rag_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=3072), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rag_documents")),
    )
    op.create_index("ix_rag_documents_category", "rag_documents", ["category"], unique=False)
