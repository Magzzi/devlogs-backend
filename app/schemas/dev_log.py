from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date


class DevLogContentJson(BaseModel):
    """Structured content for a dev log entry."""
    summary: str = Field(..., description="Brief summary of what was done")
    tasks_completed: List[str] = Field(default=[], description="List of completed tasks")
    blockers: List[str] = Field(default=[], description="Any blockers encountered")
    learning: Optional[str] = Field(None, description="Key learnings from the day")
    commits: List[str] = Field(default=[], description="Related commit hashes")
    time_spent_hours: Optional[float] = Field(None, ge=0, le=24, description="Hours spent")
    notes: Optional[str] = Field(None, description="Additional notes")


class DevLogBase(BaseModel):
    project_id: UUID
    log_date: date = Field(default_factory=date.today)
    title: str = Field(..., min_length=1, max_length=255)
    content_json: Dict[str, Any] = Field(default={})
    tags: List[str] = Field(default=[])
    visibility: str = Field(default="private", pattern="^(private|team|public)$")


class DevLogCreate(DevLogBase):
    pass


class DevLogUpdate(BaseModel):
    project_id: Optional[UUID] = None
    log_date: Optional[date] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content_json: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    visibility: Optional[str] = Field(None, pattern="^(private|team|public)$")


class DevLogResponse(DevLogBase):
    id: UUID
    user_id: UUID
    ai_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    project_name: Optional[str] = None
    project_color: Optional[str] = None
    
    class Config:
        from_attributes = True


class DevLogList(BaseModel):
    items: List[DevLogResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
