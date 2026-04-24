"""Logs routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_auth
from app.application.unit_of_work import SqlAlchemyUnitOfWork
from app.application.use_cases.logs import (
    ClearUpdateLogsUseCase,
    ClearVisitLogsUseCase,
    GetUpdateLogsUseCase,
    GetVisitLogsUseCase,
)
from app.database import get_db

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


@router.get("/visits")
async def get_visits(
    limit: int = 100,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get visit logs."""
    return await GetVisitLogsUseCase(SqlAlchemyUnitOfWork(db)).execute(limit)


@router.delete("/visits")
async def clear_visits(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Clear visit logs."""
    return await ClearVisitLogsUseCase(SqlAlchemyUnitOfWork(db)).execute()


@router.get("/updates")
async def get_updates(
    limit: int = 100,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get update logs."""
    return await GetUpdateLogsUseCase(SqlAlchemyUnitOfWork(db)).execute(limit)


@router.delete("/updates")
async def clear_updates(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Clear update logs."""
    return await ClearUpdateLogsUseCase(SqlAlchemyUnitOfWork(db)).execute()
