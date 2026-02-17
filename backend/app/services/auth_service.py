from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    get_password_hash,
    get_refresh_token_expires_at,
    verify_password,
)
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    AuthUserResponse,
    LoginRequest,
    LoginResponseData,
    RefreshResponseData,
    RegisterRequest,
    RegisterResponseData,
)

settings = get_settings()


class AuthServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, payload: RegisterRequest) -> RegisterResponseData:
        existing_user = await self._get_user_by_email(payload.email)
        if existing_user is not None:
            raise AuthServiceError(409, "CONFLICT", "Email is already registered")

        user = User(
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            is_active=True,
        )

        self.db.add(user)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise AuthServiceError(409, "CONFLICT", "Email is already registered") from exc

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        refresh_token_row = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=get_refresh_token_expires_at(),
            is_revoked=False,
        )
        self.db.add(refresh_token_row)

        await self.db.commit()
        await self.db.refresh(user)

        return RegisterResponseData(
            user=AuthUserResponse(
                id=user.id,
                email=user.email,
                created_at=user.created_at,
            ),
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def login(self, payload: LoginRequest) -> LoginResponseData:
        user = await self._get_user_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AuthServiceError(401, "UNAUTHORIZED", "Invalid email or password")

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        refresh_token_row = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=get_refresh_token_expires_at(),
            is_revoked=False,
        )
        self.db.add(refresh_token_row)

        await self.db.commit()

        return LoginResponseData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> RefreshResponseData:
        try:
            token_payload = decode_jwt_token(refresh_token, expected_token_type="refresh")
        except ValueError as exc:
            raise AuthServiceError(401, "UNAUTHORIZED", "Invalid refresh token") from exc

        refresh_row = await self._get_valid_refresh_token(refresh_token)
        if refresh_row is None:
            raise AuthServiceError(401, "UNAUTHORIZED", "Invalid refresh token")

        user = await self._get_user_by_id(token_payload.sub)
        if user is None or not user.is_active:
            raise AuthServiceError(401, "UNAUTHORIZED", "Invalid refresh token")

        access_token = create_access_token(user.id)
        return RefreshResponseData(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(func.lower(User.email) == email.lower()))
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _get_valid_refresh_token(self, refresh_token: str) -> RefreshToken | None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == refresh_token,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none()
