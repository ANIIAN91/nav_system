"""Folders routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_auth
from app.api.http import raise_http_error
from app.application.errors import ApplicationError
from app.application.unit_of_work import SqlAlchemyUnitOfWork
from app.application.use_cases.content import (
    CreateFolderUseCase,
    DeleteFolderUseCase,
    ListFoldersUseCase,
    RenameFolderUseCase,
)
from app.database import get_db
from app.schemas.folder import FolderListResponse, FolderRenameRequest

router = APIRouter(prefix="/api/v1/folders", tags=["folders"])


@router.get("")
async def list_folders(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> FolderListResponse:
    """Get article folders list."""
    return await ListFoldersUseCase(SqlAlchemyUnitOfWork(db)).execute()


@router.post("")
async def create_folder(
    name: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create article folder."""
    try:
        return await CreateFolderUseCase(SqlAlchemyUnitOfWork(db)).execute(name, username)
    except ApplicationError as exc:
        raise_http_error(exc)


@router.put("/{name:path}")
async def rename_folder(
    name: str,
    request: FolderRenameRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Rename article folder."""
    try:
        return await RenameFolderUseCase(SqlAlchemyUnitOfWork(db)).execute(name, request.new_name, username)
    except ApplicationError as exc:
        raise_http_error(exc)


@router.delete("/{name:path}")
async def delete_folder(
    name: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete article folder including all articles."""
    try:
        return await DeleteFolderUseCase(SqlAlchemyUnitOfWork(db)).execute(name, username)
    except ApplicationError as exc:
        raise_http_error(exc)
