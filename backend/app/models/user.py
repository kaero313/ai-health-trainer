from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ai_recommendation import AIRecommendation
    from app.models.diet import DietLog
    from app.models.exercise import ExerciseLog
    from app.models.token import RefreshToken
    from app.models.weight_log import WeightLog


class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class GoalEnum(str, enum.Enum):
    BULK = "bulk"
    DIET = "diet"
    MAINTAIN = "maintain"


class ActivityLevelEnum(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    profile: Mapped[UserProfile | None] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    exercise_logs: Mapped[list[ExerciseLog]] = relationship("ExerciseLog", back_populates="user")
    diet_logs: Mapped[list[DietLog]] = relationship("DietLog", back_populates="user")
    weight_logs: Mapped[list[WeightLog]] = relationship("WeightLog", back_populates="user")
    ai_recommendations: Mapped[list[AIRecommendation]] = relationship("AIRecommendation", back_populates="user")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship("RefreshToken", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[GenderEnum | None] = mapped_column(
        Enum(
            GenderEnum,
            name="gender_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    goal: Mapped[GoalEnum] = mapped_column(
        Enum(
            GoalEnum,
            name="goal_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    activity_level: Mapped[ActivityLevelEnum | None] = mapped_column(
        Enum(
            ActivityLevelEnum,
            name="activity_level_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    allergies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    food_preferences: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    tdee_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_protein_g: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    target_carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    target_fat_g: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship("User", back_populates="profile")

