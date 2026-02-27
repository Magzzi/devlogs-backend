from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import date, datetime

from app.core.database import logs_db, projects_db


class DevLogRepository:
    def __init__(self):
        pass
    
    async def create(
        self,
        user_id: UUID,
        project_id: UUID,
        title: str,
        content_json: Dict[str, Any],
        log_date: date = None,
        tags: List[str] = None,
        visibility: str = "private"
    ) -> Dict[str, Any]:
        log = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "project_id": str(project_id),
            "title": title,
            "content_json": content_json,
            "log_date": (log_date or date.today()).isoformat(),
            "tags": tags or [],
            "visibility": visibility,
            "ai_summary": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        logs_db[log["id"]] = log
        return log
    
    async def get_by_id(self, log_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        log = logs_db.get(str(log_id))
        if log and log["user_id"] == str(user_id):
            # Attach project info
            project = projects_db.get(log["project_id"])
            if project:
                log["project"] = project
            return log
        return None
    
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
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get filtered and paginated logs."""
        # Filter by user
        user_logs = [
            log for log in logs_db.values()
            if log["user_id"] == str(user_id)
        ]
        
        # Apply filters
        if project_id:
            user_logs = [log for log in user_logs if log["project_id"] == str(project_id)]
        
        if from_date:
            user_logs = [log for log in user_logs if log["log_date"] >= from_date.isoformat()]
        
        if to_date:
            user_logs = [log for log in user_logs if log["log_date"] <= to_date.isoformat()]
        
        if tags:
            user_logs = [
                log for log in user_logs
                if any(tag in log.get("tags", []) for tag in tags)
            ]
        
        if search:
            search_lower = search.lower()
            user_logs = [
                log for log in user_logs
                if search_lower in log["title"].lower() or
                   search_lower in log["content_json"].get("summary", "").lower()
            ]
        
        total = len(user_logs)
        
        # Sort by log_date desc, then created_at desc
        user_logs.sort(key=lambda x: (x["log_date"], x["created_at"]), reverse=True)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_logs = user_logs[start_idx:end_idx]
        
        # Attach project info
        for log in paginated_logs:
            project = projects_db.get(log["project_id"])
            if project:
                log["project"] = project
        
        return paginated_logs, total
    
    async def get_logs_grouped_by_date(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get logs grouped by date for timeline view."""
        logs, _ = await self.get_logs(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            page_size=100
        )
        
        grouped = {}
        for log in logs:
            log_date = log["log_date"]
            if log_date not in grouped:
                grouped[log_date] = []
            grouped[log_date].append(log)
        
        return grouped
    
    async def update(self, log_id: UUID, user_id: UUID, **kwargs) -> Optional[Dict[str, Any]]:
        log = await self.get_by_id(log_id, user_id)
        if not log:
            return None
        
        for key, value in kwargs.items():
            if value is not None and key in ["title", "content_json", "log_date", "tags", "visibility", "project_id"]:
                if key == "log_date" and isinstance(value, date):
                    log[key] = value.isoformat()
                else:
                    log[key] = value
        
        log["updated_at"] = datetime.utcnow().isoformat()
        return log
    
    async def delete(self, log_id: UUID, user_id: UUID) -> bool:
        log = logs_db.get(str(log_id))
        if log and log["user_id"] == str(user_id):
            del logs_db[str(log_id)]
            return True
        return False
    
    async def get_stats(self, user_id: UUID, from_date: date, to_date: date) -> Dict[str, Any]:
        """Get statistics for dashboard."""
        user_logs = [
            log for log in logs_db.values()
            if log["user_id"] == str(user_id) and
               from_date.isoformat() <= log["log_date"] <= to_date.isoformat()
        ]
        
        log_count = len(user_logs)
        
        # Count active projects
        active_project_ids = set(log["project_id"] for log in user_logs)
        active_projects = len(active_project_ids)
        
        # Sum hours logged
        total_hours = sum(
            log["content_json"].get("time_spent_hours", 0)
            for log in user_logs
        )
        
        return {
            "logs_count": log_count,
            "active_projects": active_projects,
            "hours_logged": round(total_hours, 1)
        }
