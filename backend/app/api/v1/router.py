from fastapi import APIRouter

from app.api.v1.ai_chat import router as ai_chat_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.diet import router as diet_router
from app.api.v1.exercise import router as exercise_router
from app.api.v1.health import router as health_router
from app.api.v1.profile import router as profile_router

api_router = APIRouter()
api_router.include_router(ai_chat_router)
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(diet_router)
api_router.include_router(exercise_router)
api_router.include_router(health_router)
api_router.include_router(profile_router)
