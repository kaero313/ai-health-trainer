from datetime import date
from typing import Literal

from pydantic import BaseModel


class NutritionValues(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class NutritionProgress(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class TodayNutrition(BaseModel):
    target: NutritionValues | None
    consumed: NutritionValues
    remaining: NutritionValues | None
    progress_percent: NutritionProgress | None


class TodayExercise(BaseModel):
    completed: bool
    muscle_groups_trained: list[str]
    total_sets: int
    exercises_count: int


class Streak(BaseModel):
    exercise_days: int
    diet_logging_days: int


class TodayDashboardData(BaseModel):
    date: date
    nutrition: TodayNutrition
    exercise: TodayExercise
    streak: Streak


class DailyBreakdown(BaseModel):
    date: date
    calories: float
    exercised: bool


class WeeklyNutritionAvg(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class WeeklyExerciseSummary(BaseModel):
    total_days: int
    muscle_groups: dict[str, int]


class WeeklyDashboardData(BaseModel):
    week_start: date
    week_end: date
    nutrition_avg: WeeklyNutritionAvg
    exercise_summary: WeeklyExerciseSummary
    daily_breakdown: list[DailyBreakdown]


class TodayDashboardResponse(BaseModel):
    status: Literal["success"] = "success"
    data: TodayDashboardData
    message: str | None = None


class WeeklyDashboardResponse(BaseModel):
    status: Literal["success"] = "success"
    data: WeeklyDashboardData
    message: str | None = None
