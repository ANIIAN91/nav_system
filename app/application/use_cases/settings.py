"""Settings use cases."""

from app.application.ports import UnitOfWork
from app.schemas.site_settings import SiteSettingsUpdateRequest


class GetSettingsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self) -> dict:
        return await self.uow.settings.get_public_settings()


class GetAdminSettingsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self) -> dict:
        return await self.uow.settings.get_settings()


class UpdateSettingsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, payload: SiteSettingsUpdateRequest) -> dict:
        settings_dict = await self.uow.settings.update_settings(payload)
        await self.uow.commit()
        return {"message": "设置已保存", "settings": settings_dict}
