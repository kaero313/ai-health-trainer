from fastapi import APIRouter

from app.api.v1.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)


@api_router.get("/health", tags=["health"])
async def api_health_check() -> dict[str, str]:
    return {"status": "ok"}
