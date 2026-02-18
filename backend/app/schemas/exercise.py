from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.exercise import MuscleGroupEnum


class ExerciseSetCreate(BaseModel):
    set_number: int = Field(..., ge=1)
    reps: int = Field(..., ge=1, le=1000)
    weight_kg: float | None = Field(None, ge=0, le=500)
    is_completed: bool = True


class ExerciseLogCreate(BaseModel):
    exercise_date: date
    exercise_name: str = Field(..., min_length=1, max_length=100)
    muscle_group: MuscleGroupEnum
    duration_min: int | None = Field(None, ge=1, le=600)
    memo: str | None = Field(None, max_length=500)
    sets: list[ExerciseSetCreate] = Field(..., min_length=1)


class ExerciseLogUpdate(BaseModel):
    exercise_date: date | None = None
    exercise_name: str | None = Field(None, min_length=1, max_length=100)
    muscle_group: MuscleGroupEnum | None = None
    duration_min: int | None = Field(None, ge=1, le=600)
    memo: str | None = Field(None, max_length=500)
    sets: list[ExerciseSetCreate] | None = Field(None, min_length=1)


class ExerciseSetResponse(BaseModel):
    id: int
    set_number: int
    reps: int
    weight_kg: float | None
    is_completed: bool


class ExerciseLogResponse(BaseModel):
    id: int
    exercise_date: date
    exercise_name: str
    muscle_group: MuscleGroupEnum
    duration_min: int | None
    memo: str | None
    sets: list[ExerciseSetResponse]
    created_at: datetime


class ExerciseLogsListResponseData(BaseModel):
    date: date
    exercises: list[ExerciseLogResponse]
    muscle_groups_trained: list[str]


class ExerciseHistoryExerciseSummary(BaseModel):
    exercise_name: str
    sets: int
    reps: int
    weight_kg: float | None


class ExerciseHistoryDateEntry(BaseModel):
    date: date
    exercises: list[ExerciseHistoryExerciseSummary]


class ExerciseProgressEntry(BaseModel):
    weight_change: str
    trend: Literal["increasing", "decreasing", "stable"]


class ExerciseHistoryResponseData(BaseModel):
    muscle_group: MuscleGroupEnum
    history: list[ExerciseHistoryDateEntry]
    progress: dict[str, ExerciseProgressEntry]


class ExerciseLogSingleResponse(BaseModel):
    status: Literal["success"] = "success"
    data: ExerciseLogResponse
    message: str | None = None


class ExerciseLogsListResponse(BaseModel):
    status: Literal["success"] = "success"
    data: ExerciseLogsListResponseData
    message: str | None = None


class ExerciseHistoryResponse(BaseModel):
    status: Literal["success"] = "success"
    data: ExerciseHistoryResponseData
    message: str | None = None


class ExerciseDeleteResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str
