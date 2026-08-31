from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis_client

router = APIRouter(prefix="/health", tags=["health"])

APP_VERSION = "1.0.0"


async def _is_redis_connected() -> bool:
    try:
        return await get_redis_client().ping()
    except Exception:
        return False


@router.get("", response_model=None)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "db": "disconnected",
            },
        )

    redis_connected = await _is_redis_connected()
    if not redis_connected:
        return {
            "status": "degraded",
            "db": "connected",
            "redis": "disconnected",
        }

    return {
        "status": "ok",
        "version": APP_VERSION,
        "db": "connected",
        "redis": "connected",
    }
