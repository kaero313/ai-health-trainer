from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.diet import MealTypeEnum


class DietLogItemCreate(BaseModel):
    food_catalog_item_id: int | None = Field(None, ge=1)
    food_name: str = Field(..., min_length=1, max_length=200)
    serving_size: str | None = Field(None, max_length=50)
    serving_grams: float | None = Field(None, ge=0)
    calories: float = Field(..., ge=0)
    protein_g: float = Field(0, ge=0)
    carbs_g: float = Field(0, ge=0)
    fat_g: float = Field(0, ge=0)
    sugar_g: float | None = Field(None, ge=0)
    saturated_fat_g: float | None = Field(None, ge=0)
    unsaturated_fat_g: float | None = Field(None, ge=0)
    confidence: float | None = Field(None, ge=0, le=1)


class DietLogCreate(BaseModel):
    log_date: date
    meal_type: MealTypeEnum
    image_url: str | None = Field(None, max_length=500)
    items: list[DietLogItemCreate] = Field(..., min_length=1)


class DietLogUpdate(BaseModel):
    log_date: date | None = None
    meal_type: MealTypeEnum | None = None
    image_url: str | None = Field(None, max_length=500)
    items: list[DietLogItemCreate] | None = Field(None, min_length=1)


class DietLogItemResponse(BaseModel):
    id: int
    food_catalog_item_id: int | None
    food_name: str
    serving_size: str | None
    serving_grams: float | None
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    sugar_g: float | None
    saturated_fat_g: float | None
    unsaturated_fat_g: float | None
    confidence: float | None


class DietLogResponse(BaseModel):
    id: int
    log_date: date
    meal_type: MealTypeEnum
    image_url: str | None
    ai_analyzed: bool
    items: list[DietLogItemResponse]
    created_at: datetime


class DailyNutritionTotal(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class DailyDietData(BaseModel):
    date: date
    meals: dict[str, list[DietLogResponse]]
    daily_total: DailyNutritionTotal
    target_remaining: DailyNutritionTotal | None


class DietLogSingleResponse(BaseModel):
    status: Literal["success"] = "success"
    data: DietLogResponse
    message: str | None = None


class DietLogsByDateResponse(BaseModel):
    status: Literal["success"] = "success"
    data: DailyDietData
    message: str | None = None


class DietDeleteResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str


class FoodCatalogItemResponse(BaseModel):
    id: int
    name: str
    aliases: list[str]
    category: str
    serving_basis_g: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    sugar_g: float | None
    saturated_fat_g: float | None
    unsaturated_fat_g: float | None


class FoodCatalogSearchResponse(BaseModel):
    status: Literal["success"] = "success"
    data: list[FoodCatalogItemResponse]
