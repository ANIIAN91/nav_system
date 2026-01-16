"""Categories routes"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.link import BatchReorderRequest
from app.services.link import LinkService
from app.services.log import LogService
from app.routers.auth import require_auth

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

@router.post("")
async def add_category(
    category: CategoryCreate,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Add a category"""
    service = LinkService(db)
    log_service = LogService(db)

    existing = await service.get_category_by_name(category.name)
    if existing:
        raise HTTPException(status_code=400, detail="分类已存在")

    result = await service.create_category(category.name, category.auth_required)
    await log_service.record_update(
        "add", "category", category.name,
        f"私密: {'是' if category.auth_required else '否'}", username
    )
    await db.commit()

    return {"message": "添加成功", "category": {"name": result.name, "auth_required": result.auth_required}}

@router.put("/{category_name}")
async def update_category(
    category_name: str,
    category: CategoryUpdate,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update a category"""
    service = LinkService(db)
    log_service = LogService(db)

    if category.name != category_name:
        existing = await service.get_category_by_name(category.name)
        if existing:
            raise HTTPException(status_code=400, detail="分类名称已存在")

    result = await service.update_category(category_name, category.name, category.auth_required)
    if not result:
        raise HTTPException(status_code=404, detail="分类不存在")

    details = f"重命名为: {category.name}" if category.name != category_name else f"私密: {'是' if category.auth_required else '否'}"
    await log_service.record_update("update", "category", category_name, details, username)
    await db.commit()

    return {"message": "更新成功", "category": {"name": result.name, "auth_required": result.auth_required}}

@router.delete("/{category_name}")
async def delete_category(
    category_name: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete a category"""
    service = LinkService(db)
    log_service = LogService(db)

    success = await service.delete_category(category_name)
    if not success:
        raise HTTPException(status_code=404, detail="分类不存在")

    await log_service.record_update("delete", "category", category_name, "", username)
    await db.commit()
    return {"message": "删除成功"}

@router.post("/reorder/batch")
async def batch_reorder_categories(
    request: BatchReorderRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Batch reorder categories"""
    service = LinkService(db)
    success = await service.batch_reorder_categories(request.ids)
    if not success:
        raise HTTPException(status_code=400, detail="批量排序失败")
    await db.commit()
    return {"message": "排序成功"}
