from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.diet import DietLog, DietLogItem
from app.models.exercise import ExerciseLog
from app.models.user import UserProfile
from app.schemas.dashboard import (
    DailyBreakdown,
    NutritionProgress,
    NutritionValues,
    Streak,
    TodayDashboardData,
    TodayExercise,
    TodayNutrition,
    WeeklyDashboardData,
    WeeklyExerciseSummary,
    WeeklyNutritionAvg,
)


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_today(self, user_id: int, target_date: date) -> TodayDashboardData:
        profile_result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()

        nutrition_totals_result = await self.db.execute(
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
        nutrition_totals = nutrition_totals_result.one()
        consumed = NutritionValues(
            calories=self._decimal_to_float(nutrition_totals[0]),
            protein_g=self._decimal_to_float(nutrition_totals[1]),
            carbs_g=self._decimal_to_float(nutrition_totals[2]),
            fat_g=self._decimal_to_float(nutrition_totals[3]),
        )

        target: NutritionValues | None = None
        remaining: NutritionValues | None = None
        progress_percent: NutritionProgress | None = None
        if (
            profile is not None
            and profile.target_calories is not None
            and profile.target_protein_g is not None
            and profile.target_carbs_g is not None
            and profile.target_fat_g is not None
        ):
            target = NutritionValues(
                calories=self._decimal_to_float(Decimal(profile.target_calories)),
                protein_g=self._decimal_to_float(profile.target_protein_g),
                carbs_g=self._decimal_to_float(profile.target_carbs_g),
                fat_g=self._decimal_to_float(profile.target_fat_g),
            )
            remaining = NutritionValues(
                calories=self._decimal_to_float(Decimal(profile.target_calories) - self._to_decimal(consumed.calories)),
                protein_g=self._decimal_to_float(profile.target_protein_g - self._to_decimal(consumed.protein_g)),
                carbs_g=self._decimal_to_float(profile.target_carbs_g - self._to_decimal(consumed.carbs_g)),
                fat_g=self._decimal_to_float(profile.target_fat_g - self._to_decimal(consumed.fat_g)),
            )
            progress_percent = NutritionProgress(
                calories=self._progress(consumed.calories, target.calories),
                protein_g=self._progress(consumed.protein_g, target.protein_g),
                carbs_g=self._progress(consumed.carbs_g, target.carbs_g),
                fat_g=self._progress(consumed.fat_g, target.fat_g),
            )

        exercise_logs_result = await self.db.execute(
            select(ExerciseLog)
            .options(selectinload(ExerciseLog.exercise_sets))
            .where(ExerciseLog.user_id == user_id, ExerciseLog.exercise_date == target_date)
            .order_by(ExerciseLog.created_at, ExerciseLog.id)
        )
        exercise_logs = exercise_logs_result.scalars().all()

        muscle_groups_seen: set[str] = set()
        muscle_groups_trained: list[str] = []
        for log in exercise_logs:
            group = log.muscle_group.value
            if group not in muscle_groups_seen:
                muscle_groups_seen.add(group)
                muscle_groups_trained.append(group)

        total_sets = sum(len(log.exercise_sets) for log in exercise_logs)
        exercises_count = len(exercise_logs)

        streak_start = target_date - timedelta(days=29)
        exercise_streak_dates_result = await self.db.execute(
            select(ExerciseLog.exercise_date)
            .where(
                ExerciseLog.user_id == user_id,
                ExerciseLog.exercise_date >= streak_start,
                ExerciseLog.exercise_date <= target_date,
            )
            .distinct()
        )
        exercise_dates = {row[0] for row in exercise_streak_dates_result.all()}

        diet_streak_dates_result = await self.db.execute(
            select(DietLog.log_date)
            .where(
                DietLog.user_id == user_id,
                DietLog.log_date >= streak_start,
                DietLog.log_date <= target_date,
            )
            .distinct()
        )
        diet_dates = {row[0] for row in diet_streak_dates_result.all()}

        return TodayDashboardData(
            date=target_date,
            nutrition=TodayNutrition(
                target=target,
                consumed=consumed,
                remaining=remaining,
                progress_percent=progress_percent,
            ),
            exercise=TodayExercise(
                completed=exercises_count > 0,
                muscle_groups_trained=muscle_groups_trained,
                total_sets=total_sets,
                exercises_count=exercises_count,
            ),
            streak=Streak(
                exercise_days=self._calculate_streak_days(target_date, exercise_dates),
                diet_logging_days=self._calculate_streak_days(target_date, diet_dates),
            ),
        )

    async def get_weekly(self, user_id: int, week_start: date) -> WeeklyDashboardData:
        week_end = week_start + timedelta(days=6)

        weekly_nutrition_totals_result = await self.db.execute(
            select(
                func.coalesce(func.sum(DietLogItem.calories), 0),
                func.coalesce(func.sum(DietLogItem.protein_g), 0),
                func.coalesce(func.sum(DietLogItem.carbs_g), 0),
                func.coalesce(func.sum(DietLogItem.fat_g), 0),
            )
            .select_from(DietLog)
            .join(DietLogItem, DietLogItem.diet_log_id == DietLog.id)
            .where(DietLog.user_id == user_id, DietLog.log_date >= week_start, DietLog.log_date <= week_end)
        )
        weekly_nutrition_totals = weekly_nutrition_totals_result.one()

        nutrition_avg = WeeklyNutritionAvg(
            calories=self._decimal_to_float(weekly_nutrition_totals[0] / Decimal("7")),
            protein_g=self._decimal_to_float(weekly_nutrition_totals[1] / Decimal("7")),
            carbs_g=self._decimal_to_float(weekly_nutrition_totals[2] / Decimal("7")),
            fat_g=self._decimal_to_float(weekly_nutrition_totals[3] / Decimal("7")),
        )

        exercise_days_result = await self.db.execute(
            select(ExerciseLog.exercise_date)
            .where(
                ExerciseLog.user_id == user_id,
                ExerciseLog.exercise_date >= week_start,
                ExerciseLog.exercise_date <= week_end,
            )
            .distinct()
        )
        exercise_days = {row[0] for row in exercise_days_result.all()}

        muscle_group_counts_result = await self.db.execute(
            select(ExerciseLog.muscle_group, func.count(ExerciseLog.id))
            .where(
                ExerciseLog.user_id == user_id,
                ExerciseLog.exercise_date >= week_start,
                ExerciseLog.exercise_date <= week_end,
            )
            .group_by(ExerciseLog.muscle_group)
        )
        muscle_groups = {row[0].value: int(row[1]) for row in muscle_group_counts_result.all()}

        daily_calories_result = await self.db.execute(
            select(DietLog.log_date, func.coalesce(func.sum(DietLogItem.calories), 0))
            .select_from(DietLog)
            .join(DietLogItem, DietLogItem.diet_log_id == DietLog.id)
            .where(DietLog.user_id == user_id, DietLog.log_date >= week_start, DietLog.log_date <= week_end)
            .group_by(DietLog.log_date)
        )
        calories_by_date = {row[0]: self._decimal_to_float(row[1]) for row in daily_calories_result.all()}

        daily_breakdown: list[DailyBreakdown] = []
        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            daily_breakdown.append(
                DailyBreakdown(
                    date=current_date,
                    calories=calories_by_date.get(current_date, 0.0),
                    exercised=current_date in exercise_days,
                )
            )

        return WeeklyDashboardData(
            week_start=week_start,
            week_end=week_end,
            nutrition_avg=nutrition_avg,
            exercise_summary=WeeklyExerciseSummary(
                total_days=len(exercise_days),
                muscle_groups=muscle_groups,
            ),
            daily_breakdown=daily_breakdown,
        )

    @staticmethod
    def _progress(consumed: float, target: float) -> float:
        if target == 0:
            return 0.0
        return round((consumed / target) * 100, 1)

    @staticmethod
    def _calculate_streak_days(target_date: date, available_dates: set[date]) -> int:
        streak_days = 0
        for day_offset in range(30):
            current_date = target_date - timedelta(days=day_offset)
            if current_date in available_dates:
                streak_days += 1
            else:
                break
        return streak_days

    @staticmethod
    def _to_decimal(value: float) -> Decimal:
        return Decimal(str(value))

    @staticmethod
    def _decimal_to_float(value: Decimal | int | float) -> float:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
