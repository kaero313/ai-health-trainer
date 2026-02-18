from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exercise import ExerciseLog, ExerciseSet, MuscleGroupEnum
from app.schemas.exercise import (
    ExerciseHistoryDateEntry,
    ExerciseHistoryExerciseSummary,
    ExerciseHistoryResponseData,
    ExerciseLogCreate,
    ExerciseLogResponse,
    ExerciseLogUpdate,
    ExerciseLogsListResponseData,
    ExerciseProgressEntry,
    ExerciseSetCreate,
    ExerciseSetResponse,
)


class ExerciseServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ExerciseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_log(self, user_id: int, payload: ExerciseLogCreate) -> ExerciseLogResponse:
        log = ExerciseLog(
            user_id=user_id,
            exercise_date=payload.exercise_date,
            exercise_name=payload.exercise_name,
            muscle_group=payload.muscle_group,
            duration_min=payload.duration_min,
            memo=payload.memo,
        )
        log.exercise_sets = self._build_exercise_sets(payload.sets)
        self.db.add(log)
        await self.db.commit()

        created_log = await self._get_log_by_id(log.id, include_sets=True)
        if created_log is None:
            raise ExerciseServiceError(500, "INTERNAL_ERROR", "Failed to load created exercise log")
        return self._to_log_response(created_log)

    async def get_logs_by_date(self, user_id: int, log_date: date) -> ExerciseLogsListResponseData:
        result = await self.db.execute(
            select(ExerciseLog)
            .options(selectinload(ExerciseLog.exercise_sets))
            .where(ExerciseLog.user_id == user_id, ExerciseLog.exercise_date == log_date)
            .order_by(ExerciseLog.created_at, ExerciseLog.id)
        )
        logs = result.scalars().all()

        muscle_groups_trained: list[str] = []
        seen_groups: set[str] = set()
        for log in logs:
            group = log.muscle_group.value
            if group not in seen_groups:
                seen_groups.add(group)
                muscle_groups_trained.append(group)

        return ExerciseLogsListResponseData(
            date=log_date,
            exercises=[self._to_log_response(log) for log in logs],
            muscle_groups_trained=muscle_groups_trained,
        )

    async def update_log(self, user_id: int, log_id: int, payload: ExerciseLogUpdate) -> ExerciseLogResponse:
        log = await self._get_log_by_id(log_id, include_sets=True)
        if log is None:
            raise ExerciseServiceError(404, "NOT_FOUND", "Exercise log not found")
        if log.user_id != user_id:
            raise ExerciseServiceError(403, "FORBIDDEN", "You can only modify your own exercise log")

        update_data = payload.model_dump(exclude_unset=True, exclude={"sets"})
        sets_payload = payload.sets if "sets" in payload.model_fields_set else None

        for field_name, field_value in update_data.items():
            setattr(log, field_name, field_value)

        if sets_payload is not None:
            log.exercise_sets.clear()
            log.exercise_sets.extend(self._build_exercise_sets(sets_payload))

        await self.db.commit()

        updated_log = await self._get_log_by_id(log_id, include_sets=True)
        if updated_log is None:
            raise ExerciseServiceError(500, "INTERNAL_ERROR", "Failed to load updated exercise log")
        return self._to_log_response(updated_log)

    async def delete_log(self, user_id: int, log_id: int) -> None:
        log = await self._get_log_by_id(log_id, include_sets=False)
        if log is None:
            raise ExerciseServiceError(404, "NOT_FOUND", "Exercise log not found")
        if log.user_id != user_id:
            raise ExerciseServiceError(403, "FORBIDDEN", "You can only delete your own exercise log")

        await self.db.delete(log)
        await self.db.commit()

    async def get_history_by_muscle(
        self,
        user_id: int,
        muscle_group: MuscleGroupEnum,
        limit: int,
    ) -> ExerciseHistoryResponseData:
        result = await self.db.execute(
            select(ExerciseLog)
            .options(selectinload(ExerciseLog.exercise_sets))
            .where(ExerciseLog.user_id == user_id, ExerciseLog.muscle_group == muscle_group)
            .order_by(ExerciseLog.exercise_date.desc(), ExerciseLog.created_at.desc(), ExerciseLog.id.desc())
            .limit(limit)
        )
        logs = result.scalars().all()

        history_entries: list[ExerciseHistoryDateEntry] = []
        for log in logs:
            summary = self._to_history_summary(log)
            if history_entries and history_entries[-1].date == log.exercise_date:
                history_entries[-1].exercises.append(summary)
            else:
                history_entries.append(
                    ExerciseHistoryDateEntry(
                        date=log.exercise_date,
                        exercises=[summary],
                    )
                )

        grouped_by_name: dict[str, list[ExerciseLog]] = defaultdict(list)
        for log in logs:
            grouped_by_name[log.exercise_name].append(log)

        progress: dict[str, ExerciseProgressEntry] = {}
        for exercise_name, exercise_logs in grouped_by_name.items():
            latest_weight = self._max_weight_from_log(exercise_logs[0])
            previous_weight = (
                self._max_weight_from_log(exercise_logs[1]) if len(exercise_logs) > 1 else latest_weight
            )
            latest_weight_value = latest_weight if latest_weight is not None else 0.0
            previous_weight_value = previous_weight if previous_weight is not None else 0.0
            weight_diff = latest_weight_value - previous_weight_value

            if weight_diff > 0:
                trend = "increasing"
            elif weight_diff < 0:
                trend = "decreasing"
            else:
                trend = "stable"

            progress[exercise_name] = ExerciseProgressEntry(
                weight_change=f"{weight_diff:+.1f}kg",
                trend=trend,
            )

        return ExerciseHistoryResponseData(
            muscle_group=muscle_group,
            history=history_entries,
            progress=progress,
        )

    async def _get_log_by_id(self, log_id: int, include_sets: bool) -> ExerciseLog | None:
        statement = select(ExerciseLog).where(ExerciseLog.id == log_id)
        if include_sets:
            statement = statement.options(selectinload(ExerciseLog.exercise_sets))
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    def _build_exercise_sets(sets_payload: list[ExerciseSetCreate]) -> list[ExerciseSet]:
        exercise_sets: list[ExerciseSet] = []
        for set_payload in sets_payload:
            exercise_sets.append(
                ExerciseSet(
                    set_number=set_payload.set_number,
                    reps=set_payload.reps,
                    weight_kg=Decimal(str(set_payload.weight_kg)) if set_payload.weight_kg is not None else None,
                    is_completed=set_payload.is_completed,
                )
            )
        return exercise_sets

    def _to_log_response(self, log: ExerciseLog) -> ExerciseLogResponse:
        return ExerciseLogResponse(
            id=log.id,
            exercise_date=log.exercise_date,
            exercise_name=log.exercise_name,
            muscle_group=log.muscle_group,
            duration_min=log.duration_min,
            memo=log.memo,
            sets=[self._to_set_response(exercise_set) for exercise_set in log.exercise_sets],
            created_at=log.created_at,
        )

    @staticmethod
    def _to_set_response(exercise_set: ExerciseSet) -> ExerciseSetResponse:
        return ExerciseSetResponse(
            id=exercise_set.id,
            set_number=exercise_set.set_number,
            reps=exercise_set.reps,
            weight_kg=float(exercise_set.weight_kg) if exercise_set.weight_kg is not None else None,
            is_completed=exercise_set.is_completed,
        )

    def _to_history_summary(self, log: ExerciseLog) -> ExerciseHistoryExerciseSummary:
        set_count = len(log.exercise_sets)
        if set_count == 0:
            average_reps = 0
        else:
            total_reps = sum(exercise_set.reps for exercise_set in log.exercise_sets)
            average_reps = int(
                (Decimal(total_reps) / Decimal(set_count)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )

        max_weight = self._max_weight_from_log(log)
        return ExerciseHistoryExerciseSummary(
            exercise_name=log.exercise_name,
            sets=set_count,
            reps=average_reps,
            weight_kg=max_weight,
        )

    @staticmethod
    def _max_weight_from_log(log: ExerciseLog) -> float | None:
        weights = [
            float(exercise_set.weight_kg)
            for exercise_set in log.exercise_sets
            if exercise_set.weight_kg is not None
        ]
        if not weights:
            return None
        return max(weights)
