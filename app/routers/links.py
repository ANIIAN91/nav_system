"""Links routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_auth
from app.api.http import raise_http_error
from app.application.errors import ApplicationError
from app.application.unit_of_work import SqlAlchemyUnitOfWork
from app.application.use_cases.navigation import (
    AddLinkUseCase,
    BatchReorderLinksUseCase,
    DeleteLinkUseCase,
    ExportNavigationUseCase,
    ImportNavigationUseCase,
    ListNavigationUseCase,
    ReorderLinkUseCase,
    UpdateLinkUseCase,
)
from app.database import get_db
from app.schemas.link import BatchReorderRequest, ImportRequest, LinkCreate, LinkUpdate, ReorderRequest

router = APIRouter(prefix="/api/v1/links", tags=["links"])


@router.get("")
async def get_links(
    current_user: str | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get navigation links filtered by login state."""
    return await ListNavigationUseCase(SqlAlchemyUnitOfWork(db)).execute(include_private=current_user is not None)


@router.post("")
async def add_link(
    category_name: str,
    link: LinkCreate,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Add a navigation link."""
    try:
        return await AddLinkUseCase(SqlAlchemyUnitOfWork(db)).execute(
            category_name=category_name,
            title=link.title,
            url=link.url,
            icon=link.icon,
            username=username,
        )
    except ApplicationError as exc:
        raise_http_error(exc)


@router.put("/{link_id}")
async def update_link(
    link_id: str,
    link: LinkUpdate,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update a navigation link."""
    try:
        return await UpdateLinkUseCase(SqlAlchemyUnitOfWork(db)).execute(
            link_id=link_id,
            title=link.title,
            url=link.url,
            icon=link.icon,
            category=link.category,
            username=username,
        )
    except ApplicationError as exc:
        raise_http_error(exc)


@router.delete("/{link_id}")
async def delete_link(
    link_id: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete a navigation link."""
    try:
        return await DeleteLinkUseCase(SqlAlchemyUnitOfWork(db)).execute(link_id, username)
    except ApplicationError as exc:
        raise_http_error(exc)


@router.post("/{link_id}/reorder")
async def reorder_link(
    link_id: str,
    request: ReorderRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Reorder a link."""
    return await ReorderLinkUseCase(SqlAlchemyUnitOfWork(db)).execute(link_id, request.direction)


@router.post("/reorder/batch")
async def batch_reorder_links(
    request: BatchReorderRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Batch reorder links."""
    try:
        return await BatchReorderLinksUseCase(SqlAlchemyUnitOfWork(db)).execute(request.ids)
    except ApplicationError as exc:
        raise_http_error(exc)


@router.get("/export")
async def export_links(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Export navigation data."""
    return await ExportNavigationUseCase(SqlAlchemyUnitOfWork(db)).execute()


@router.post("/import")
async def import_links(
    request: ImportRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Import navigation data."""
    try:
        return await ImportNavigationUseCase(SqlAlchemyUnitOfWork(db)).execute(request.data, request.format, username)
    except ApplicationError as exc:
        raise_http_error(exc)
