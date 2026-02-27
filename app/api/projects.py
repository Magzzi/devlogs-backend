from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from app.core.security import get_current_user, TokenData
from app.repositories.project_repository import ProjectRepository
from app.services.project_service import ProjectService
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectList

router = APIRouter()


def get_service() -> ProjectService:
    repository = ProjectRepository()
    return ProjectService(repository)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    current_user: TokenData = Depends(get_current_user),
    service: ProjectService = Depends(get_service)
):
    """Create a new project."""
    return await service.create_project(current_user.user_id, data)


@router.get("", response_model=ProjectList)
async def get_projects(
    current_user: TokenData = Depends(get_current_user),
    service: ProjectService = Depends(get_service)
):
    """Get all projects for the current user."""
    return await service.get_all_projects(current_user.user_id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    service: ProjectService = Depends(get_service)
):
    """Get a single project by ID."""
    project = await service.get_project(project_id, current_user.user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    current_user: TokenData = Depends(get_current_user),
    service: ProjectService = Depends(get_service)
):
    """Update a project."""
    project = await service.update_project(project_id, current_user.user_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    service: ProjectService = Depends(get_service)
):
    """Delete a project and all its logs."""
    deleted = await service.delete_project(project_id, current_user.user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
