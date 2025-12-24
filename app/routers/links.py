"""Links routes"""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.link import LinkCreate, LinkUpdate, ReorderRequest, FaviconRequest, ImportRequest
from app.services.link import LinkService
from app.services.log import LogService
from app.routers.auth import get_current_user, require_auth
from app.utils.favicon import fetch_favicon

router = APIRouter(prefix="/api/v1/links", tags=["links"])

@router.get("")
async def get_links(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get navigation links (filtered by login status)"""
    service = LinkService(db)
    return await service.get_all_categories(include_auth_required=current_user is not None)

@router.post("")
async def add_link(
    category_name: str,
    link: LinkCreate,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Add a navigation link"""
    service = LinkService(db)
    log_service = LogService(db)

    result = await service.add_link(category_name, link.title, link.url, link.icon)
    await log_service.record_update("add", "link", link.title, f"分类: {category_name}, URL: {link.url}", username)
    await db.commit()

    return {"message": "添加成功", "link": result}

@router.put("/{link_id}")
async def update_link(
    link_id: str,
    link: LinkUpdate,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update a navigation link"""
    service = LinkService(db)
    log_service = LogService(db)

    result = await service.update_link(link_id, link.title, link.url, link.icon, link.category)
    if not result:
        raise HTTPException(status_code=404, detail="链接不存在")

    await log_service.record_update("update", "link", link.title, f"URL: {link.url}", username)
    await db.commit()
    return {"message": "修改成功", "link": result}

@router.delete("/{link_id}")
async def delete_link(
    link_id: str,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete a navigation link"""
    service = LinkService(db)
    log_service = LogService(db)

    link = await service.get_link_by_id(link_id)
    if not link:
        raise HTTPException(status_code=404, detail="链接不存在")

    link_title = link.title
    await service.delete_link(link_id)
    await log_service.record_update("delete", "link", link_title, "", username)
    await db.commit()

    return {"message": "删除成功"}

@router.post("/{link_id}/reorder")
async def reorder_link(
    link_id: str,
    request: ReorderRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Reorder a link"""
    service = LinkService(db)
    success = await service.reorder_link(link_id, request.direction)
    if not success:
        return {"message": "无法移动"}
    await db.commit()
    return {"message": "移动成功"}

@router.get("/export")
async def export_links(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Export navigation data"""
    from datetime import datetime
    service = LinkService(db)
    data = await service.get_all_categories(include_auth_required=True)
    return {
        "version": 1,
        "appName": "HomePage-Export",
        "exportTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": data
    }

@router.post("/import")
async def import_links(
    request: ImportRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Import navigation data"""
    service = LinkService(db)

    if request.format == "sunpanel":
        try:
            icons = request.data.get("icons", [])
            for group in icons:
                category_name = group.get("title", "未分类")
                auth_required = category_name == "Me"
                category = await service.get_category_by_name(category_name)
                if not category:
                    category = await service.create_category(category_name, auth_required)

                for item in group.get("children", []):
                    await service.add_link(
                        category_name,
                        item.get("title", ""),
                        item.get("url", ""),
                        None
                    )
            await db.commit()
            return {"message": f"导入成功，共 {len(icons)} 个分类"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"SunPanel 格式解析失败: {str(e)}")
    else:
        try:
            import_data = request.data
            if "data" in import_data:
                import_data = import_data["data"]
            if "categories" not in import_data:
                raise ValueError("缺少 categories 字段")

            for cat_data in import_data["categories"]:
                category = await service.get_category_by_name(cat_data["name"])
                if not category:
                    category = await service.create_category(
                        cat_data["name"],
                        cat_data.get("auth_required", False)
                    )
                for link_data in cat_data.get("links", []):
                    await service.add_link(
                        cat_data["name"],
                        link_data.get("title", ""),
                        link_data.get("url", ""),
                        link_data.get("icon"),
                        link_data.get("id")
                    )
            await db.commit()
            return {"message": "导入成功"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")
