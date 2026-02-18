from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.exercise import router as exercise_router
from app.api.v1.profile import router as profile_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(exercise_router)
api_router.include_router(profile_router)


@api_router.get("/health", tags=["health"])
async def api_health_check() -> dict[str, str]:
    return {"status": "ok"}
