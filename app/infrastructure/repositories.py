"""Repository adapters over the existing service layer."""

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.articles import ArticleService
from app.services.folders import FolderService
from app.services.log import LogService
from app.services.settings import SettingsService


class FileArticleRepository:
    """Article repository backed by the filesystem service."""

    def __init__(self):
        self.service = ArticleService()

    async def list_articles_async(self, protected_paths: list[str], include_protected: bool) -> list[dict]:
        return await self.service.list_articles_async(protected_paths, include_protected)

    async def get_article_async(self, path: str, protected_paths: list[str], allow_protected: bool) -> dict:
        return await self.service.get_article_async(path, protected_paths, allow_protected)

    async def sync_article_async(
        self,
        path: str,
        content: str,
        title: str | None = None,
        frontmatter: dict | None = None,
    ) -> dict:
        return await self.service.sync_article_async(path, content, title, frontmatter)

    async def update_article_async(self, path: str, content: str) -> dict:
        return await self.service.update_article_async(path, content)

    async def delete_article_async(self, path: str) -> dict:
        return await self.service.delete_article_async(path)


class FileFolderRepository:
    """Folder repository backed by the filesystem service."""

    def __init__(self):
        self.service = FolderService()

    async def list_folders_async(self) -> list[dict]:
        return await self.service.list_folders_async()

    async def create_folder_async(self, name: str) -> dict:
        return await self.service.create_folder_async(name)

    async def rename_folder_async(self, name: str, new_name: str) -> dict:
        return await self.service.rename_folder_async(name, new_name)

    async def delete_folder_async(self, name: str) -> dict:
        return await self.service.delete_folder_async(name)


class SqlAlchemySettingsRepository:
    """Settings repository backed by SQLAlchemy services."""

    def __init__(self, db: AsyncSession):
        self.service = SettingsService(db)

    async def get_settings(self, use_cache: bool = True) -> dict:
        return await self.service.get_settings(use_cache=use_cache)

    async def get_public_settings(self, use_cache: bool = True) -> dict:
        return await self.service.get_public_settings(use_cache=use_cache)

    async def update_settings(self, payload):
        return await self.service.update_settings(payload)


class SqlAlchemyLogRepository:
    """Log repository backed by SQLAlchemy services."""

    def __init__(self, db: AsyncSession):
        self.service = LogService(db)

    async def record_visit(self, ip: str, path: str, user_agent: str = "") -> None:
        await self.service.record_visit(ip, path, user_agent)

    async def record_update(
        self,
        action: str,
        target_type: str,
        target_name: str,
        details: str = "",
        username: str = "",
    ) -> None:
        await self.service.record_update(action, target_type, target_name, details, username)

    async def get_visits(self, limit: int = 100) -> dict:
        return await self.service.get_visits(limit)

    async def clear_visits(self) -> None:
        await self.service.clear_visits()

    async def get_updates(self, limit: int = 100) -> dict:
        return await self.service.get_updates(limit)

    async def clear_updates(self) -> None:
        await self.service.clear_updates()
