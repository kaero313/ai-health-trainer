from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class MealTypeEnum(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class DietLog(Base):
    __tablename__ = "diet_logs"
    __table_args__ = (Index("ix_diet_logs_user_date", "user_id", "log_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[MealTypeEnum] = mapped_column(
        Enum(
            MealTypeEnum,
            name="meal_type_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_analyzed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="diet_logs")
    diet_log_items: Mapped[list[DietLogItem]] = relationship(
        "DietLogItem",
        back_populates="diet_log",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DietLogItem(Base):
    __tablename__ = "diet_log_items"
    __table_args__ = (Index("ix_diet_log_items_log_id", "diet_log_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diet_log_id: Mapped[int] = mapped_column(ForeignKey("diet_logs.id", ondelete="CASCADE"), nullable=False)
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)
    serving_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    calories: Mapped[Decimal] = mapped_column(Numeric(7, 1), nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False, server_default=text("0"))
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False, server_default=text("0"))
    fat_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False, server_default=text("0"))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    diet_log: Mapped[DietLog] = relationship("DietLog", back_populates="diet_log_items")

