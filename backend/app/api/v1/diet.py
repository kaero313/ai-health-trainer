import hashlib
import json
import time
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_ai_quota_service, get_current_user
from app.models.diet import MealTypeEnum
from app.models.user import User
from app.schemas.ai import DietRecommendationResponse, FoodAnalysisResponse
from app.schemas.diet import (
    DietDeleteResponse,
    FoodCatalogSearchResponse,
    DietLogCreate,
    DietLogSingleResponse,
    DietLogsByDateResponse,
    DietLogUpdate,
)
from app.services.ai_service import (
    FOOD_ANALYSIS_SCHEMA_VERSION,
    AIService,
    AIServiceError,
)
from app.services.ai_trace_service import AIGenerationAttemptRecorder
from app.services.ai_quota_service import AIQuotaError, AIQuotaService
from app.services.diet_service import DietService, DietServiceError
from app.services.rag_service import RAGService
from app.services.recommendation_service import RecommendationService, RecommendationServiceError

router = APIRouter(prefix="/diet", tags=["diet"])


def _hash_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def _raise_recommendation_error(service_error: RecommendationServiceError) -> None:
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


@router.get("/foods", response_model=FoodCatalogSearchResponse)
async def search_food_catalog(
    query: str = Query("", max_length=100),
    limit: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FoodCatalogSearchResponse:
    _ = current_user
    service = DietService(db)
    data = await service.search_food_catalog(query, limit)
    return FoodCatalogSearchResponse(data=data)


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
    return DietDeleteResponse(message="식단 기록을 삭제했습니다.")


@router.post("/analyze-image", response_model=FoodAnalysisResponse)
async def analyze_food_image(
    image: UploadFile = File(...),
    meal_type: MealTypeEnum | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    quota_service: AIQuotaService = Depends(get_ai_quota_service),
) -> FoodAnalysisResponse:
    pipeline_started = time.perf_counter()
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

    image_read_started = time.perf_counter()
    image_bytes = await image.read()
    image_read_latency_ms = int((time.perf_counter() - image_read_started) * 1000)
    max_size_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(image_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Image size must be <= {settings.MAX_IMAGE_SIZE_MB}MB",
            },
        )

    input_context_hash = hashlib.sha256(image_bytes).hexdigest()
    try:
        generation_trace = await ai_service.start_generation_trace(
            db,
            user_id=current_user.id,
            request_type="food_analysis",
            prompt_version=FOOD_ANALYSIS_SCHEMA_VERSION,
            input_context_hash=input_context_hash,
            trace_metadata={
                "mime_type": image.content_type,
                "image_size_bytes": len(image_bytes),
                "image_read_latency_ms": image_read_latency_ms,
            },
        )
    except AIServiceError as exc:
        _raise_ai_error(exc)
    try:
        await quota_service.reserve(db, generation_trace)
    except AIQuotaError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    attempt_recorder = AIGenerationAttemptRecorder(
        db,
        generation_trace.id,
        quota_service,
    )
    generation_started = time.perf_counter()
    try:
        invocation = await ai_service.analyze_food_image(
            image_bytes,
            image.content_type,
            attempt_recorder=attempt_recorder,
        )
    except AIServiceError as exc:
        generation_call_latency_ms = int((time.perf_counter() - generation_started) * 1000)
        await ai_service.complete_generation_trace(
            db,
            generation_trace.id,
            quota_service=quota_service,
            user_id=current_user.id,
            request_type="food_analysis",
            prompt_version=FOOD_ANALYSIS_SCHEMA_VERSION,
            status=exc.trace_status,
            input_context_hash=input_context_hash,
            error=exc,
            provider_invoked=exc.provider_invoked,
            trace_metadata={
                "mime_type": image.content_type,
                "image_size_bytes": len(image_bytes),
                "image_read_latency_ms": image_read_latency_ms,
                "generation_call_latency_ms": generation_call_latency_ms,
                "pre_persistence_pipeline_latency_ms": int(
                    (time.perf_counter() - pipeline_started) * 1000
                ),
            },
        )
        _raise_ai_error(exc)
    generation_call_latency_ms = int((time.perf_counter() - generation_started) * 1000)

    result = dict(invocation.payload)

    foods = result.get("foods", [])
    if "total" not in result:
        result["total"] = {
            "calories": sum(f.get("calories", 0) for f in foods),
            "protein_g": sum(f.get("protein_g", 0) for f in foods),
            "carbs_g": sum(f.get("carbs_g", 0) for f in foods),
            "fat_g": sum(f.get("fat_g", 0) for f in foods),
        }

    await ai_service.complete_generation_trace(
        db,
        generation_trace.id,
        quota_service=quota_service,
        user_id=current_user.id,
        request_type="food_analysis",
        prompt_version=FOOD_ANALYSIS_SCHEMA_VERSION,
        status="succeeded",
        input_context_hash=input_context_hash,
        output_hash=_hash_json(result),
        invocation=invocation,
        trace_metadata={
            "mime_type": image.content_type,
            "food_count": len(foods),
            "image_size_bytes": len(image_bytes),
            "image_read_latency_ms": image_read_latency_ms,
            "generation_call_latency_ms": generation_call_latency_ms,
            "pre_persistence_pipeline_latency_ms": int(
                (time.perf_counter() - pipeline_started) * 1000
            ),
        },
    )

    return FoodAnalysisResponse(status="success", data=result)


@router.get("/recommend", response_model=DietRecommendationResponse)
async def recommend_diet(
    target_date: date | None = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    quota_service: AIQuotaService = Depends(get_ai_quota_service),
) -> DietRecommendationResponse:
    settings = get_settings()
    ai_service = AIService(settings)
    rag_service = RAGService(db, settings)
    rec_service = RecommendationService(
        db,
        ai_service,
        rag_service,
        quota_service,
    )

    try:
        result = await rec_service.recommend_diet(current_user.id, target_date or date.today())
    except RecommendationServiceError as exc:
        _raise_recommendation_error(exc)
    except AIServiceError as exc:
        _raise_ai_error(exc)

    return DietRecommendationResponse(status="success", data=result)
