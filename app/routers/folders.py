"""Folders routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import require_auth
from app.schemas.folder import FolderListResponse, FolderRenameRequest
from app.services.folders import FolderService
from app.services.log import LogService

router = APIRouter(prefix="/api/v1/folders", tags=["folders"])


@router.get("")
async def list_folders(username: str = Depends(require_auth)) -> FolderListResponse:
    """Get article folders list."""
    return {"folders": await FolderService().list_folders_async()}


@router.post("")
async def create_folder(
    name: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create article folder."""
    try:
        folder = await FolderService().create_folder_async(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_service = LogService(db)
    await log_service.record_update("add", "folder", folder["name"], "", username)
    await db.commit()
    return {"message": "目录创建成功", "name": folder["name"]}


@router.put("/{name:path}")
async def rename_folder(
    name: str,
    request: FolderRenameRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Rename article folder."""
    try:
        result = await FolderService().rename_folder_async(name, request.new_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_service = LogService(db)
    await log_service.record_update(
        "update",
        "folder",
        result["old_name"],
        f"重命名为: {result['new_name']}",
        username,
    )
    await db.commit()
    return {"message": "目录重命名成功", "old_name": result["old_name"], "new_name": result["new_name"]}


@router.delete("/{name:path}")
async def delete_folder(
    name: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete article folder including all articles."""
    try:
        result = await FolderService().delete_folder_async(name)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_service = LogService(db)
    await log_service.record_update(
        "delete",
        "folder",
        result["name"],
        f"包含 {result['article_count']} 篇文章",
        username,
    )
    await db.commit()
    return {"message": "目录已删除"}
