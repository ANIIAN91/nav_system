"""Logs routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.log import LogService
from app.routers.auth import require_auth

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])

@router.get("/visits")
async def get_visits(
    limit: int = 100,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get visit logs (requires login)"""
    service = LogService(db)
    return await service.get_visits(limit)

@router.delete("/visits")
async def clear_visits(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Clear visit logs (requires login)"""
    service = LogService(db)
    await service.clear_visits()
    await db.commit()
    return {"message": "访问记录已清空"}

@router.get("/updates")
async def get_updates(
    limit: int = 100,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get update logs (requires login)"""
    service = LogService(db)
    return await service.get_updates(limit)

@router.delete("/updates")
async def clear_updates(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Clear update logs (requires login)"""
    service = LogService(db)
    await service.clear_updates()
    await db.commit()
    return {"message": "更新记录已清空"}
