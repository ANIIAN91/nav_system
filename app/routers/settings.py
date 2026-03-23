"""Settings routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import require_auth
from app.schemas.site_settings import (
    SiteSettingsResponse,
    SiteSettingsUpdateRequest,
    SiteSettingsUpdateResponse,
)
from app.services.settings import SettingsService

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=SiteSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SiteSettingsResponse:
    """Get site settings."""
    return await SettingsService(db).get_public_settings()


@router.put("", response_model=SiteSettingsUpdateResponse)
async def update_settings(
    settings: SiteSettingsUpdateRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> SiteSettingsUpdateResponse:
    """Update site settings."""
    service = SettingsService(db)
    settings_dict = await service.update_settings(settings)
    await db.commit()
    return {"message": "设置已保存", "settings": settings_dict}
