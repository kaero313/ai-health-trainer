from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.diet import DietLog, DietLogItem, FoodCatalogItem, MealTypeEnum
from app.models.user import UserProfile
from app.schemas.diet import (
    DailyDietData,
    DailyNutritionTotal,
    DietLogCreate,
    DietLogItemCreate,
    DietLogItemResponse,
    DietLogResponse,
    DietLogUpdate,
    FoodCatalogItemResponse,
)


class DietServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class DietService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_log(self, user_id: int, payload: DietLogCreate) -> DietLogResponse:
        log = DietLog(
            user_id=user_id,
            log_date=payload.log_date,
            meal_type=payload.meal_type,
            image_url=payload.image_url,
        )
        log.diet_log_items = self._build_diet_items(payload.items)
        self.db.add(log)
        await self.db.commit()

        created_log = await self._get_log_by_id(log.id, include_items=True)
        if created_log is None:
            raise DietServiceError(500, "INTERNAL_ERROR", "Failed to load created diet log")
        return self._to_log_response(created_log)

    async def get_logs_by_date(self, user_id: int, log_date: date) -> DailyDietData:
        result = await self.db.execute(
            select(DietLog)
            .options(selectinload(DietLog.diet_log_items))
            .where(DietLog.user_id == user_id, DietLog.log_date == log_date)
            .order_by(DietLog.created_at, DietLog.id)
        )
        logs = result.scalars().all()

        meals: dict[str, list[DietLogResponse]] = {meal_type.value: [] for meal_type in MealTypeEnum}

        total_calories = Decimal("0")
        total_protein = Decimal("0")
        total_carbs = Decimal("0")
        total_fat = Decimal("0")

        for log in logs:
            meals[log.meal_type.value].append(self._to_log_response(log))
            for item in log.diet_log_items:
                total_calories += item.calories
                total_protein += item.protein_g
                total_carbs += item.carbs_g
                total_fat += item.fat_g

        daily_total = DailyNutritionTotal(
            calories=self._decimal_to_float(total_calories),
            protein_g=self._decimal_to_float(total_protein),
            carbs_g=self._decimal_to_float(total_carbs),
            fat_g=self._decimal_to_float(total_fat),
        )

        profile_result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()

        target_remaining: DailyNutritionTotal | None = None
        if (
            profile is not None
            and profile.target_calories is not None
            and profile.target_protein_g is not None
            and profile.target_carbs_g is not None
            and profile.target_fat_g is not None
        ):
            target_remaining = DailyNutritionTotal(
                calories=self._decimal_to_float(Decimal(profile.target_calories) - total_calories),
                protein_g=self._decimal_to_float(profile.target_protein_g - total_protein),
                carbs_g=self._decimal_to_float(profile.target_carbs_g - total_carbs),
                fat_g=self._decimal_to_float(profile.target_fat_g - total_fat),
            )

        return DailyDietData(
            date=log_date,
            meals=meals,
            daily_total=daily_total,
            target_remaining=target_remaining,
        )

    async def update_log(self, user_id: int, log_id: int, payload: DietLogUpdate) -> DietLogResponse:
        log = await self._get_log_by_id(log_id, include_items=True)
        if log is None:
            raise DietServiceError(404, "NOT_FOUND", "Diet log not found")
        if log.user_id != user_id:
            raise DietServiceError(403, "FORBIDDEN", "You can only modify your own diet log")

        update_data = payload.model_dump(exclude_unset=True, exclude={"items"})
        items_payload = payload.items if "items" in payload.model_fields_set else None

        for field_name, field_value in update_data.items():
            setattr(log, field_name, field_value)

        if items_payload is not None:
            log.diet_log_items.clear()
            log.diet_log_items.extend(self._build_diet_items(items_payload))

        await self.db.commit()

        updated_log = await self._get_log_by_id(log_id, include_items=True)
        if updated_log is None:
            raise DietServiceError(500, "INTERNAL_ERROR", "Failed to load updated diet log")
        return self._to_log_response(updated_log)

    async def delete_log(self, user_id: int, log_id: int) -> None:
        log = await self._get_log_by_id(log_id, include_items=False)
        if log is None:
            raise DietServiceError(404, "NOT_FOUND", "Diet log not found")
        if log.user_id != user_id:
            raise DietServiceError(403, "FORBIDDEN", "You can only delete your own diet log")

        await self.db.delete(log)
        await self.db.commit()

    async def search_food_catalog(
        self,
        query: str,
        limit: int,
    ) -> list[FoodCatalogItemResponse]:
        normalized_query = query.strip()
        statement = select(FoodCatalogItem).where(
            FoodCatalogItem.is_active.is_(True)
        )

        if normalized_query:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    FoodCatalogItem.name.ilike(pattern),
                    cast(FoodCatalogItem.aliases, String).ilike(pattern),
                )
            )

        result = await self.db.execute(
            statement.order_by(FoodCatalogItem.name).limit(limit)
        )
        return [self._to_food_catalog_response(item) for item in result.scalars().all()]

    async def _get_log_by_id(self, log_id: int, include_items: bool) -> DietLog | None:
        statement = select(DietLog).where(DietLog.id == log_id)
        if include_items:
            statement = statement.options(selectinload(DietLog.diet_log_items))
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    def _build_diet_items(items_payload: list[DietLogItemCreate]) -> list[DietLogItem]:
        diet_items: list[DietLogItem] = []
        for item_payload in items_payload:
            diet_items.append(
                DietLogItem(
                    food_catalog_item_id=item_payload.food_catalog_item_id,
                    food_name=item_payload.food_name,
                    serving_size=item_payload.serving_size,
                    serving_grams=(
                        Decimal(str(item_payload.serving_grams))
                        if item_payload.serving_grams is not None
                        else None
                    ),
                    calories=Decimal(str(item_payload.calories)),
                    protein_g=Decimal(str(item_payload.protein_g)),
                    carbs_g=Decimal(str(item_payload.carbs_g)),
                    fat_g=Decimal(str(item_payload.fat_g)),
                    sugar_g=(
                        Decimal(str(item_payload.sugar_g))
                        if item_payload.sugar_g is not None
                        else None
                    ),
                    saturated_fat_g=(
                        Decimal(str(item_payload.saturated_fat_g))
                        if item_payload.saturated_fat_g is not None
                        else None
                    ),
                    unsaturated_fat_g=(
                        Decimal(str(item_payload.unsaturated_fat_g))
                        if item_payload.unsaturated_fat_g is not None
                        else None
                    ),
                    confidence=(
                        Decimal(str(item_payload.confidence))
                        if item_payload.confidence is not None
                        else None
                    ),
                )
            )
        return diet_items

    def _to_log_response(self, log: DietLog) -> DietLogResponse:
        return DietLogResponse(
            id=log.id,
            log_date=log.log_date,
            meal_type=log.meal_type,
            image_url=log.image_url,
            ai_analyzed=log.ai_analyzed,
            items=[self._to_item_response(item) for item in log.diet_log_items],
            created_at=log.created_at,
        )

    @staticmethod
    def _to_item_response(item: DietLogItem) -> DietLogItemResponse:
        return DietLogItemResponse(
            id=item.id,
            food_catalog_item_id=item.food_catalog_item_id,
            food_name=item.food_name,
            serving_size=item.serving_size,
            serving_grams=(
                float(item.serving_grams)
                if item.serving_grams is not None
                else None
            ),
            calories=float(item.calories),
            protein_g=float(item.protein_g),
            carbs_g=float(item.carbs_g),
            fat_g=float(item.fat_g),
            sugar_g=float(item.sugar_g) if item.sugar_g is not None else None,
            saturated_fat_g=(
                float(item.saturated_fat_g)
                if item.saturated_fat_g is not None
                else None
            ),
            unsaturated_fat_g=(
                float(item.unsaturated_fat_g)
                if item.unsaturated_fat_g is not None
                else None
            ),
            confidence=float(item.confidence) if item.confidence is not None else None,
        )

    @staticmethod
    def _to_food_catalog_response(item: FoodCatalogItem) -> FoodCatalogItemResponse:
        return FoodCatalogItemResponse(
            id=item.id,
            name=item.name,
            aliases=item.aliases,
            category=item.category,
            serving_basis_g=float(item.serving_basis_g),
            calories=float(item.calories),
            protein_g=float(item.protein_g),
            carbs_g=float(item.carbs_g),
            fat_g=float(item.fat_g),
            sugar_g=float(item.sugar_g) if item.sugar_g is not None else None,
            saturated_fat_g=(
                float(item.saturated_fat_g)
                if item.saturated_fat_g is not None
                else None
            ),
            unsaturated_fat_g=(
                float(item.unsaturated_fat_g)
                if item.unsaturated_fat_g is not None
                else None
            ),
        )

    @staticmethod
    def _decimal_to_float(value: Decimal) -> float:
        return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
