from typing import Literal

from pydantic import BaseModel, Field


class NutrientSummary(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class AnalyzedFoodItem(BaseModel):
    food_name: str
    serving_size: str | None = None
    calories: float
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    confidence: float = Field(ge=0, le=1)


class FoodAnalysisResponseData(BaseModel):
    foods: list[AnalyzedFoodItem]
    total: NutrientSummary


class SuggestedFood(BaseModel):
    food_name: str
    serving_size: str | None = None
    calories: float
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    reason: str | None = None


class DietRecommendationResponseData(BaseModel):
    remaining_nutrients: NutrientSummary
    recommendation: str
    suggested_foods: list[SuggestedFood]
    sources: list[str] = Field(default_factory=list)


class SuggestedExercise(BaseModel):
    exercise_name: str
    muscle_group: str
    sets: int
    reps: int
    weight_kg: float | None = None
    reason: str | None = None


class ExerciseRecommendationResponseData(BaseModel):
    recommendation: str
    suggested_exercises: list[SuggestedExercise]
    sources: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    context_type: Literal["diet", "exercise", "general"] = "general"


class ContextUsed(BaseModel):
    profile_loaded: bool
    today_diet_records: int = 0
    today_exercise_records: int = 0


class ChatResponseData(BaseModel):
    answer: str
    context_used: ContextUsed
    sources: list[str] = Field(default_factory=list)


class FoodAnalysisResponse(BaseModel):
    status: Literal["success"] = "success"
    data: FoodAnalysisResponseData


class DietRecommendationResponse(BaseModel):
    status: Literal["success"] = "success"
    data: DietRecommendationResponseData


class ExerciseRecommendationResponse(BaseModel):
    status: Literal["success"] = "success"
    data: ExerciseRecommendationResponseData


class ChatResponse(BaseModel):
    status: Literal["success"] = "success"
    data: ChatResponseData
