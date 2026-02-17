from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.services.auth_service import AuthService, AuthServiceError

router = APIRouter(prefix="/auth", tags=["auth"])


def _raise_http_error(service_error: AuthServiceError) -> None:
    raise HTTPException(
        status_code=service_error.status_code,
        detail={
            "code": service_error.code,
            "message": service_error.message,
        },
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    service = AuthService(db)
    try:
        data = await service.register(payload)
    except AuthServiceError as exc:
        _raise_http_error(exc)

    return RegisterResponse(data=data)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    service = AuthService(db)
    try:
        data = await service.login(payload)
    except AuthServiceError as exc:
        _raise_http_error(exc)

    return LoginResponse(data=data)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    service = AuthService(db)
    try:
        data = await service.refresh_access_token(payload.refresh_token)
    except AuthServiceError as exc:
        _raise_http_error(exc)

    return RefreshResponse(data=data)
