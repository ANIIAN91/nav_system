"""Log service"""
from datetime import datetime
from typing import List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VisitLog, UpdateLog
from app.config import get_settings

settings = get_settings()

class LogService:
    """Service for managing logs"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_visit(self, ip: str, path: str, user_agent: str = ""):
        """Record a visit"""
        log = VisitLog(ip=ip, path=path, user_agent=user_agent)
        self.db.add(log)
        await self._cleanup_old_visits()

    async def get_visits(self, limit: int = 100) -> dict:
        """Get visit logs"""
        result = await self.db.execute(
            select(VisitLog).order_by(VisitLog.created_at.desc()).limit(limit)
        )
        visits = result.scalars().all()
        total = await self._count_visits()
        return {
            "visits": [
                {
                    "ip": v.ip,
                    "path": v.path,
                    "user_agent": v.user_agent,
                    "time": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else ""
                }
                for v in visits
            ],
            "total": total
        }

    async def clear_visits(self):
        """Clear all visit logs"""
        await self.db.execute(delete(VisitLog))

    async def record_update(self, action: str, target_type: str, target_name: str,
                           details: str = "", username: str = ""):
        """Record an update"""
        log = UpdateLog(
            action=action,
            target_type=target_type,
            target_name=target_name,
            details=details,
            username=username
        )
        self.db.add(log)
        await self._cleanup_old_updates()

    async def get_updates(self, limit: int = 100) -> dict:
        """Get update logs"""
        result = await self.db.execute(
            select(UpdateLog).order_by(UpdateLog.created_at.desc()).limit(limit)
        )
        updates = result.scalars().all()
        total = await self._count_updates()
        return {
            "updates": [
                {
                    "action": u.action,
                    "target_type": u.target_type,
                    "target_name": u.target_name,
                    "details": u.details,
                    "username": u.username,
                    "time": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else ""
                }
                for u in updates
            ],
            "total": total
        }

    async def clear_updates(self):
        """Clear all update logs"""
        await self.db.execute(delete(UpdateLog))

    async def _count_visits(self) -> int:
        """Count total visits"""
        from sqlalchemy import func
        result = await self.db.execute(select(func.count(VisitLog.id)))
        return result.scalar() or 0

    async def _count_updates(self) -> int:
        """Count total updates"""
        from sqlalchemy import func
        result = await self.db.execute(select(func.count(UpdateLog.id)))
        return result.scalar() or 0

    async def _cleanup_old_visits(self):
        """Cleanup old visit logs if exceeding max"""
        count = await self._count_visits()
        if count > settings.max_visit_records:
            # Delete oldest records
            subquery = select(VisitLog.id).order_by(VisitLog.created_at.desc()).limit(settings.max_visit_records)
            await self.db.execute(delete(VisitLog).where(VisitLog.id.not_in(subquery)))

    async def _cleanup_old_updates(self):
        """Cleanup old update logs if exceeding max"""
        count = await self._count_updates()
        if count > settings.max_update_records:
            subquery = select(UpdateLog.id).order_by(UpdateLog.created_at.desc()).limit(settings.max_update_records)
            await self.db.execute(delete(UpdateLog).where(UpdateLog.id.not_in(subquery)))
