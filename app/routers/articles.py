"""Articles routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user, require_auth
from app.schemas.article import (
    ArticleDetailResponse,
    ArticleListResponse,
    ArticleMutationResponse,
    ArticleSyncRequest,
    ArticleUpdateRequest,
)
from app.services.articles import ArticleAuthenticationRequiredError, ArticleService
from app.services.log import LogService
from app.services.settings import SettingsService

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])


@router.get("")
async def list_articles(
    current_user: Optional[str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """Get article list filtered by login status."""
    site_settings = await SettingsService(db).get_public_settings()
    articles = await ArticleService().list_articles_async(
        protected_paths=site_settings.get("protected_article_paths", []),
        include_protected=current_user is not None,
    )
    return {"articles": articles}


@router.get("/{path:path}")
async def get_article(
    path: str,
    current_user: Optional[str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleDetailResponse:
    """Get article content."""
    site_settings = await SettingsService(db).get_public_settings()
    try:
        return await ArticleService().get_article_async(
            path,
            protected_paths=site_settings.get("protected_article_paths", []),
            allow_protected=current_user is not None,
        )
    except ArticleAuthenticationRequiredError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sync")
async def sync_article(
    request: ArticleSyncRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ArticleMutationResponse:
    """Sync article content from external clients."""
    try:
        result = await ArticleService().sync_article_async(
            path=request.path,
            content=request.content,
            title=request.title,
            frontmatter=request.frontmatter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    log_service = LogService(db)
    await log_service.record_update("add", "article", result["title"] or "", f"路径: {result['path']}", username)
    await db.commit()
    return result


@router.put("/{path:path}")
async def update_article(
    path: str,
    request: ArticleUpdateRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ArticleMutationResponse:
    """Edit article content."""
    try:
        result = await ArticleService().update_article_async(path, request.content)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_service = LogService(db)
    await log_service.record_update("update", "article", result["title"], f"路径: {result['path']}", username)
    await db.commit()
    return {"message": "文章已更新", "path": result["path"], "title": result["title"]}


@router.delete("/{path:path}")
async def delete_article(
    path: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ArticleMutationResponse:
    """Delete article."""
    try:
        result = await ArticleService().delete_article_async(path)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_service = LogService(db)
    await log_service.record_update("delete", "article", result["title"], f"路径: {result['path']}", username)
    await db.commit()
    return {"message": "文章已删除", "path": result["path"], "title": result["title"]}
