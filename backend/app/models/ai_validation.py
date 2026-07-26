from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AIValidationRun(Base):
    __tablename__ = "ai_validation_runs"
    __table_args__ = (
        Index("ix_ai_validation_runs_status_created", "status", "created_at"),
        CheckConstraint(
            "mode IN ('live_api', 'mock')",
            name="ck_ai_validation_runs_mode",
        ),
        CheckConstraint(
            "status IN ('started', 'succeeded', 'failed', 'partial', 'abandoned')",
            name="ck_ai_validation_runs_status",
        ),
        CheckConstraint(
            "cleanup_status IN ('pending', 'succeeded', 'failed', 'not_required')",
            name="ck_ai_validation_runs_cleanup_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default="live_api")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="started")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    validation_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_checks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    passed_checks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed_checks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    skipped_checks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cleanup_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    report_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    summary: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    items: Mapped[list[AIValidationItem]] = relationship(
        "AIValidationItem",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AIValidationItem.id",
    )


class AIValidationItem(Base):
    __tablename__ = "ai_validation_items"
    __table_args__ = (
        UniqueConstraint(
            "validation_run_id",
            "check_name",
            name="uq_ai_validation_items_run_check",
        ),
        Index("ix_ai_validation_items_run_status", "validation_run_id", "status"),
        CheckConstraint(
            "category IN ('setup', 'api', 'ai', 'trace', 'privacy', 'cleanup', 'ui')",
            name="ck_ai_validation_items_category",
        ),
        CheckConstraint(
            "status IN ('started', 'passed', 'failed', 'skipped')",
            name="ck_ai_validation_items_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    validation_run_id: Mapped[int] = mapped_column(
        ForeignKey("ai_validation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    check_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="started")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped[AIValidationRun] = relationship(
        "AIValidationRun",
        back_populates="items",
    )
