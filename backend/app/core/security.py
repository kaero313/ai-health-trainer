from datetime import datetime, timedelta, timezone
import hashlib
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()


class TokenPayload(BaseModel):
    sub: int
    exp: int
    token_type: str | None = None


def _bcrypt_ready_password(password: str) -> bytes:
    password_bytes = password.encode("utf-8")
    return hashlib.sha256(password_bytes).hexdigest().encode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_password_bytes = _bcrypt_ready_password(plain_password)
    hashed_password_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    password_bytes = _bcrypt_ready_password(password)
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed_password.decode("utf-8")


def _create_token(subject: int, expires_delta: timedelta, token_type: str) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(subject),
        "exp": expire,
        "token_type": token_type,
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: int) -> str:
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(subject=subject, expires_delta=expires, token_type="access")


def create_refresh_token(subject: int) -> str:
    expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(subject=subject, expires_delta=expires, token_type="refresh")


def get_refresh_token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def decode_jwt_token(token: str, expected_token_type: str | None = None) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    raw_sub = payload.get("sub")
    if raw_sub is None:
        raise ValueError("Missing token subject")

    try:
        subject = int(raw_sub)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid token subject") from exc

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise ValueError("Missing token expiration")

    token_type = payload.get("token_type")
    if expected_token_type is not None and token_type != expected_token_type:
        raise ValueError("Unexpected token type")

    return TokenPayload(sub=subject, exp=exp, token_type=token_type)
