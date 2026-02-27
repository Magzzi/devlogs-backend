# In-memory database for demo purposes
from typing import Dict, List, Any
from datetime import datetime, date
import uuid

# Mock in-memory storage
projects_db: Dict[str, Dict[str, Any]] = {}
logs_db: Dict[str, Dict[str, Any]] = {}


def init_mock_data():
    """Initialize with some mock data."""
    mock_user_id = "00000000-0000-0000-0000-000000000123"
    
    # Create mock projects
    project1 = {
        "id": str(uuid.uuid4()),
        "user_id": mock_user_id,
        "name": "devlogs-api",
        "description": "Backend API for DevLogs application",
        "color": "#3B82F6",
        "created_at": datetime(2026, 1, 15).isoformat(),
        "updated_at": datetime(2026, 1, 15).isoformat(),
    }
    project2 = {
        "id": str(uuid.uuid4()),
        "user_id": mock_user_id,
        "name": "auth-service",
        "description": "Authentication and authorization microservice",
        "color": "#22C55E",
        "created_at": datetime(2026, 2, 1).isoformat(),
        "updated_at": datetime(2026, 2, 1).isoformat(),
    }
    project3 = {
        "id": str(uuid.uuid4()),
        "user_id": mock_user_id,
        "name": "dashboard-ui",
        "description": "Frontend dashboard built with Next.js",
        "color": "#F59E0B",
        "created_at": datetime(2026, 1, 20).isoformat(),
        "updated_at": datetime(2026, 1, 20).isoformat(),
    }
    
    projects_db[project1["id"]] = project1
    projects_db[project2["id"]] = project2
    projects_db[project3["id"]] = project3
    
    # Create mock logs (using recent dates around Feb 25, 2026)
    log1 = {
        "id": str(uuid.uuid4()),
        "user_id": mock_user_id,
        "project_id": project2["id"],
        "log_date": "2026-02-25",
        "title": "Implement JWT refresh token rotation",
        "content_json": {
            "summary": "Added automatic token rotation with sliding window expiry. Updated middleware to handle refresh flow gracefully.",
            "tasks_completed": ["JWT login", "Refresh token rotation", "Protected routes"],
            "blockers": [],
            "learning": "Token rotation patterns",
            "commits": ["a1b2c3"],
            "time_spent_hours": 3.33,
        },
        "tags": ["auth", "security"],
        "visibility": "private",
        "ai_summary": None,
        "created_at": datetime(2026, 2, 25, 14, 45).isoformat(),
        "updated_at": datetime(2026, 2, 25, 14, 45).isoformat(),
    }
    
    log2 = {
        "id": str(uuid.uuid4()),
        "user_id": mock_user_id,
        "project_id": project1["id"],
        "log_date": "2026-02-24",
        "title": "Fix pagination offset bug in /logs endpoint",
        "content_json": {
            "summary": "Off-by-one error in cursor-based pagination. Added regression test covering edge cases with empty result sets.",
            "tasks_completed": ["Fixed pagination bug", "Added regression tests"],
            "blockers": [],
            "learning": "Cursor pagination edge cases",
            "commits": ["d4e5f6"],
            "time_spent_hours": 1.17,
        },
        "tags": ["bugfix", "api"],
        "visibility": "private",
        "ai_summary": None,
        "created_at": datetime(2026, 2, 24, 11, 30).isoformat(),
        "updated_at": datetime(2026, 2, 24, 11, 30).isoformat(),
    }
    
    log3 = {
        "id": str(uuid.uuid4()),
        "user_id": mock_user_id,
        "project_id": project3["id"],
        "log_date": "2026-02-23",
        "title": "Dashboard stats component refactoring",
        "content_json": {
            "summary": "Refactored dashboard statistics components for better reusability. Added loading states and error handling.",
            "tasks_completed": ["Stats card component", "Loading skeletons", "Error boundaries"],
            "blockers": [],
            "commits": ["g7h8i9"],
            "time_spent_hours": 4.5,
        },
        "tags": ["refactor", "frontend"],
        "visibility": "private",
        "ai_summary": None,
        "created_at": datetime(2026, 2, 23, 16, 20).isoformat(),
        "updated_at": datetime(2026, 2, 23, 16, 20).isoformat(),
    }
    
    logs_db[log1["id"]] = log1
    logs_db[log2["id"]] = log2
    logs_db[log3["id"]] = log3


# Initialize mock data on module load
init_mock_data()
