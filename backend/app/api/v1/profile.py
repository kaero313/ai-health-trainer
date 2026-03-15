from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpsertRequest
from app.services.profile_service import ProfileService, ProfileServiceError

router = APIRouter(prefix="/profile", tags=["profile"])


def _raise_http_error(service_error: ProfileServiceError) -> None:
    raise HTTPException(
        status_code=service_error.status_code,
        detail={
            "code": service_error.code,
            "message": service_error.message,
        },
    )


@router.get("/check")
async def check_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProfileService(db)
    try:
        await service.get_profile(current_user.id)
        return {"has_profile": True}
    except ProfileServiceError:
        return {"has_profile": False}


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    service = ProfileService(db)
    try:
        data = await service.get_profile(current_user.id)
    except ProfileServiceError as exc:
        _raise_http_error(exc)

    return ProfileResponse(data=data)


@router.put("", response_model=ProfileResponse)
async def upsert_profile(
    payload: ProfileUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    service = ProfileService(db)
    try:
        data = await service.upsert_profile(current_user.id, payload)
    except ProfileServiceError as exc:
        _raise_http_error(exc)

    return ProfileResponse(data=data)
