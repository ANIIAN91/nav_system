"""Articles routes"""
from pathlib import Path
from typing import Optional, List

import markdown
import yaml
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.setting import ArticleSyncRequest, ArticleUpdateRequest
from app.services.log import LogService
from app.routers.auth import get_current_user, require_auth
from app.routers.settings import get_site_settings

router = APIRouter(prefix="/api/articles", tags=["articles"])
settings = get_settings()

def is_path_protected(path: str, protected_paths: List[str]) -> bool:
    """Check if path is in protected directories"""
    path_parts = Path(path).parts
    for protected in protected_paths:
        protected_parts = Path(protected).parts
        if len(path_parts) >= len(protected_parts):
            if path_parts[:len(protected_parts)] == protected_parts:
                return True
    return False

@router.get("")
async def list_articles(
    current_user: Optional[str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get article list (filtered by login status)"""
    site_settings = await get_site_settings(db)
    protected_paths = site_settings.get("protected_article_paths", [])

    articles = []
    if settings.articles_dir.exists():
        for path in settings.articles_dir.rglob("*.md"):
            rel_path = path.relative_to(settings.articles_dir)
            rel_path_str = str(rel_path)

            if current_user is None and is_path_protected(rel_path_str, protected_paths):
                continue

            stat = path.stat()
            articles.append({
                "path": rel_path_str,
                "title": path.stem,
                "category": str(rel_path.parent) if rel_path.parent != Path(".") else None,
                "protected": is_path_protected(rel_path_str, protected_paths),
                "created_time": stat.st_mtime
            })

    articles.sort(key=lambda x: x["created_time"], reverse=True)
    return {"articles": articles}

@router.get("/{path:path}")
async def get_article(
    path: str,
    current_user: Optional[str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get article content"""
    article_path = (settings.articles_dir / path).resolve()
    if not str(article_path).startswith(str(settings.articles_dir.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问")

    site_settings = await get_site_settings(db)
    protected_paths = site_settings.get("protected_article_paths", [])
    if current_user is None and is_path_protected(path, protected_paths):
        raise HTTPException(status_code=401, detail="需要登录才能查看此文章")

    if not article_path.exists() or not article_path.suffix == ".md":
        raise HTTPException(status_code=404, detail="文章不存在")

    with open(article_path, "r", encoding="utf-8") as f:
        content = f.read()

    html_content = markdown.markdown(
        content,
        extensions=["fenced_code", "tables", "toc", "codehilite", "nl2br", "sane_lists"]
    )
    return {"path": path, "content": content, "html": html_content}

@router.post("/sync")
async def sync_article(
    request: ArticleSyncRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Sync article (from Obsidian etc.)"""
    safe_path = request.path.replace("..", "").lstrip("/")
    if not safe_path.endswith(".md"):
        safe_path += ".md"

    article_path = (settings.articles_dir / safe_path).resolve()
    if not str(article_path).startswith(str(settings.articles_dir.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问该路径")

    article_path.parent.mkdir(parents=True, exist_ok=True)

    content = request.content
    if request.frontmatter:
        frontmatter_str = yaml.dump(request.frontmatter, allow_unicode=True, default_flow_style=False)
        content = f"---\n{frontmatter_str}---\n\n{content}"

    with open(article_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "message": "文章同步成功",
        "path": safe_path,
        "title": request.title or article_path.stem
    }

@router.put("/{path:path}")
async def update_article(
    path: str,
    request: ArticleUpdateRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Edit article content"""
    article_path = (settings.articles_dir / path).resolve()
    if not str(article_path).startswith(str(settings.articles_dir.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问")

    if not article_path.exists() or not article_path.suffix == ".md":
        raise HTTPException(status_code=404, detail="文章不存在")

    with open(article_path, "w", encoding="utf-8") as f:
        f.write(request.content)

    log_service = LogService(db)
    await log_service.record_update("update", "article", article_path.stem, f"路径: {path}", username)

    return {"message": "文章已更新", "path": path}

@router.delete("/{path:path}")
async def delete_article(
    path: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete article"""
    article_path = (settings.articles_dir / path).resolve()
    if not str(article_path).startswith(str(settings.articles_dir.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问")

    if not article_path.exists():
        raise HTTPException(status_code=404, detail="文章不存在")

    article_name = article_path.stem
    article_path.unlink()

    log_service = LogService(db)
    await log_service.record_update("delete", "article", article_name, f"路径: {path}", username)

    return {"message": "文章已删除"}
