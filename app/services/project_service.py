from typing import List, Optional
from uuid import UUID

from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectList


class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository
    
    async def create_project(self, user_id: UUID, data: ProjectCreate) -> ProjectResponse:
        project = await self.repository.create(
            user_id=user_id,
            name=data.name,
            description=data.description,
            color=data.color
        )
        return ProjectResponse(
            id=project["id"],
            user_id=project["user_id"],
            name=project["name"],
            description=project["description"],
            color=project["color"],
            created_at=project["created_at"],
            updated_at=project["updated_at"],
            log_count=0
        )
    
    async def get_project(self, project_id: UUID, user_id: UUID) -> Optional[ProjectResponse]:
        project = await self.repository.get_by_id(project_id, user_id)
        if not project:
            return None
        
        return ProjectResponse(
            id=project["id"],
            user_id=project["user_id"],
            name=project["name"],
            description=project["description"],
            color=project["color"],
            created_at=project["created_at"],
            updated_at=project["updated_at"]
        )
    
    async def get_all_projects(self, user_id: UUID) -> ProjectList:
        projects_with_counts = await self.repository.get_with_log_count(user_id)
        
        items = [
            ProjectResponse(
                id=p["id"],
                user_id=p["user_id"],
                name=p["name"],
                description=p["description"],
                color=p["color"],
                created_at=p["created_at"],
                updated_at=p["updated_at"],
                log_count=p["log_count"]
            )
            for p in projects_with_counts
        ]
        
        return ProjectList(items=items, total=len(items))
    
    async def update_project(
        self,
        project_id: UUID,
        user_id: UUID,
        data: ProjectUpdate
    ) -> Optional[ProjectResponse]:
        update_data = data.model_dump(exclude_unset=True)
        project = await self.repository.update(project_id, user_id, **update_data)
        
        if not project:
            return None
        
        return ProjectResponse(
            id=project["id"],
            user_id=project["user_id"],
            name=project["name"],
            description=project["description"],
            color=project["color"],
            created_at=project["created_at"],
            updated_at=project["updated_at"]
        )
    
    async def delete_project(self, project_id: UUID, user_id: UUID) -> bool:
        return await self.repository.delete(project_id, user_id)
