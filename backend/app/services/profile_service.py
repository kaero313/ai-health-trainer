from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import ActivityLevelEnum, GenderEnum, GoalEnum, UserProfile
from app.models.weight_log import WeightLog
from app.schemas.profile import ProfileResponseData, ProfileUpsertRequest

ACTIVITY_MULTIPLIER = {
    ActivityLevelEnum.SEDENTARY: Decimal("1.2"),
    ActivityLevelEnum.LIGHT: Decimal("1.375"),
    ActivityLevelEnum.MODERATE: Decimal("1.55"),
    ActivityLevelEnum.ACTIVE: Decimal("1.725"),
    ActivityLevelEnum.VERY_ACTIVE: Decimal("1.9"),
}


class ProfileServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_profile(self, user_id: int) -> ProfileResponseData:
        profile = await self._get_profile_by_user_id(user_id)
        if profile is None:
            raise ProfileServiceError(404, "NOT_FOUND", "Profile is not set")
        return self._to_response(profile)

    async def upsert_profile(self, user_id: int, payload: ProfileUpsertRequest) -> ProfileResponseData:
        profile = await self._get_profile_by_user_id(user_id)
        targets = self._calculate_targets(payload)

        if profile is None:
            profile = UserProfile(
                user_id=user_id,
                height_cm=Decimal(str(payload.height_cm)),
                weight_kg=Decimal(str(payload.weight_kg)),
                age=payload.age,
                gender=payload.gender,
                goal=payload.goal,
                activity_level=payload.activity_level,
                allergies=payload.allergies,
                food_preferences=payload.food_preferences,
                tdee_kcal=targets["tdee_kcal"],
                target_calories=targets["target_calories"],
                target_protein_g=targets["target_protein_g"],
                target_carbs_g=targets["target_carbs_g"],
                target_fat_g=targets["target_fat_g"],
            )
            self.db.add(profile)
        else:
            profile.height_cm = Decimal(str(payload.height_cm))
            profile.weight_kg = Decimal(str(payload.weight_kg))
            profile.age = payload.age
            profile.gender = payload.gender
            profile.goal = payload.goal
            profile.activity_level = payload.activity_level
            profile.allergies = payload.allergies
            profile.food_preferences = payload.food_preferences
            profile.tdee_kcal = targets["tdee_kcal"]
            profile.target_calories = targets["target_calories"]
            profile.target_protein_g = targets["target_protein_g"]
            profile.target_carbs_g = targets["target_carbs_g"]
            profile.target_fat_g = targets["target_fat_g"]

        await self.db.commit()
        await self.db.refresh(profile)
        return self._to_response(profile)

    async def upsert_weight_log(self, user_id: int, weight_kg: float, log_date: date) -> dict[str, date | float]:
        profile = await self._get_profile_by_user_id(user_id)
        if profile is None:
            raise ProfileServiceError(404, "NOT_FOUND", "Profile is not set")

        profile_payload = self._build_profile_payload(profile, weight_kg=weight_kg)
        targets = self._calculate_targets(profile_payload)

        result = await self.db.execute(
            select(WeightLog).where(
                WeightLog.user_id == user_id,
                WeightLog.log_date == log_date,
            )
        )
        weight_log = result.scalar_one_or_none()

        if weight_log is None:
            weight_log = WeightLog(
                user_id=user_id,
                log_date=log_date,
                weight_kg=Decimal(str(weight_kg)),
            )
            self.db.add(weight_log)
        else:
            weight_log.weight_kg = Decimal(str(weight_kg))

        profile.weight_kg = Decimal(str(weight_kg))
        profile.tdee_kcal = targets["tdee_kcal"]
        profile.target_calories = targets["target_calories"]
        profile.target_protein_g = targets["target_protein_g"]
        profile.target_carbs_g = targets["target_carbs_g"]
        profile.target_fat_g = targets["target_fat_g"]

        await self.db.commit()

        return {
            "log_date": log_date,
            "weight_kg": float(self._round_decimal(Decimal(str(weight_kg)))),
        }

    async def get_weight_history(self, user_id: int, months: int) -> list[dict[str, date | float]]:
        today = date.today()
        start_month_index = today.year * 12 + today.month - months
        start_year, start_month_zero_based = divmod(start_month_index, 12)
        start_date = date(start_year, start_month_zero_based + 1, 1)

        result = await self.db.execute(
            select(WeightLog)
            .where(
                WeightLog.user_id == user_id,
                WeightLog.log_date >= start_date,
                WeightLog.log_date <= today,
            )
            .order_by(WeightLog.log_date.asc())
        )
        logs = result.scalars().all()

        return [
            {
                "log_date": item.log_date,
                "weight_kg": float(item.weight_kg),
            }
            for item in logs
        ]

    async def _get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        return result.scalar_one_or_none()

    def _build_profile_payload(self, profile: UserProfile, weight_kg: float | None = None) -> ProfileUpsertRequest:
        if (
            profile.height_cm is None
            or profile.age is None
            or profile.gender is None
            or profile.activity_level is None
            or (profile.weight_kg is None and weight_kg is None)
        ):
            raise ProfileServiceError(400, "VALIDATION_ERROR", "Profile data is incomplete")

        return ProfileUpsertRequest(
            height_cm=float(profile.height_cm),
            weight_kg=weight_kg if weight_kg is not None else float(profile.weight_kg),
            age=profile.age,
            gender=profile.gender,
            goal=profile.goal,
            activity_level=profile.activity_level,
            allergies=profile.allergies,
            food_preferences=profile.food_preferences,
        )

    @staticmethod
    def _round_decimal(value: Decimal, scale: str = "0.1") -> Decimal:
        return value.quantize(Decimal(scale), rounding=ROUND_HALF_UP)

    @staticmethod
    def _round_int(value: Decimal) -> int:
        return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def _calculate_targets(self, payload: ProfileUpsertRequest) -> dict[str, int | Decimal]:
        weight_kg = Decimal(str(payload.weight_kg))
        height_cm = Decimal(str(payload.height_cm))
        age = Decimal(str(payload.age))

        if payload.gender == GenderEnum.MALE:
            bmr = Decimal("10") * weight_kg + Decimal("6.25") * height_cm - Decimal("5") * age + Decimal("5")
        else:
            bmr = Decimal("10") * weight_kg + Decimal("6.25") * height_cm - Decimal("5") * age - Decimal("161")

        tdee = bmr * ACTIVITY_MULTIPLIER[payload.activity_level]
        tdee_kcal = self._round_int(tdee)

        if payload.goal == GoalEnum.BULK:
            target_calories = tdee_kcal + 300
        elif payload.goal == GoalEnum.DIET:
            target_calories = tdee_kcal - 500
        else:
            target_calories = tdee_kcal

        target_protein_g = weight_kg * Decimal("1.8")
        target_fat_g = Decimal(target_calories) * Decimal("0.25") / Decimal("9")
        target_carbs_g = (
            Decimal(target_calories) - target_protein_g * Decimal("4") - target_fat_g * Decimal("9")
        ) / Decimal("4")

        return {
            "tdee_kcal": tdee_kcal,
            "target_calories": target_calories,
            "target_protein_g": self._round_decimal(target_protein_g),
            "target_carbs_g": self._round_decimal(target_carbs_g),
            "target_fat_g": self._round_decimal(target_fat_g),
        }

    def _to_response(self, profile: UserProfile) -> ProfileResponseData:
        return ProfileResponseData(
            user_id=profile.user_id,
            height_cm=float(profile.height_cm) if profile.height_cm is not None else None,
            weight_kg=float(profile.weight_kg) if profile.weight_kg is not None else None,
            age=profile.age,
            gender=profile.gender,
            goal=profile.goal,
            activity_level=profile.activity_level,
            allergies=profile.allergies,
            food_preferences=profile.food_preferences,
            tdee_kcal=profile.tdee_kcal,
            target_calories=profile.target_calories,
            target_protein_g=float(profile.target_protein_g) if profile.target_protein_g is not None else None,
            target_carbs_g=float(profile.target_carbs_g) if profile.target_carbs_g is not None else None,
            target_fat_g=float(profile.target_fat_g) if profile.target_fat_g is not None else None,
        )
