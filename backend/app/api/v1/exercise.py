from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.exercise import MuscleGroupEnum
from app.models.user import User
from app.schemas.exercise import (
    ExerciseDeleteResponse,
    ExerciseHistoryResponse,
    ExerciseLogCreate,
    ExerciseLogSingleResponse,
    ExerciseLogUpdate,
    ExerciseLogsListResponse,
)
from app.services.exercise_service import ExerciseService, ExerciseServiceError

router = APIRouter(prefix="/exercise", tags=["exercise"])


def _raise_http_error(service_error: ExerciseServiceError) -> None:
    raise HTTPException(
        status_code=service_error.status_code,
        detail={
            "code": service_error.code,
            "message": service_error.message,
        },
    )


@router.post("/logs", status_code=status.HTTP_201_CREATED, response_model=ExerciseLogSingleResponse)
async def create_exercise_log(
    payload: ExerciseLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExerciseLogSingleResponse:
    service = ExerciseService(db)
    try:
        data = await service.create_log(current_user.id, payload)
    except ExerciseServiceError as exc:
        _raise_http_error(exc)
    return ExerciseLogSingleResponse(data=data)


@router.get("/logs", response_model=ExerciseLogsListResponse)
async def get_exercise_logs(
    date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExerciseLogsListResponse:
    service = ExerciseService(db)
    try:
        data = await service.get_logs_by_date(current_user.id, date)
    except ExerciseServiceError as exc:
        _raise_http_error(exc)
    return ExerciseLogsListResponse(data=data)


@router.put("/logs/{log_id}", response_model=ExerciseLogSingleResponse)
async def update_exercise_log(
    log_id: int,
    payload: ExerciseLogUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExerciseLogSingleResponse:
    service = ExerciseService(db)
    try:
        data = await service.update_log(current_user.id, log_id, payload)
    except ExerciseServiceError as exc:
        _raise_http_error(exc)
    return ExerciseLogSingleResponse(data=data)


@router.delete("/logs/{log_id}", response_model=ExerciseDeleteResponse)
async def delete_exercise_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExerciseDeleteResponse:
    service = ExerciseService(db)
    try:
        await service.delete_log(current_user.id, log_id)
    except ExerciseServiceError as exc:
        _raise_http_error(exc)
    return ExerciseDeleteResponse(message="Exercise log deleted successfully")


@router.get("/history/{muscle_group}", response_model=ExerciseHistoryResponse)
async def get_exercise_history(
    muscle_group: MuscleGroupEnum,
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExerciseHistoryResponse:
    service = ExerciseService(db)
    try:
        data = await service.get_history_by_muscle(current_user.id, muscle_group, limit)
    except ExerciseServiceError as exc:
        _raise_http_error(exc)
    return ExerciseHistoryResponse(data=data)
