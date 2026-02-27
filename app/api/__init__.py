# API module - FastAPI routes
from fastapi import APIRouter
from app.api.logs import router as logs_router
from app.api.projects import router as projects_router
from app.api.stats import router as stats_router

router = APIRouter()

router.include_router(logs_router, prefix="/logs", tags=["logs"])
router.include_router(projects_router, prefix="/projects", tags=["projects"])
router.include_router(stats_router, prefix="/stats", tags=["stats"])
