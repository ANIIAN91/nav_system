"""Folders routes"""
import shutil
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.setting import FolderRenameRequest
from app.services.log import LogService
from app.routers.auth import require_auth

router = APIRouter(prefix="/api/v1/folders", tags=["folders"])
settings = get_settings()

@router.get("")
async def list_folders(username: str = Depends(require_auth)):
    """Get article folders list"""
    folders = []
    if settings.articles_dir.exists():
        for item in settings.articles_dir.iterdir():
            if item.is_dir():
                article_count = len(list(item.rglob("*.md")))
                folders.append({
                    "name": item.name,
                    "path": item.name,
                    "article_count": article_count
                })
    return {"folders": folders}

@router.post("")
async def create_folder(
    name: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Create article folder"""
    safe_name = name.replace("..", "").replace("/", "").replace("\\", "").strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="目录名称无效")

    folder_path = settings.articles_dir / safe_name
    if folder_path.exists():
        raise HTTPException(status_code=400, detail="目录已存在")

    folder_path.mkdir(parents=True, exist_ok=True)

    log_service = LogService(db)
    await log_service.record_update("add", "folder", safe_name, "", username)
    await db.commit()

    return {"message": "目录创建成功", "name": safe_name}

@router.put("/{name}")
async def rename_folder(
    name: str,
    request: FolderRenameRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Rename article folder"""
    folder_path = (settings.articles_dir / name).resolve()
    if not str(folder_path).startswith(str(settings.articles_dir.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问")

    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在")

    safe_new_name = request.new_name.replace("..", "").replace("/", "").replace("\\", "").strip()
    if not safe_new_name:
        raise HTTPException(status_code=400, detail="新目录名称无效")

    new_path = settings.articles_dir / safe_new_name
    if new_path.exists():
        raise HTTPException(status_code=400, detail="目标目录已存在")

    folder_path.rename(new_path)

    log_service = LogService(db)
    await log_service.record_update("update", "folder", name, f"重命名为: {safe_new_name}", username)
    await db.commit()

    return {"message": "目录重命名成功", "old_name": name, "new_name": safe_new_name}

@router.delete("/{name}")
async def delete_folder(
    name: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete article folder (including all articles)"""
    folder_path = (settings.articles_dir / name).resolve()
    if not str(folder_path).startswith(str(settings.articles_dir.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问")

    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在")

    article_count = len(list(folder_path.rglob("*.md")))
    shutil.rmtree(folder_path)

    log_service = LogService(db)
    await log_service.record_update("delete", "folder", name, f"包含 {article_count} 篇文章", username)
    await db.commit()

    return {"message": "目录已删除"}
