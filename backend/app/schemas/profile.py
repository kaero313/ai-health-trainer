from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.user import ActivityLevelEnum, GenderEnum, GoalEnum


class ProfileUpsertRequest(BaseModel):
    height_cm: float = Field(..., ge=100.0, le=250.0)
    weight_kg: float = Field(..., ge=30.0, le=300.0)
    age: int = Field(..., ge=10, le=100)
    gender: GenderEnum
    goal: GoalEnum
    activity_level: ActivityLevelEnum
    allergies: list[str] = Field(default_factory=list)
    food_preferences: list[str] = Field(default_factory=list)

    @field_validator("allergies", "food_preferences")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class ProfileResponseData(BaseModel):
    user_id: int
    height_cm: float | None
    weight_kg: float | None
    age: int | None
    gender: GenderEnum | None
    goal: GoalEnum
    activity_level: ActivityLevelEnum | None
    allergies: list[str]
    food_preferences: list[str]
    tdee_kcal: int | None
    target_calories: int | None
    target_protein_g: float | None
    target_carbs_g: float | None
    target_fat_g: float | None


class ProfileResponse(BaseModel):
    status: Literal["success"] = "success"
    data: ProfileResponseData
    message: str | None = None
