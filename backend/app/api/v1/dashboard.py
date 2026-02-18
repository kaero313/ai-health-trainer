from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import TodayDashboardResponse, WeeklyDashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/today", response_model=TodayDashboardResponse)
async def get_today_dashboard(
    target_date: date | None = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TodayDashboardResponse:
    resolved_target_date = target_date or date_today()
    service = DashboardService(db)
    data = await service.get_today(current_user.id, resolved_target_date)
    return TodayDashboardResponse(data=data)


@router.get("/weekly", response_model=WeeklyDashboardResponse)
async def get_weekly_dashboard(
    week_start: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WeeklyDashboardResponse:
    resolved_week_start = week_start or monday_of_current_week()
    service = DashboardService(db)
    data = await service.get_weekly(current_user.id, resolved_week_start)
    return WeeklyDashboardResponse(data=data)


def date_today() -> date:
    return date.today()


def monday_of_current_week() -> date:
    today = date_today()
    return today - timedelta(days=today.weekday())
