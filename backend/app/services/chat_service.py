from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_recommendation import AIRecommendation, RecommendationTypeEnum
from app.models.diet import DietLog, DietLogItem
from app.models.exercise import ExerciseLog
from app.models.user import UserProfile
from app.services.ai_service import AIService
from app.services.rag_service import RAGService


class ChatServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ChatService:
    GOAL_DESCRIPTION_MAP = {
        "bulk": "벌크업",
        "diet": "다이어트",
        "maintain": "유지",
    }

    def __init__(self, db: AsyncSession, ai_service: AIService, rag_service: RAGService):
        self.db = db
        self.ai_service = ai_service
        self.rag_service = rag_service

    async def chat(self, user_id: int, message: str, context_type: str) -> dict:
        profile = await self._get_profile(user_id)
        today = date.today()
        goal_description = self.GOAL_DESCRIPTION_MAP.get(profile.goal.value, profile.goal.value)

        context_lines = [self._build_profile_line(profile, goal_description)]
        context_used = {
            "profile_loaded": True,
            "today_diet_records": 0,
            "today_exercise_records": 0,
        }

        if context_type == "diet":
            diet_line, today_diet_records = await self._build_diet_context_line(user_id, today, profile)
            context_lines.append(diet_line)
            context_used["today_diet_records"] = today_diet_records
            rag_category = "nutrition"
            rag_query = f"{goal_description} 식단 코칭"
        elif context_type == "exercise":
            exercise_line, today_exercise_records = await self._build_exercise_context_line(user_id, today)
            context_lines.append(exercise_line)
            context_used["today_exercise_records"] = today_exercise_records
            rag_category = "exercise"
            rag_query = f"{goal_description} 운동 코칭"
        elif context_type == "general":
            rag_category = None
            rag_query = f"{goal_description} 건강 코칭"
        else:
            raise ChatServiceError(400, "VALIDATION_ERROR", "지원하지 않는 context_type입니다")

        documents = await self.rag_service.search(rag_query, category=rag_category, top_k=3)
        rag_context = self._build_rag_context(documents)
        user_context_text = "\n".join(context_lines)

        ai_result = await self.ai_service.chat(message, user_context_text, rag_context)
        answer = str(ai_result.get("answer", "")).strip()
        if not answer:
            raise ChatServiceError(502, "AI_PARSE_ERROR", "AI 응답을 처리할 수 없습니다")

        rag_sources = [str(document.get("title")) for document in documents if document.get("title")]
        ai_sources = ai_result.get("sources")
        if isinstance(ai_sources, list):
            sources = [str(item) for item in ai_sources if str(item).strip()]
        else:
            sources = []
        if not sources:
            sources = rag_sources

        await self._save_chat_recommendation(
            user_id=user_id,
            context_type=context_type,
            message=message,
            answer=answer,
            rag_sources=sources,
        )

        return {
            "answer": answer,
            "context_used": context_used,
            "sources": sources,
        }

    async def _get_profile(self, user_id: int) -> UserProfile:
        result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            raise ChatServiceError(404, "NOT_FOUND", "프로필을 먼저 설정해주세요")
        return profile

    async def _build_diet_context_line(self, user_id: int, target_date: date, profile: UserProfile) -> tuple[str, int]:
        meal_count_result = await self.db.execute(
            select(func.count(DietLog.id)).where(
                DietLog.user_id == user_id,
                DietLog.log_date == target_date,
            )
        )
        meal_count = int(meal_count_result.scalar_one())

        totals_result = await self.db.execute(
            select(
                func.coalesce(func.sum(DietLogItem.calories), 0),
                func.coalesce(func.sum(DietLogItem.protein_g), 0),
                func.coalesce(func.sum(DietLogItem.carbs_g), 0),
                func.coalesce(func.sum(DietLogItem.fat_g), 0),
            )
            .select_from(DietLog)
            .join(DietLogItem, DietLogItem.diet_log_id == DietLog.id)
            .where(
                DietLog.user_id == user_id,
                DietLog.log_date == target_date,
            )
        )
        consumed_row = totals_result.one()

        consumed_calories = self._to_float(consumed_row[0])
        consumed_protein = self._to_float(consumed_row[1])
        consumed_carbs = self._to_float(consumed_row[2])
        consumed_fat = self._to_float(consumed_row[3])

        target_calories = float(profile.target_calories or 0)
        target_protein = self._to_float(profile.target_protein_g)
        target_carbs = self._to_float(profile.target_carbs_g)
        target_fat = self._to_float(profile.target_fat_g)

        remaining_calories = self._round_one_decimal(target_calories - consumed_calories)
        remaining_protein = self._round_one_decimal(target_protein - consumed_protein)
        remaining_carbs = self._round_one_decimal(target_carbs - consumed_carbs)
        remaining_fat = self._round_one_decimal(target_fat - consumed_fat)

        context_line = (
            f"[오늘 식단] 칼로리 {consumed_calories}/{self._round_one_decimal(target_calories)}kcal, "
            f"단백질 {consumed_protein}/{target_protein}g, 탄수화물 {consumed_carbs}/{target_carbs}g, "
            f"지방 {consumed_fat}/{target_fat}g, 남은 목표: 칼로리 {remaining_calories}kcal / "
            f"단백질 {remaining_protein}g / 탄수화물 {remaining_carbs}g / 지방 {remaining_fat}g"
        )
        return context_line, meal_count

    async def _build_exercise_context_line(self, user_id: int, target_date: date) -> tuple[str, int]:
        start_date = target_date - timedelta(days=6)
        result = await self.db.execute(
            select(ExerciseLog)
            .options(selectinload(ExerciseLog.exercise_sets))
            .where(
                ExerciseLog.user_id == user_id,
                ExerciseLog.exercise_date >= start_date,
                ExerciseLog.exercise_date <= target_date,
            )
            .order_by(ExerciseLog.exercise_date.desc(), ExerciseLog.created_at.desc(), ExerciseLog.id.desc())
        )
        logs = result.scalars().all()
        today_count = sum(1 for log in logs if log.exercise_date == target_date)

        if not logs:
            return "[최근 운동(7일)] 기록 없음", today_count

        history_lines: list[str] = []
        for log in logs[:7]:
            set_count = len(log.exercise_sets)
            history_lines.append(
                f"- {log.exercise_date.isoformat()} {log.exercise_name} ({log.muscle_group.value}, {set_count}세트)"
            )
        return "[최근 운동(7일)]\n" + "\n".join(history_lines), today_count

    async def _save_chat_recommendation(
        self,
        user_id: int,
        context_type: str,
        message: str,
        answer: str,
        rag_sources: list[str],
    ) -> None:
        summary_message = message.strip()
        if len(summary_message) > 120:
            summary_message = summary_message[:117] + "..."

        recommendation = AIRecommendation(
            user_id=user_id,
            type=RecommendationTypeEnum.COACHING,
            context_summary=f"{context_type} 채팅: {summary_message}",
            prompt_used=None,
            recommendation=answer,
            rag_sources=rag_sources,
            model_used=self.ai_service.settings.AI_DEFAULT_MODEL,
        )

        try:
            self.db.add(recommendation)
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            raise ChatServiceError(500, "INTERNAL_ERROR", "채팅 결과 저장에 실패했습니다") from exc

    @staticmethod
    def _build_profile_line(profile: UserProfile, goal_description: str) -> str:
        height = ChatService._to_float(profile.height_cm)
        weight = ChatService._to_float(profile.weight_kg)
        activity_level = profile.activity_level.value if profile.activity_level is not None else "unknown"
        return (
            f"[프로필] 키 {height}cm, 몸무게 {weight}kg, 목표: {goal_description}, 활동수준: {activity_level}"
        )

    @staticmethod
    def _build_rag_context(documents: list[dict]) -> str:
        if not documents:
            return "참고 자료 없음"
        return "\n\n".join(f"[{document['title']}]\n{document['content']}" for document in documents)

    @staticmethod
    def _to_float(value: Decimal | int | float | None) -> float:
        if value is None:
            return 0.0
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
        return ChatService._round_one_decimal(float(decimal_value))

    @staticmethod
    def _round_one_decimal(value: float) -> float:
        return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
