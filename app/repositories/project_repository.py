from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from app.core.database import projects_db, logs_db


class ProjectRepository:
    def __init__(self):
        pass
    
    async def create(self, user_id: UUID, name: str, description: Optional[str] = None, color: Optional[str] = "#3B82F6") -> Dict[str, Any]:
        project = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "name": name,
            "description": description,
            "color": color,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        projects_db[project["id"]] = project
        return project
    
    async def get_by_id(self, project_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        project = projects_db.get(str(project_id))
        if project and project["user_id"] == str(user_id):
            return project
        return None
    
    async def get_all_by_user(self, user_id: UUID) -> List[Dict[str, Any]]:
        user_projects = [
            p for p in projects_db.values()
            if p["user_id"] == str(user_id)
        ]
        # Sort by created_at descending
        user_projects.sort(key=lambda x: x["created_at"], reverse=True)
        return user_projects
    
    async def get_with_log_count(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all projects with their log counts."""
        user_projects = await self.get_all_by_user(user_id)
        
        result = []
        for project in user_projects:
            log_count = sum(
                1 for log in logs_db.values()
                if log["project_id"] == project["id"]
            )
            result.append({
                **project,
                "log_count": log_count
            })
        
        return result
    
    async def update(self, project_id: UUID, user_id: UUID, **kwargs) -> Optional[Dict[str, Any]]:
        project = await self.get_by_id(project_id, user_id)
        if not project:
            return None
        
        for key, value in kwargs.items():
            if value is not None and key in ["name", "description", "color"]:
                project[key] = value
        
        project["updated_at"] = datetime.utcnow().isoformat()
        return project
    
    async def delete(self, project_id: UUID, user_id: UUID) -> bool:
        project = await self.get_by_id(project_id, user_id)
        if not project:
            return False
        
        del projects_db[str(project_id)]
        return True
