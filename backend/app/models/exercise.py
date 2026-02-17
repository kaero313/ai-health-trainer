from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class MuscleGroupEnum(str, enum.Enum):
    CHEST = "chest"
    BACK = "back"
    SHOULDER = "shoulder"
    LEGS = "legs"
    ARMS = "arms"
    CORE = "core"
    CARDIO = "cardio"
    FULL_BODY = "full_body"


class ExerciseLog(Base):
    __tablename__ = "exercise_logs"
    __table_args__ = (
        Index("ix_exercise_logs_user_date", "user_id", "exercise_date"),
        Index("ix_exercise_logs_user_muscle", "user_id", "muscle_group"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    exercise_date: Mapped[date] = mapped_column(Date, nullable=False)
    exercise_name: Mapped[str] = mapped_column(String(100), nullable=False)
    muscle_group: Mapped[MuscleGroupEnum] = mapped_column(
        Enum(
            MuscleGroupEnum,
            name="muscle_group_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="exercise_logs")
    exercise_sets: Mapped[list[ExerciseSet]] = relationship(
        "ExerciseSet",
        back_populates="exercise_log",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExerciseSet.set_number",
    )


class ExerciseSet(Base):
    __tablename__ = "exercise_sets"
    __table_args__ = (Index("ix_exercise_sets_log_id", "exercise_log_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_log_id: Mapped[int] = mapped_column(
        ForeignKey("exercise_logs.id", ondelete="CASCADE"),
        nullable=False,
    )
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    exercise_log: Mapped[ExerciseLog] = relationship("ExerciseLog", back_populates="exercise_sets")

