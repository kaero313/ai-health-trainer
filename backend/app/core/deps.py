from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.core.security import decode_jwt_token
from app.models.user import User
from app.services.ai_quota_service import AIQuotaService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_ai_quota_service() -> AIQuotaService:
    return AIQuotaService(get_settings(), get_redis_client())


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "UNAUTHORIZED",
            "message": "Invalid or expired access token",
        },
    )

    try:
        token_payload = decode_jwt_token(token, expected_token_type="access")
    except ValueError as exc:
        raise credentials_error from exc

    result = await db.execute(select(User).where(User.id == token_payload.sub))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_error

    return user
