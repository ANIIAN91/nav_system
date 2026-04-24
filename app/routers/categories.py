"""Categories routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_auth
from app.api.http import raise_http_error
from app.application.errors import ApplicationError
from app.application.unit_of_work import SqlAlchemyUnitOfWork
from app.application.use_cases.navigation import (
    BatchReorderCategoriesUseCase,
    CreateCategoryUseCase,
    DeleteCategoryUseCase,
    UpdateCategoryUseCase,
)
from app.database import get_db
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.link import BatchReorderRequest

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.post("")
async def add_category(
    category: CategoryCreate,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Add a category."""
    try:
        return await CreateCategoryUseCase(SqlAlchemyUnitOfWork(db)).execute(
            name=category.name,
            auth_required=category.auth_required,
            username=username,
        )
    except ApplicationError as exc:
        raise_http_error(exc)


@router.put("/{category_name}")
async def update_category(
    category_name: str,
    category: CategoryUpdate,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update a category."""
    try:
        return await UpdateCategoryUseCase(SqlAlchemyUnitOfWork(db)).execute(
            category_name=category_name,
            new_name=category.name,
            auth_required=category.auth_required,
            username=username,
        )
    except ApplicationError as exc:
        raise_http_error(exc)


@router.delete("/{category_name}")
async def delete_category(
    category_name: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete a category."""
    try:
        return await DeleteCategoryUseCase(SqlAlchemyUnitOfWork(db)).execute(category_name, username)
    except ApplicationError as exc:
        raise_http_error(exc)


@router.post("/reorder/batch")
async def batch_reorder_categories(
    request: BatchReorderRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Batch reorder categories."""
    try:
        return await BatchReorderCategoriesUseCase(SqlAlchemyUnitOfWork(db)).execute(request.ids)
    except ApplicationError as exc:
        raise_http_error(exc)
