from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


NonEmptyText = Annotated[str, Field(min_length=1, max_length=4000)]
NutrientValue = Annotated[float, Field(ge=0, le=10000)]
SourceRef = Annotated[str, Field(pattern=r"^S[1-9][0-9]*$")]
MuscleGroup = Literal["chest", "back", "shoulder", "legs", "arms", "core", "cardio", "full_body"]
SOURCE_MARKER_PATTERN = re.compile(r"(?<![A-Za-z0-9])S[1-9][0-9]*(?![0-9])")


class StructuredOutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FoodAnalysisItemV2(StructuredOutputModel):
    food_name: Annotated[str, Field(min_length=1, max_length=200)]
    serving_size: Annotated[str, Field(min_length=1, max_length=100)]
    calories: NutrientValue
    protein_g: NutrientValue
    carbs_g: NutrientValue
    fat_g: NutrientValue
    confidence: Annotated[float, Field(ge=0, le=1)]


class FoodAnalysisV2(StructuredOutputModel):
    foods: Annotated[list[FoodAnalysisItemV2], Field(min_length=1, max_length=20)]


class SuggestedFoodV2(StructuredOutputModel):
    food_name: Annotated[str, Field(min_length=1, max_length=200)]
    serving_size: Annotated[str, Field(min_length=1, max_length=100)]
    calories: NutrientValue
    protein_g: NutrientValue
    carbs_g: NutrientValue
    fat_g: NutrientValue
    reason: Annotated[str, Field(min_length=1, max_length=1000)]


class SourceReferencedOutput(StructuredOutputModel):
    source_refs: Annotated[list[SourceRef], Field(min_length=1, max_length=10)]

    @field_validator("source_refs")
    @classmethod
    def source_refs_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("source_refs must be unique")
        return value

    @model_validator(mode="after")
    def internal_refs_must_not_appear_in_visible_text(self) -> "SourceReferencedOutput":
        visible_payload = self.model_dump(mode="json", exclude={"source_refs"})
        if any(SOURCE_MARKER_PATTERN.search(text) for text in _iter_text(visible_payload)):
            raise ValueError("internal source references must only appear in source_refs")
        return self


class DietRecommendationV2(SourceReferencedOutput):
    recommendation: NonEmptyText
    suggested_foods: Annotated[list[SuggestedFoodV2], Field(min_length=1, max_length=10)]


class SuggestedExerciseV2(StructuredOutputModel):
    exercise_name: Annotated[str, Field(min_length=1, max_length=200)]
    muscle_group: MuscleGroup
    sets: Annotated[int, Field(ge=1, le=20)]
    reps: Annotated[int, Field(ge=1, le=100)]
    weight_kg: Annotated[float | None, Field(default=None, ge=0, le=1000)]
    reason: Annotated[str, Field(min_length=1, max_length=1000)]


class ExerciseRecommendationV2(SourceReferencedOutput):
    recommendation: NonEmptyText
    suggested_exercises: Annotated[list[SuggestedExerciseV2], Field(min_length=1, max_length=15)]


class ChatV2(SourceReferencedOutput):
    answer: NonEmptyText


def _iter_text(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_text(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_text(item)
