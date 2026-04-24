"""Unit-of-work implementation."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.navigation import NavigationDomainService
from app.infrastructure.navigation import SqlAlchemyNavigationRepository
from app.infrastructure.repositories import (
    FileArticleRepository,
    FileFolderRepository,
    SqlAlchemyLogRepository,
    SqlAlchemySettingsRepository,
)


class SqlAlchemyUnitOfWork:
    """Collect repositories and commit/rollback boundaries around one DB session."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.navigation = NavigationDomainService(SqlAlchemyNavigationRepository(db))
        self.articles = FileArticleRepository()
        self.folders = FileFolderRepository()
        self.settings = SqlAlchemySettingsRepository(db)
        self.logs = SqlAlchemyLogRepository(db)

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()
