from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_recommendation import AIRecommendation, RecommendationTypeEnum
from app.models.diet import DietLog, DietLogItem
from app.models.exercise import ExerciseLog, MuscleGroupEnum
from app.models.user import UserProfile
from app.services.ai_service import AIService
from app.services.rag_service import RAGService


class RecommendationServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class RecommendationService:
    GOAL_DESCRIPTION_MAP = {
        "bulk": "벌크업",
        "diet": "다이어트",
        "maintain": "유지",
    }

    def __init__(self, db: AsyncSession, ai_service: AIService, rag_service: RAGService) -> None:
        self.db = db
        self.ai_service = ai_service
        self.rag_service = rag_service

    async def recommend_diet(self, user_id: int, target_date: date) -> dict:
        profile = await self._get_profile(user_id)
        goal = profile.goal.value
        goal_description = self.GOAL_DESCRIPTION_MAP.get(goal, goal)

        consumed_calories, consumed_protein, consumed_carbs, consumed_fat = await self._get_daily_consumed(
            user_id,
            target_date,
        )

        target_calories = profile.target_calories if profile.target_calories is not None else 0
        target_protein = self._to_float(profile.target_protein_g)
        target_carbs = self._to_float(profile.target_carbs_g)
        target_fat = self._to_float(profile.target_fat_g)

        remaining = {
            "calories": self._round_one_decimal(float(target_calories) - consumed_calories),
            "protein_g": self._round_one_decimal(target_protein - consumed_protein),
            "carbs_g": self._round_one_decimal(target_carbs - consumed_carbs),
            "fat_g": self._round_one_decimal(target_fat - consumed_fat),
        }

        user_context = {
            "height_cm": self._to_float(profile.height_cm),
            "weight_kg": self._to_float(profile.weight_kg),
            "goal": goal,
            "goal_description": goal_description,
            "activity_level": profile.activity_level.value if profile.activity_level is not None else "unknown",
            "allergies": self._list_to_csv(profile.allergies),
            "food_preferences": self._list_to_csv(profile.food_preferences),
            "target_calories": int(target_calories),
            "target_protein_g": target_protein,
            "target_carbs_g": target_carbs,
            "target_fat_g": target_fat,
            "consumed_calories": consumed_calories,
            "consumed_protein": consumed_protein,
            "consumed_carbs": consumed_carbs,
            "consumed_fat": consumed_fat,
        }

        documents = await self.rag_service.search(
            f"{goal_description} 식단 추천",
            category="nutrition",
            top_k=3,
        )
        rag_context = self._build_rag_context(documents)

        ai_result = await self.ai_service.recommend_diet(user_context, rag_context)
        recommendation_text = str(ai_result.get("recommendation", ""))
        suggested_foods = ai_result.get("suggested_foods")
        if not isinstance(suggested_foods, list):
            suggested_foods = []

        sources = [str(document.get("title", "")) for document in documents if document.get("title")]
        await self._save_recommendation(
            user_id=user_id,
            recommendation_type=RecommendationTypeEnum.DIET,
            context_summary=f"{target_date.isoformat()} 식단 추천",
            recommendation=recommendation_text,
            rag_sources=sources,
            prompt_used=None,
        )

        return {
            "remaining_nutrients": remaining,
            "recommendation": recommendation_text,
            "suggested_foods": suggested_foods,
            "sources": sources,
        }

    async def recommend_exercise(self, user_id: int, muscle_group: str | None) -> dict:
        profile = await self._get_profile(user_id)
        goal = profile.goal.value
        goal_description = self.GOAL_DESCRIPTION_MAP.get(goal, goal)

        parsed_muscle_group: MuscleGroupEnum | None = None
        if muscle_group is not None:
            try:
                parsed_muscle_group = MuscleGroupEnum(muscle_group)
            except ValueError as exc:
                raise RecommendationServiceError(400, "VALIDATION_ERROR", "지원하지 않는 근육군입니다") from exc

        recent_logs = await self._get_recent_exercise_logs(user_id, parsed_muscle_group)
        selected_muscle_group = (
            parsed_muscle_group.value
            if parsed_muscle_group is not None
            else (recent_logs[0].muscle_group.value if recent_logs else "full_body")
        )

        documents = await self.rag_service.search(
            f"{goal_description} {selected_muscle_group} 운동 추천",
            category="exercise",
            top_k=3,
        )
        rag_context = self._build_rag_context(documents)

        exercise_history = self._build_exercise_history(recent_logs)
        user_context = {
            "goal": goal,
            "weight_kg": self._to_float(profile.weight_kg),
            "muscle_group": selected_muscle_group,
            "exercise_history": exercise_history,
        }

        ai_result = await self.ai_service.recommend_exercise(user_context, rag_context)
        recommendation_text = str(ai_result.get("recommendation", ""))
        suggested_exercises = ai_result.get("suggested_exercises")
        if not isinstance(suggested_exercises, list):
            suggested_exercises = []

        sources = [str(document.get("title", "")) for document in documents if document.get("title")]
        await self._save_recommendation(
            user_id=user_id,
            recommendation_type=RecommendationTypeEnum.EXERCISE,
            context_summary=f"{selected_muscle_group} 운동 추천",
            recommendation=recommendation_text,
            rag_sources=sources,
            prompt_used=None,
        )

        return {
            "recommendation": recommendation_text,
            "suggested_exercises": suggested_exercises,
            "sources": sources,
        }

    async def _get_profile(self, user_id: int) -> UserProfile:
        result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            raise RecommendationServiceError(404, "NOT_FOUND", "프로필을 먼저 설정해주세요")
        return profile

    async def _get_daily_consumed(self, user_id: int, target_date: date) -> tuple[float, float, float, float]:
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(DietLogItem.calories), 0),
                func.coalesce(func.sum(DietLogItem.protein_g), 0),
                func.coalesce(func.sum(DietLogItem.carbs_g), 0),
                func.coalesce(func.sum(DietLogItem.fat_g), 0),
            )
            .select_from(DietLog)
            .join(DietLogItem, DietLogItem.diet_log_id == DietLog.id)
            .where(DietLog.user_id == user_id, DietLog.log_date == target_date)
        )
        row = result.one()
        return (
            self._to_float(row[0]),
            self._to_float(row[1]),
            self._to_float(row[2]),
            self._to_float(row[3]),
        )

    async def _get_recent_exercise_logs(
        self,
        user_id: int,
        muscle_group: MuscleGroupEnum | None,
    ) -> list[ExerciseLog]:
        stmt = (
            select(ExerciseLog)
            .options(selectinload(ExerciseLog.exercise_sets))
            .where(ExerciseLog.user_id == user_id)
            .order_by(ExerciseLog.exercise_date.desc(), ExerciseLog.created_at.desc(), ExerciseLog.id.desc())
            .limit(3)
        )
        if muscle_group is not None:
            stmt = stmt.where(ExerciseLog.muscle_group == muscle_group)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def _save_recommendation(
        self,
        user_id: int,
        recommendation_type: RecommendationTypeEnum,
        context_summary: str,
        recommendation: str,
        rag_sources: list[str],
        prompt_used: str | None,
    ) -> None:
        record = AIRecommendation(
            user_id=user_id,
            type=recommendation_type,
            context_summary=context_summary,
            prompt_used=prompt_used,
            recommendation=recommendation,
            rag_sources=rag_sources,
            model_used=self.ai_service.settings.AI_DEFAULT_MODEL,
        )
        try:
            self.db.add(record)
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            raise RecommendationServiceError(500, "INTERNAL_ERROR", "추천 결과 저장에 실패했습니다") from exc

    @staticmethod
    def _build_rag_context(documents: list[dict]) -> str:
        if not documents:
            return "참고 자료 없음"
        return "\n\n".join(f"[{doc['title']}]\n{doc['content']}" for doc in documents)

    @staticmethod
    def _build_exercise_history(logs: list[ExerciseLog]) -> str:
        if not logs:
            return "기록 없음"

        lines: list[str] = []
        for log in logs:
            set_parts: list[str] = []
            for exercise_set in log.exercise_sets:
                if exercise_set.weight_kg is None:
                    weight_text = "맨몸"
                else:
                    weight_text = f"{float(exercise_set.weight_kg):.1f}kg"
                set_parts.append(f"{exercise_set.set_number}세트 {exercise_set.reps}회 {weight_text}")
            sets_text = ", ".join(set_parts) if set_parts else "세트 정보 없음"
            lines.append(f"- {log.exercise_date.isoformat()} {log.exercise_name}: {sets_text}")
        return "\n".join(lines)

    @staticmethod
    def _list_to_csv(values: list[str]) -> str:
        normalized = [value.strip() for value in values if value.strip()]
        return ", ".join(normalized) if normalized else "없음"

    @staticmethod
    def _to_float(value: Decimal | int | float | None) -> float:
        if value is None:
            return 0.0
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
        return RecommendationService._round_one_decimal(float(decimal_value))

    @staticmethod
    def _round_one_decimal(value: float) -> float:
        return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
