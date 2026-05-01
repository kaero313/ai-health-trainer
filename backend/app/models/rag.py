from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ai_recommendation import AIRecommendation
    from app.models.user import User


class RagSource(Base):
    __tablename__ = "rag_sources"
    __table_args__ = (
        Index("ix_rag_sources_category_status", "category", "status"),
        Index("ix_rag_sources_content_hash", "content_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="internal_policy")
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_grade: Mapped[str] = mapped_column(String(5), nullable=False, server_default="B")
    license: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="ko")
    author_or_org: Mapped[str | None] = mapped_column(String(300), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    chunks: Mapped[list[RagChunk]] = relationship(
        "RagChunk",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        Index("ix_rag_chunks_source_index", "source_id", "chunk_index"),
        Index("ix_rag_chunks_category_status", "category", "status"),
        Index("ix_rag_chunks_index_status", "index_status"),
        Index("ix_rag_chunks_content_hash", "content_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("rag_sources.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    embedding: Mapped[list[float]] = mapped_column(Vector(3072), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3072"))
    opensearch_index: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opensearch_document_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    index_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source: Mapped[RagSource] = relationship("RagSource", back_populates="chunks")


class RagIngestJob(Base):
    __tablename__ = "rag_ingest_jobs"
    __table_args__ = (
        Index("ix_rag_ingest_jobs_status", "status"),
        Index("ix_rag_ingest_jobs_source_id", "source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("rag_sources.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    requested_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_index: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chunks_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    chunks_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    chunks_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    indexed_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    indexed_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    indexed_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RagRetrievalTrace(Base):
    __tablename__ = "rag_retrieval_traces"
    __table_args__ = (
        Index("ix_rag_retrieval_traces_user_request", "user_id", "request_type"),
        Index("ix_rag_retrieval_traces_group", "rag_trace_group_id"),
        Index("ix_rag_retrieval_traces_chunk_id", "chunk_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_type: Mapped[str] = mapped_column(String(30), nullable=False)
    request_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rag_trace_group_id: Mapped[str] = mapped_column(String(36), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    category_filter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    search_backend: Mapped[str] = mapped_column(String(30), nullable=False)
    search_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    index_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    index_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("rag_chunks.id", ondelete="SET NULL"), nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("rag_sources.id", ondelete="SET NULL"), nullable=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    keyword_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    vector_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    used_in_prompt: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User | None] = relationship("User")
    chunk: Mapped[RagChunk | None] = relationship("RagChunk")
    source: Mapped[RagSource | None] = relationship("RagSource")


class AIGenerationTrace(Base):
    __tablename__ = "ai_generation_traces"
    __table_args__ = (
        Index("ix_ai_generation_traces_user_type", "user_id", "request_type"),
        Index("ix_ai_generation_traces_rag_group", "rag_trace_group_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recommendation_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_recommendations.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rag_trace_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    input_context_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User | None] = relationship("User")
    recommendation: Mapped[AIRecommendation | None] = relationship("AIRecommendation")
