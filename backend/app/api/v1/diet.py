from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.diet import MealTypeEnum
from app.models.user import User
from app.schemas.ai import FoodAnalysisResponse
from app.schemas.diet import (
    DietDeleteResponse,
    DietLogCreate,
    DietLogSingleResponse,
    DietLogsByDateResponse,
    DietLogUpdate,
)
from app.services.ai_service import AIService, AIServiceError
from app.services.diet_service import DietService, DietServiceError

router = APIRouter(prefix="/diet", tags=["diet"])


def _raise_http_error(service_error: DietServiceError) -> None:
    raise HTTPException(
        status_code=service_error.status_code,
        detail={
            "code": service_error.code,
            "message": service_error.message,
        },
    )


def _raise_ai_error(service_error: AIServiceError) -> None:
    raise HTTPException(
        status_code=service_error.status_code,
        detail={
            "code": service_error.code,
            "message": service_error.message,
        },
    )


@router.post("/logs", status_code=status.HTTP_201_CREATED, response_model=DietLogSingleResponse)
async def create_diet_log(
    payload: DietLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DietLogSingleResponse:
    service = DietService(db)
    try:
        data = await service.create_log(current_user.id, payload)
    except DietServiceError as exc:
        _raise_http_error(exc)
    return DietLogSingleResponse(data=data)


@router.get("/logs", response_model=DietLogsByDateResponse)
async def get_diet_logs(
    date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DietLogsByDateResponse:
    service = DietService(db)
    try:
        data = await service.get_logs_by_date(current_user.id, date)
    except DietServiceError as exc:
        _raise_http_error(exc)
    return DietLogsByDateResponse(data=data)


@router.put("/logs/{log_id}", response_model=DietLogSingleResponse)
async def update_diet_log(
    log_id: int,
    payload: DietLogUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DietLogSingleResponse:
    service = DietService(db)
    try:
        data = await service.update_log(current_user.id, log_id, payload)
    except DietServiceError as exc:
        _raise_http_error(exc)
    return DietLogSingleResponse(data=data)


@router.delete("/logs/{log_id}", response_model=DietDeleteResponse)
async def delete_diet_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DietDeleteResponse:
    service = DietService(db)
    try:
        await service.delete_log(current_user.id, log_id)
    except DietServiceError as exc:
        _raise_http_error(exc)
    return DietDeleteResponse(message="Diet log deleted successfully")


@router.post("/analyze-image", response_model=FoodAnalysisResponse)
async def analyze_food_image(
    image: UploadFile = File(...),
    meal_type: MealTypeEnum | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FoodAnalysisResponse:
    _ = meal_type
    settings = get_settings()
    ai_service = AIService(settings)

    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Only image/jpeg and image/png are supported",
            },
        )

    image_bytes = await image.read()
    max_size_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(image_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Image size must be <= {settings.MAX_IMAGE_SIZE_MB}MB",
            },
        )

    is_limited = await ai_service.check_rate_limit(db, current_user.id)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "DAILY_LIMIT_EXCEEDED",
                "message": "일일 AI 사용 한도에 도달했습니다",
            },
        )

    try:
        result = await ai_service.analyze_food_image(image_bytes, image.content_type)
    except AIServiceError as exc:
        _raise_ai_error(exc)

    return FoodAnalysisResponse(status="success", data=result)
