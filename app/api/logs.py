from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import Optional, List
from uuid import UUID
from datetime import date

from app.core.security import get_current_user, TokenData
from app.repositories.dev_log_repository import DevLogRepository
from app.services.dev_log_service import DevLogService
from app.schemas.dev_log import DevLogCreate, DevLogUpdate, DevLogResponse, DevLogList

router = APIRouter()


def get_service() -> DevLogService:
    repository = DevLogRepository()
    return DevLogService(repository)


@router.post("", response_model=DevLogResponse, status_code=201)
async def create_log(
    data: DevLogCreate,
    current_user: TokenData = Depends(get_current_user),
    service: DevLogService = Depends(get_service)
):
    """Create a new dev log entry."""
    return await service.create_log(current_user.user_id, data)


@router.get("", response_model=DevLogList)
async def get_logs(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    from_date: Optional[date] = Query(None, alias="from", description="Start date"),
    to_date: Optional[date] = Query(None, alias="to", description="End date"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    search: Optional[str] = Query(None, description="Search in title and summary"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: TokenData = Depends(get_current_user),
    service: DevLogService = Depends(get_service)
):
    """Get filtered and paginated logs."""
    return await service.get_logs(
        user_id=current_user.user_id,
        project_id=project_id,
        from_date=from_date,
        to_date=to_date,
        tags=tags,
        search=search,
        page=page,
        page_size=page_size
    )


@router.get("/export")
async def export_logs(
    format: str = Query("json", pattern="^(json|md)$", description="Export format"),
    project_id: Optional[UUID] = Query(None),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    current_user: TokenData = Depends(get_current_user),
    service: DevLogService = Depends(get_service)
):
    """Export logs as JSON or Markdown."""
    content = await service.export_logs(
        user_id=current_user.user_id,
        format=format,
        project_id=project_id,
        from_date=from_date,
        to_date=to_date
    )
    
    media_type = "application/json" if format == "json" else "text/markdown"
    filename = f"devlogs_export.{format}"
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{log_id}", response_model=DevLogResponse)
async def get_log(
    log_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    service: DevLogService = Depends(get_service)
):
    """Get a single log entry by ID."""
    log = await service.get_log(log_id, current_user.user_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.patch("/{log_id}", response_model=DevLogResponse)
async def update_log(
    log_id: UUID,
    data: DevLogUpdate,
    current_user: TokenData = Depends(get_current_user),
    service: DevLogService = Depends(get_service)
):
    """Update a log entry."""
    log = await service.update_log(log_id, current_user.user_id, data)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.delete("/{log_id}", status_code=204)
async def delete_log(
    log_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    service: DevLogService = Depends(get_service)
):
    """Delete a log entry."""
    deleted = await service.delete_log(log_id, current_user.user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Log not found")
