import asyncio
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_supabase


class ProjectRepository:
    def __init__(self):
        self._sb = get_supabase()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _run(self, fn):
        """Run a synchronous supabase-py call in a thread so we don't block the event loop."""
        return asyncio.to_thread(fn)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = "#3B82F6",
    ):
        data = {
            "user_id": str(user_id),
            "name": name,
            "description": description,
            "color": color,
        }
        result = await self._run(
            lambda: self._sb.table("projects").insert(data).execute()
        )
        return result.data[0]

    async def get_by_id(self, project_id: UUID, user_id: UUID) -> Optional[dict]:
        result = await self._run(
            lambda: self._sb.table("projects")
            .select("*")
            .eq("id", str(project_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        return result.data

    async def get_all_by_user(self, user_id: UUID) -> List[dict]:
        result = await self._run(
            lambda: self._sb.table("projects")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data

    async def get_with_log_count(self, user_id: UUID) -> List[dict]:
        """Fetch projects with their dev_log count in a single query."""
        result = await self._run(
            lambda: self._sb.table("projects")
            .select("*, dev_logs(count)")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        projects = []
        for p in result.data:
            count_data = p.pop("dev_logs", [])
            log_count = count_data[0]["count"] if count_data else 0
            projects.append({**p, "log_count": log_count})
        return projects

    async def update(self, project_id: UUID, user_id: UUID, **kwargs) -> Optional[dict]:
        updates = {
            k: v
            for k, v in kwargs.items()
            if v is not None and k in ("name", "description", "color")
        }
        if not updates:
            return await self.get_by_id(project_id, user_id)
        updates["updated_at"] = datetime.utcnow().isoformat()
        result = await self._run(
            lambda: self._sb.table("projects")
            .update(updates)
            .eq("id", str(project_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def delete(self, project_id: UUID, user_id: UUID) -> bool:
        result = await self._run(
            lambda: self._sb.table("projects")
            .delete()
            .eq("id", str(project_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return len(result.data) > 0
