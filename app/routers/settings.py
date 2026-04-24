"""Settings routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_auth
from app.application.unit_of_work import SqlAlchemyUnitOfWork
from app.application.use_cases.settings import GetAdminSettingsUseCase, GetSettingsUseCase, UpdateSettingsUseCase
from app.database import get_db
from app.schemas.site_settings import (
    PublicSiteSettingsResponse,
    SiteSettingsResponse,
    SiteSettingsUpdateRequest,
    SiteSettingsUpdateResponse,
)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=PublicSiteSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> PublicSiteSettingsResponse:
    """Get public site settings."""
    return await GetSettingsUseCase(SqlAlchemyUnitOfWork(db)).execute()


@router.get("/admin", response_model=SiteSettingsResponse)
async def get_admin_settings(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> SiteSettingsResponse:
    """Get full site settings for the management UI."""
    return await GetAdminSettingsUseCase(SqlAlchemyUnitOfWork(db)).execute()


@router.put("", response_model=SiteSettingsUpdateResponse)
async def update_settings(
    settings: SiteSettingsUpdateRequest,
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> SiteSettingsUpdateResponse:
    """Update site settings."""
    return await UpdateSettingsUseCase(SqlAlchemyUnitOfWork(db)).execute(settings)
