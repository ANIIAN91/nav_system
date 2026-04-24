"""Markdown content and folder use cases."""

from app.application.errors import BadRequestError, ForbiddenError, NotFoundError, UnauthorizedError
from app.application.ports import UnitOfWork
from app.services.articles import ArticleAuthenticationRequiredError


class ListArticlesUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, include_protected: bool) -> dict:
        site_settings = await self.uow.settings.get_settings()
        articles = await self.uow.articles.list_articles_async(
            protected_paths=site_settings.get("protected_article_paths", []),
            include_protected=include_protected,
        )
        return {"articles": articles}


class GetArticleUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, path: str, allow_protected: bool) -> dict:
        site_settings = await self.uow.settings.get_settings()
        try:
            return await self.uow.articles.get_article_async(
                path,
                protected_paths=site_settings.get("protected_article_paths", []),
                allow_protected=allow_protected,
            )
        except ArticleAuthenticationRequiredError as exc:
            raise UnauthorizedError(str(exc)) from exc
        except ValueError as exc:
            raise ForbiddenError(str(exc)) from exc
        except FileNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc


class CreateArticleUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, path: str, content: str, title: str | None, frontmatter: dict | None, username: str) -> dict:
        try:
            result = await self.uow.articles.sync_article_async(path=path, content=content, title=title, frontmatter=frontmatter)
        except ValueError as exc:
            raise ForbiddenError(str(exc)) from exc

        await self.uow.logs.record_update("add", "article", result["title"] or "", f"路径: {result['path']}", username)
        await self.uow.commit()
        return result


class UpdateArticleUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, path: str, content: str, username: str) -> dict:
        try:
            result = await self.uow.articles.update_article_async(path, content)
        except ValueError as exc:
            raise ForbiddenError(str(exc)) from exc
        except FileNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

        await self.uow.logs.record_update("update", "article", result["title"], f"路径: {result['path']}", username)
        await self.uow.commit()
        return {"message": "文章已更新", "path": result["path"], "title": result["title"]}


class DeleteArticleUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, path: str, username: str) -> dict:
        try:
            result = await self.uow.articles.delete_article_async(path)
        except ValueError as exc:
            raise ForbiddenError(str(exc)) from exc
        except FileNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

        await self.uow.logs.record_update("delete", "article", result["title"], f"路径: {result['path']}", username)
        await self.uow.commit()
        return {"message": "文章已删除", "path": result["path"], "title": result["title"]}


class ListFoldersUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self) -> dict:
        return {"folders": await self.uow.folders.list_folders_async()}


class CreateFolderUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, name: str, username: str) -> dict:
        try:
            folder = await self.uow.folders.create_folder_async(name)
        except (ValueError, FileExistsError) as exc:
            raise BadRequestError(str(exc)) from exc

        await self.uow.logs.record_update("add", "folder", folder["name"], "", username)
        await self.uow.commit()
        return {"message": "目录创建成功", "name": folder["name"]}


class RenameFolderUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, name: str, new_name: str, username: str) -> dict:
        try:
            result = await self.uow.folders.rename_folder_async(name, new_name)
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc
        except FileExistsError as exc:
            raise BadRequestError(str(exc)) from exc
        except FileNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

        await self.uow.logs.record_update("update", "folder", result["old_name"], f"重命名为: {result['new_name']}", username)
        await self.uow.commit()
        return {"message": "目录重命名成功", "old_name": result["old_name"], "new_name": result["new_name"]}


class DeleteFolderUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, name: str, username: str) -> dict:
        try:
            result = await self.uow.folders.delete_folder_async(name)
        except ValueError as exc:
            raise ForbiddenError(str(exc)) from exc
        except FileNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

        await self.uow.logs.record_update("delete", "folder", result["name"], f"包含 {result['article_count']} 篇文章", username)
        await self.uow.commit()
        return {"message": "目录已删除"}
