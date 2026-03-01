import asyncio
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import date, datetime

from app.core.database import get_supabase


class DevLogRepository:
    def __init__(self):
        self._sb = get_supabase()

    def _run(self, fn):
        return asyncio.to_thread(fn)

    async def create(
        self,
        user_id: UUID,
        project_id: UUID,
        title: str,
        content_json: Dict[str, Any],
        log_date: date = None,
        tags: List[str] = None,
        visibility: str = "private",
    ) -> Dict[str, Any]:
        data = {
            "user_id": str(user_id),
            "project_id": str(project_id),
            "title": title,
            "content_json": content_json,
            "log_date": (log_date or date.today()).isoformat(),
            "tags": tags or [],
            "visibility": visibility,
        }
        result = await self._run(
            lambda: self._sb.table("dev_logs").insert(data).execute()
        )
        return result.data[0]

    async def get_by_id(self, log_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        result = await self._run(
            lambda: self._sb.table("dev_logs")
            .select("*, projects(*)")
            .eq("id", str(log_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        if not result.data:
            return None
        log = result.data
        if "projects" in log:
            log["project"] = log.pop("projects")
        return log

    async def get_logs(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        def _query():
            q = (
                self._sb.table("dev_logs")
                .select("*, projects(*)", count="exact")
                .eq("user_id", str(user_id))
            )
            if project_id:
                q = q.eq("project_id", str(project_id))
            if from_date:
                q = q.gte("log_date", from_date.isoformat())
            if to_date:
                q = q.lte("log_date", to_date.isoformat())
            q = q.order("log_date", desc=True).order("created_at", desc=True)
            return q.execute()

        result = await self._run(_query)
        logs = result.data

        # Rename nested project key
        for log in logs:
            if "projects" in log:
                log["project"] = log.pop("projects")

        # Python-side filters (tags / full-text search)
        if tags:
            logs = [lg for lg in logs if any(t in lg.get("tags", []) for t in tags)]
        if search:
            s = search.lower()
            logs = [
                lg for lg in logs
                if s in lg["title"].lower()
                or s in (lg.get("content_json") or {}).get("summary", "").lower()
            ]

        total = len(logs)
        start = (page - 1) * page_size
        return logs[start : start + page_size], total

    async def get_logs_grouped_by_date(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        logs, _ = await self.get_logs(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            page_size=100,
        )
        grouped: Dict[str, List] = {}
        for log in logs:
            key = log["log_date"]
            grouped.setdefault(key, []).append(log)
        return grouped

    async def update(self, log_id: UUID, user_id: UUID, **kwargs) -> Optional[Dict[str, Any]]:
        updatable = ("title", "content_json", "log_date", "tags", "visibility", "project_id")
        updates = {}
        for key, value in kwargs.items():
            if value is not None and key in updatable:
                updates[key] = value.isoformat() if key == "log_date" and isinstance(value, date) else value
        if not updates:
            return await self.get_by_id(log_id, user_id)
        updates["updated_at"] = datetime.utcnow().isoformat()
        result = await self._run(
            lambda: self._sb.table("dev_logs")
            .update(updates)
            .eq("id", str(log_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def delete(self, log_id: UUID, user_id: UUID) -> bool:
        result = await self._run(
            lambda: self._sb.table("dev_logs")
            .delete()
            .eq("id", str(log_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return len(result.data) > 0

    async def get_stats(
        self, user_id: UUID, from_date: date, to_date: date
    ) -> Dict[str, Any]:
        result = await self._run(
            lambda: self._sb.table("dev_logs")
            .select("project_id, content_json")
            .eq("user_id", str(user_id))
            .gte("log_date", from_date.isoformat())
            .lte("log_date", to_date.isoformat())
            .execute()
        )
        logs = result.data
        active_projects = len({lg["project_id"] for lg in logs})
        total_hours = sum(
            (lg.get("content_json") or {}).get("time_spent_hours", 0) for lg in logs
        )
        return {
            "logs_count": len(logs),
            "active_projects": active_projects,
            "hours_logged": round(total_hours, 1),
        }
