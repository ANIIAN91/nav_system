"""Settings routes"""
import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Setting
from app.schemas.setting import SiteSettings
from app.routers.auth import require_auth

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_KEYS = [
    "icp", "copyright", "article_page_title", "site_title",
    "link_size", "protected_article_paths", "analytics_code"
]

async def get_site_settings(db: AsyncSession) -> dict:
    """Get all site settings as dict"""
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    settings_dict = {s.key: s.value for s in settings}

    # Parse protected_article_paths as JSON list
    if "protected_article_paths" in settings_dict:
        try:
            settings_dict["protected_article_paths"] = json.loads(settings_dict["protected_article_paths"])
        except:
            settings_dict["protected_article_paths"] = []
    else:
        settings_dict["protected_article_paths"] = []

    # Set defaults
    defaults = {
        "icp": "",
        "copyright": "",
        "article_page_title": "文章",
        "site_title": "个人主页导航",
        "link_size": "medium",
        "analytics_code": ""
    }
    for key, default in defaults.items():
        if key not in settings_dict:
            settings_dict[key] = default

    return settings_dict

@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get site settings"""
    return await get_site_settings(db)

@router.put("")
async def update_settings(
    settings: SiteSettings,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update site settings"""
    settings_dict = settings.model_dump()

    # Convert protected_article_paths to JSON string
    if "protected_article_paths" in settings_dict:
        settings_dict["protected_article_paths"] = json.dumps(settings_dict["protected_article_paths"])

    for key, value in settings_dict.items():
        if key in SETTINGS_KEYS:
            result = await db.execute(select(Setting).where(Setting.key == key))
            setting = result.scalar_one_or_none()
            if setting:
                setting.value = str(value) if value is not None else ""
            else:
                db.add(Setting(key=key, value=str(value) if value is not None else ""))

    return {"message": "设置已保存", "settings": await get_site_settings(db)}
