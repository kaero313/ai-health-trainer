from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
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
        Index("ix_rag_sources_refresh_due", "refresh_policy", "next_refresh_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="internal_policy")
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    origin_type: Mapped[str] = mapped_column(String(30), nullable=False, server_default="manual_text")
    origin_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    ingest_method: Mapped[str] = mapped_column(String(30), nullable=False, server_default="cli")
    parser_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="text")
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False, server_default="text-parser-v1")
    chunk_strategy: Mapped[str] = mapped_column(String(50), nullable=False, server_default="paragraph")
    chunker_version: Mapped[str] = mapped_column(String(50), nullable=False, server_default="structure-chunker-v1")
    normalization_version: Mapped[str] = mapped_column(String(50), nullable=False, server_default="chunk-normalize-v1")
    refresh_policy: Mapped[str] = mapped_column(String(30), nullable=False, server_default="manual")
    refresh_interval_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_etag: Mapped[str | None] = mapped_column(String(200), nullable=True)
    external_last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refresh_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
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
        Index("ix_rag_chunks_anchor_hash", "anchor_hash"),
        Index("ix_rag_chunks_embedding_input_hash", "embedding_input_hash"),
        Index("ix_rag_chunks_index_payload_hash", "index_payload_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("rag_sources.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    anchor_hash: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    embedding_input_hash: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    index_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
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
    source_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    chunk_strategy: Mapped[str] = mapped_column(String(50), nullable=False, server_default="paragraph")
    chunk_anchor: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
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
    pipeline_stage: Mapped[str] = mapped_column(String(50), nullable=False, server_default="created")
    parser_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_reuse_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    reembedding_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    index_skip_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    estimated_embedding_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skipped_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source: Mapped[RagSource | None] = relationship("RagSource")


class RagEmbeddingCache(Base):
    __tablename__ = "rag_embedding_cache"
    __table_args__ = (
        UniqueConstraint(
            "embedding_input_hash",
            "embedding_model",
            "embedding_dim",
            "normalization_version",
            name="uq_rag_embedding_cache_input",
        ),
        Index("ix_rag_embedding_cache_content_hash", "content_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    embedding_input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3072"))
    normalization_version: Mapped[str] = mapped_column(String(50), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(3072), nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RagPipelineDecision(Base):
    __tablename__ = "rag_pipeline_decisions"
    __table_args__ = (
        Index("ix_rag_pipeline_decisions_job_id", "job_id"),
        Index("ix_rag_pipeline_decisions_source_id", "source_id"),
        Index("ix_rag_pipeline_decisions_type", "decision_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("rag_ingest_jobs.id", ondelete="SET NULL"), nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("rag_sources.id", ondelete="SET NULL"), nullable=True)
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    selected_action: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    context: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    tradeoffs: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    job: Mapped[RagIngestJob | None] = relationship("RagIngestJob")
    source: Mapped[RagSource | None] = relationship("RagSource")


class RagCatalogPlanRun(Base):
    __tablename__ = "rag_catalog_plan_runs"
    __table_args__ = (
        Index("ix_rag_catalog_plan_runs_status", "status"),
        Index("ix_rag_catalog_plan_runs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_file: Mapped[str] = mapped_column(String(1000), nullable=False)
    catalog_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mode: Mapped[str] = mapped_column(String(30), nullable=False, server_default="live_fetch")
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="running")
    report_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    total_sources: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    orphaned_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    metadata_changed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    content_changed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    quality_warning_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_create_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_skip_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_partial_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_full_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_manual_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_defer_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    summary: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    items: Mapped[list[RagCatalogPlanItem]] = relationship(
        "RagCatalogPlanItem",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class RagCatalogPlanItem(Base):
    __tablename__ = "rag_catalog_plan_items"
    __table_args__ = (
        Index("ix_rag_catalog_plan_items_run_id", "run_id"),
        Index("ix_rag_catalog_plan_items_source_id", "source_id"),
        Index("ix_rag_catalog_plan_items_acquisition", "acquisition_type"),
        Index("ix_rag_catalog_plan_items_action", "planned_action"),
        Index("ix_rag_catalog_plan_items_apply_status", "apply_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("rag_catalog_plan_runs.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("rag_sources.id", ondelete="SET NULL"), nullable=True)
    catalog_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    catalog_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    acquisition_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    origin_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    parser_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    license: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_grade: Mapped[str | None] = mapped_column(String(5), nullable=True)
    catalog_status: Mapped[str] = mapped_column(String(50), nullable=False)
    fetch_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parser_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    old_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    etag_changed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_modified_changed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    metadata_changed_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    sections_added: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    sections_removed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    sections_changed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    sections_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    chunks_added: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    chunks_removed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    chunks_changed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    chunks_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    section_change_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    chunk_change_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_embedding_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    planned_action: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    apply_status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    applied_job_id: Mapped[int | None] = mapped_column(ForeignKey("rag_ingest_jobs.id", ondelete="SET NULL"), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    apply_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    apply_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run: Mapped[RagCatalogPlanRun] = relationship("RagCatalogPlanRun", back_populates="items")
    source: Mapped[RagSource | None] = relationship("RagSource")
    applied_job: Mapped[RagIngestJob | None] = relationship("RagIngestJob")


class RagSchedulerRun(Base):
    __tablename__ = "rag_scheduler_runs"
    __table_args__ = (
        Index("ix_rag_scheduler_runs_status", "status"),
        Index("ix_rag_scheduler_runs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="running")
    mode: Mapped[str] = mapped_column(String(30), nullable=False, server_default="plan_only")
    target_catalogs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    force_plan: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    report_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    catalog_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    due_catalog_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    plan_run_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    approval_required_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    no_change_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    summary: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    items: Mapped[list[RagSchedulerRunItem]] = relationship(
        "RagSchedulerRunItem",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class RagSchedulerRunItem(Base):
    __tablename__ = "rag_scheduler_run_items"
    __table_args__ = (
        Index("ix_rag_scheduler_run_items_run_id", "run_id"),
        Index("ix_rag_scheduler_run_items_plan_run_id", "plan_run_id"),
        Index("ix_rag_scheduler_run_items_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("rag_scheduler_runs.id", ondelete="CASCADE"), nullable=False)
    catalog_file: Mapped[str] = mapped_column(String(1000), nullable=False)
    catalog_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    due_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plan_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("rag_catalog_plan_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    total_sources: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    due_source_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_create_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_skip_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_partial_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_full_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_manual_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    planned_defer_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run: Mapped[RagSchedulerRun] = relationship("RagSchedulerRun", back_populates="items")
    plan_run: Mapped[RagCatalogPlanRun | None] = relationship("RagCatalogPlanRun")


class RagReviewRun(Base):
    __tablename__ = "rag_review_runs"
    __table_args__ = (
        Index("ix_rag_review_runs_type", "review_type"),
        Index("ix_rag_review_runs_status", "status"),
        Index("ix_rag_review_runs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_run_id: Mapped[int] = mapped_column(Integer, nullable=False)
    catalog_plan_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("rag_catalog_plan_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduler_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("rag_scheduler_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="completed")
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    recommended_action: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    report_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    summary: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    catalog_plan_run: Mapped[RagCatalogPlanRun | None] = relationship("RagCatalogPlanRun")
    scheduler_run: Mapped[RagSchedulerRun | None] = relationship("RagSchedulerRun")
    items: Mapped[list[RagReviewItem]] = relationship(
        "RagReviewItem",
        back_populates="review_run",
        cascade="all, delete-orphan",
    )


class RagReviewItem(Base):
    __tablename__ = "rag_review_items"
    __table_args__ = (
        Index("ix_rag_review_items_review_run_id", "review_run_id"),
        Index("ix_rag_review_items_catalog_plan_run_id", "catalog_plan_run_id"),
        Index("ix_rag_review_items_decision", "review_decision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_run_id: Mapped[int] = mapped_column(ForeignKey("rag_review_runs.id", ondelete="CASCADE"), nullable=False)
    catalog_plan_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("rag_catalog_plan_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    catalog_plan_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("rag_catalog_plan_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_id: Mapped[int | None] = mapped_column(ForeignKey("rag_sources.id", ondelete="SET NULL"), nullable=True)
    catalog_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    acquisition_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_grade: Mapped[str | None] = mapped_column(String(5), nullable=True)
    planned_action: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    review_decision: Mapped[str] = mapped_column(String(100), nullable=False)
    operator_recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    blocking_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parser_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    section_change_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    chunk_change_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_embedding_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    context: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    review_run: Mapped[RagReviewRun] = relationship("RagReviewRun", back_populates="items")
    catalog_plan_run: Mapped[RagCatalogPlanRun | None] = relationship("RagCatalogPlanRun")
    catalog_plan_item: Mapped[RagCatalogPlanItem | None] = relationship("RagCatalogPlanItem")
    source: Mapped[RagSource | None] = relationship("RagSource")


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
