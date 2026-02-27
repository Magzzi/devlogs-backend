from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, timedelta
import json

from app.repositories.dev_log_repository import DevLogRepository
from app.schemas.dev_log import DevLogCreate, DevLogUpdate, DevLogResponse, DevLogList


class DevLogService:
    def __init__(self, repository: DevLogRepository):
        self.repository = repository
    
    async def create_log(self, user_id: UUID, data: DevLogCreate) -> DevLogResponse:
        log = await self.repository.create(
            user_id=user_id,
            project_id=data.project_id,
            title=data.title,
            content_json=data.content_json,
            log_date=data.log_date,
            tags=data.tags,
            visibility=data.visibility
        )
        
        project = log.get("project")
        return DevLogResponse(
            id=log["id"],
            user_id=log["user_id"],
            project_id=log["project_id"],
            log_date=log["log_date"],
            title=log["title"],
            content_json=log["content_json"],
            tags=log["tags"],
            visibility=log["visibility"],
            ai_summary=log["ai_summary"],
            created_at=log["created_at"],
            updated_at=log["updated_at"],
            project_name=project["name"] if project else None,
            project_color=project["color"] if project else None
        )
    
    async def get_log(self, log_id: UUID, user_id: UUID) -> Optional[DevLogResponse]:
        log = await self.repository.get_by_id(log_id, user_id)
        if not log:
            return None
        
        project = log.get("project")
        return DevLogResponse(
            id=log["id"],
            user_id=log["user_id"],
            project_id=log["project_id"],
            log_date=log["log_date"],
            title=log["title"],
            content_json=log["content_json"],
            tags=log["tags"],
            visibility=log["visibility"],
            ai_summary=log["ai_summary"],
            created_at=log["created_at"],
            updated_at=log["updated_at"],
            project_name=project["name"] if project else None,
            project_color=project["color"] if project else None
        )
    
    async def get_logs(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> DevLogList:
        logs, total = await self.repository.get_logs(
            user_id=user_id,
            project_id=project_id,
            from_date=from_date,
            to_date=to_date,
            tags=tags,
            search=search,
            page=page,
            page_size=page_size
        )
        
        items = [
            DevLogResponse(
                id=log["id"],
                user_id=log["user_id"],
                project_id=log["project_id"],
                log_date=log["log_date"],
                title=log["title"],
                content_json=log["content_json"],
                tags=log["tags"],
                visibility=log["visibility"],
                ai_summary=log["ai_summary"],
                created_at=log["created_at"],
                updated_at=log["updated_at"],
                project_name=log.get("project", {}).get("name"),
                project_color=log.get("project", {}).get("color")
            )
            for log in logs
        ]
        
        return DevLogList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total
        )
    
    async def update_log(
        self,
        log_id: UUID,
        user_id: UUID,
        data: DevLogUpdate
    ) -> Optional[DevLogResponse]:
        update_data = data.model_dump(exclude_unset=True)
        log = await self.repository.update(log_id, user_id, **update_data)
        
        if not log:
            return None
        
        project = log.get("project")
        return DevLogResponse(
            id=log["id"],
            user_id=log["user_id"],
            project_id=log["project_id"],
            log_date=log["log_date"],
            title=log["title"],
            content_json=log["content_json"],
            tags=log["tags"],
            visibility=log["visibility"],
            ai_summary=log["ai_summary"],
            created_at=log["created_at"],
            updated_at=log["updated_at"],
            project_name=project["name"] if project else None,
            project_color=project["color"] if project else None
        )
    
    async def delete_log(self, log_id: UUID, user_id: UUID) -> bool:
        return await self.repository.delete(log_id, user_id)
    
    async def get_dashboard_stats(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get dashboard statistics."""
        if not to_date:
            to_date = date.today()
        if not from_date:
            from_date = to_date - timedelta(days=7)
        
        current_stats = await self.repository.get_stats(user_id, from_date, to_date)
        
        # Get previous period stats for comparison
        period_length = (to_date - from_date).days
        prev_from = from_date - timedelta(days=period_length)
        prev_to = from_date - timedelta(days=1)
        prev_stats = await self.repository.get_stats(user_id, prev_from, prev_to)
        
        return {
            "logs_this_week": current_stats["logs_count"],
            "logs_change": current_stats["logs_count"] - prev_stats["logs_count"],
            "active_projects": current_stats["active_projects"],
            "hours_logged": current_stats["hours_logged"],
            "hours_change": round(current_stats["hours_logged"] - prev_stats["hours_logged"], 1)
        }
    
    async def export_logs(
        self,
        user_id: UUID,
        format: str = "json",
        project_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> str:
        """Export logs in specified format."""
        logs, _ = await self.repository.get_logs(
            user_id=user_id,
            project_id=project_id,
            from_date=from_date,
            to_date=to_date,
            page_size=1000
        )
        
        if format == "json":
            return json.dumps(
                [
                    {
                        "id": log["id"],
                        "date": log["log_date"],
                        "title": log["title"],
                        "project": log.get("project", {}).get("name"),
                        "content": log["content_json"],
                        "tags": log["tags"]
                    }
                    for log in logs
                ],
                indent=2
            )
        elif format == "md":
            lines = ["# Developer Logs Export\n"]
            current_date = None
            
            for log in logs:
                log_date = log["log_date"]
                if log_date != current_date:
                    current_date = log_date
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(log_date).date() if isinstance(log_date, str) else log_date
                    lines.append(f"\n## {date_obj.strftime('%B %d, %Y')}\n")
                
                lines.append(f"### {log['title']}")
                project = log.get("project")
                lines.append(f"**Project:** {project['name'] if project else 'N/A'}")
                
                if log["content_json"].get("summary"):
                    lines.append(f"\n{log['content_json']['summary']}\n")
                
                if log["content_json"].get("tasks_completed"):
                    lines.append("**Tasks Completed:**")
                    for task in log["content_json"]["tasks_completed"]:
                        lines.append(f"- {task}")
                
                if log["tags"]:
                    lines.append(f"\n*Tags: {', '.join(log['tags'])}*\n")
                
                lines.append("---\n")
            
            return "\n".join(lines)
        
        raise ValueError(f"Unsupported export format: {format}")
