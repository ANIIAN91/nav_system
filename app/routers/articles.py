"""Articles routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_auth
from app.api.http import raise_http_error
from app.application.errors import ApplicationError
from app.application.unit_of_work import SqlAlchemyUnitOfWork
from app.application.use_cases.content import (
    CreateArticleUseCase,
    DeleteArticleUseCase,
    GetArticleUseCase,
    ListArticlesUseCase,
    UpdateArticleUseCase,
)
from app.database import get_db
from app.schemas.article import (
    ArticleDetailResponse,
    ArticleListResponse,
    ArticleMutationResponse,
    ArticleSyncRequest,
    ArticleUpdateRequest,
)

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])


@router.get("")
async def list_articles(
    current_user: str | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """Get article list filtered by login status."""
    return await ListArticlesUseCase(SqlAlchemyUnitOfWork(db)).execute(include_protected=current_user is not None)


@router.get("/{path:path}")
async def get_article(
    path: str,
    current_user: str | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleDetailResponse:
    """Get article content."""
    try:
        return await GetArticleUseCase(SqlAlchemyUnitOfWork(db)).execute(path, allow_protected=current_user is not None)
    except ApplicationError as exc:
        raise_http_error(exc)


@router.post("/sync")
async def sync_article(
    request: ArticleSyncRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ArticleMutationResponse:
    """Sync article content from external clients."""
    try:
        return await CreateArticleUseCase(SqlAlchemyUnitOfWork(db)).execute(
            path=request.path,
            content=request.content,
            title=request.title,
            frontmatter=request.frontmatter,
            username=username,
        )
    except ApplicationError as exc:
        raise_http_error(exc)


@router.put("/{path:path}")
async def update_article(
    path: str,
    request: ArticleUpdateRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ArticleMutationResponse:
    """Edit article content."""
    try:
        return await UpdateArticleUseCase(SqlAlchemyUnitOfWork(db)).execute(path, request.content, username)
    except ApplicationError as exc:
        raise_http_error(exc)


@router.delete("/{path:path}")
async def delete_article(
    path: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ArticleMutationResponse:
    """Delete article."""
    try:
        return await DeleteArticleUseCase(SqlAlchemyUnitOfWork(db)).execute(path, username)
    except ApplicationError as exc:
        raise_http_error(exc)
