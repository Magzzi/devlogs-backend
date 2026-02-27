from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import date

from app.core.security import get_current_user, TokenData
from app.repositories.dev_log_repository import DevLogRepository
from app.services.dev_log_service import DevLogService

router = APIRouter()


def get_service() -> DevLogService:
    repository = DevLogRepository()
    return DevLogService(repository)


@router.get("/dashboard")
async def get_dashboard_stats(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    current_user: TokenData = Depends(get_current_user),
    service: DevLogService = Depends(get_service)
):
    """Get dashboard statistics for the current user."""
    return await service.get_dashboard_stats(
        user_id=current_user.user_id,
        from_date=from_date,
        to_date=to_date
    )
