"""Log-related use cases."""

from collections.abc import Callable

from app.application.ports import UnitOfWork


class GetVisitLogsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, limit: int) -> dict:
        return await self.uow.logs.get_visits(limit)


class ClearVisitLogsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self) -> dict:
        await self.uow.logs.clear_visits()
        await self.uow.commit()
        return {"message": "访问记录已清空"}


class GetUpdateLogsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, limit: int) -> dict:
        return await self.uow.logs.get_updates(limit)


class ClearUpdateLogsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self) -> dict:
        await self.uow.logs.clear_updates()
        await self.uow.commit()
        return {"message": "更新记录已清空"}


async def record_page_visit(
    session_factory: Callable,
    client_ip: str,
    path: str,
    user_agent: str,
) -> None:
    """Persist a page visit in a standalone background task session."""
    from app.application.unit_of_work import SqlAlchemyUnitOfWork

    async with session_factory() as db:
        uow = SqlAlchemyUnitOfWork(db)
        await uow.logs.record_visit(client_ip, path, user_agent)
        await uow.commit()
