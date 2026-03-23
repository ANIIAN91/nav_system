"""Log service."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import UpdateLog, VisitLog

settings = get_settings()


class LogService:
    """Service for managing logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_visit(self, ip: str, path: str, user_agent: str = "") -> None:
        """Record a visit."""
        self.db.add(VisitLog(ip=ip, path=path, user_agent=user_agent))

    async def get_visits(self, limit: int = 100) -> dict:
        """Get visit logs."""
        result = await self.db.execute(
            select(VisitLog).order_by(VisitLog.created_at.desc()).limit(limit)
        )
        visits = result.scalars().all()
        total = await self._count_visits()
        return {
            "visits": [
                {
                    "ip": visit.ip,
                    "path": visit.path,
                    "user_agent": visit.user_agent,
                    "time": visit.created_at.strftime("%Y-%m-%d %H:%M:%S") if visit.created_at else "",
                }
                for visit in visits
            ],
            "total": total,
        }

    async def clear_visits(self) -> None:
        """Clear all visit logs."""
        await self.db.execute(delete(VisitLog))

    async def record_update(
        self,
        action: str,
        target_type: str,
        target_name: str,
        details: str = "",
        username: str = "",
    ) -> None:
        """Record an update."""
        self.db.add(
            UpdateLog(
                action=action,
                target_type=target_type,
                target_name=target_name,
                details=details,
                username=username,
            )
        )

    async def get_updates(self, limit: int = 100) -> dict:
        """Get update logs."""
        result = await self.db.execute(
            select(UpdateLog).order_by(UpdateLog.created_at.desc()).limit(limit)
        )
        updates = result.scalars().all()
        total = await self._count_updates()
        return {
            "updates": [
                {
                    "action": update.action,
                    "target_type": update.target_type,
                    "target_name": update.target_name,
                    "details": update.details,
                    "username": update.username,
                    "time": update.created_at.strftime("%Y-%m-%d %H:%M:%S") if update.created_at else "",
                }
                for update in updates
            ],
            "total": total,
        }

    async def clear_updates(self) -> None:
        """Clear all update logs."""
        await self.db.execute(delete(UpdateLog))

    async def cleanup_old_visits(self, max_records: int | None = None) -> int:
        """Keep only the newest visit logs."""
        keep_count = max_records if max_records is not None else settings.max_visit_records
        count = await self._count_visits()
        if count <= keep_count:
            return 0

        delete_count = count - keep_count
        subquery = (
            select(VisitLog.id)
            .order_by(VisitLog.created_at.asc(), VisitLog.id.asc())
            .limit(delete_count)
        )
        result = await self.db.execute(delete(VisitLog).where(VisitLog.id.in_(subquery)))
        return result.rowcount or 0

    async def cleanup_old_updates(self, max_records: int | None = None) -> int:
        """Keep only the newest update logs."""
        keep_count = max_records if max_records is not None else settings.max_update_records
        count = await self._count_updates()
        if count <= keep_count:
            return 0

        delete_count = count - keep_count
        subquery = (
            select(UpdateLog.id)
            .order_by(UpdateLog.created_at.asc(), UpdateLog.id.asc())
            .limit(delete_count)
        )
        result = await self.db.execute(delete(UpdateLog).where(UpdateLog.id.in_(subquery)))
        return result.rowcount or 0

    async def _count_visits(self) -> int:
        """Count total visits."""
        from sqlalchemy import func

        result = await self.db.execute(select(func.count(VisitLog.id)))
        return result.scalar() or 0

    async def _count_updates(self) -> int:
        """Count total updates."""
        from sqlalchemy import func

        result = await self.db.execute(select(func.count(UpdateLog.id)))
        return result.scalar() or 0

    async def cleanup_logs(
        self,
        max_visits: int | None = None,
        max_updates: int | None = None,
    ) -> dict[str, int]:
        """Run both retention policies and report deleted and remaining counts."""
        deleted_visits = await self.cleanup_old_visits(max_visits)
        deleted_updates = await self.cleanup_old_updates(max_updates)
        remaining_visits = await self._count_visits()
        remaining_updates = await self._count_updates()
        return {
            "deleted_visits": deleted_visits,
            "deleted_updates": deleted_updates,
            "remaining_visits": remaining_visits,
            "remaining_updates": remaining_updates,
        }


async def run_log_cleanup_job(session_factory, max_visits: int | None = None, max_updates: int | None = None) -> dict[str, int]:
    """Run a full log cleanup cycle using the provided async session factory."""
    async with session_factory() as db:
        summary = await LogService(db).cleanup_logs(max_visits=max_visits, max_updates=max_updates)
        await db.commit()
        return summary
