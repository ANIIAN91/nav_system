"""Navigation and category use cases."""

import logging
from datetime import datetime

from app.application.errors import BadRequestError, NotFoundError
from app.application.ports import UnitOfWork
from app.core import validate_url

logger = logging.getLogger(__name__)

CATEGORY_NAME_ERROR = "分类名称不能为空，且不能包含 / 或 \\"


def _normalize_category_name(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized or "/" in normalized or "\\" in normalized:
        raise BadRequestError(CATEGORY_NAME_ERROR)
    return normalized


class ListNavigationUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, include_private: bool) -> dict:
        return await self.uow.navigation.get_all_categories(include_auth_required=include_private)


class AddLinkUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(
        self,
        category_name: str,
        title: str,
        url: str,
        icon: str | None,
        username: str,
    ) -> dict:
        category_name = _normalize_category_name(category_name)
        try:
            validated_url = validate_url(url, allowed_schemes=("http", "https", "mailto"))
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc

        result = await self.uow.navigation.add_link(category_name, title, validated_url, icon)
        await self.uow.logs.record_update("add", "link", title, f"分类: {category_name}, URL: {validated_url}", username)
        await self.uow.commit()
        return {"message": "添加成功", "link": result}


class UpdateLinkUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(
        self,
        link_id: str,
        title: str,
        url: str,
        icon: str | None,
        category: str | None,
        username: str,
    ) -> dict:
        category = _normalize_category_name(category) if category else None
        try:
            validated_url = validate_url(url, allowed_schemes=("http", "https", "mailto"))
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc

        result = await self.uow.navigation.update_link(link_id, title, validated_url, icon, category)
        if not result:
            raise NotFoundError("链接不存在")

        await self.uow.logs.record_update("update", "link", title, f"URL: {validated_url}", username)
        await self.uow.commit()
        return {"message": "修改成功", "link": result}


class DeleteLinkUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, link_id: str, username: str) -> dict:
        link = await self.uow.navigation.get_link_by_id(link_id)
        if not link:
            raise NotFoundError("链接不存在")

        await self.uow.navigation.delete_link(link_id)
        await self.uow.logs.record_update("delete", "link", link.title, "", username)
        await self.uow.commit()
        return {"message": "删除成功"}


class ReorderLinkUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, link_id: str, direction: str) -> dict:
        success = await self.uow.navigation.reorder_link(link_id, direction)
        if not success:
            return {"message": "无法移动"}
        await self.uow.commit()
        return {"message": "移动成功"}


class BatchReorderLinksUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, link_ids: list[str]) -> dict:
        success = await self.uow.navigation.batch_reorder_links(link_ids)
        if not success:
            raise BadRequestError("批量排序失败")
        await self.uow.commit()
        return {"message": "排序成功"}


class ExportNavigationUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self) -> dict:
        data = await self.uow.navigation.get_all_categories(include_auth_required=True)
        return {
            "version": 1,
            "appName": "HomePage-Export",
            "exportTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": data,
        }


class ImportNavigationUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, payload: dict, format_name: str, username: str) -> dict:
        if format_name == "sunpanel":
            return await self._import_sunpanel(payload)
        return await self._import_native(payload)

    async def _import_sunpanel(self, payload: dict) -> dict:
        try:
            icons = payload.get("icons", [])
            for group in icons:
                category_name = _normalize_category_name(group.get("title", "未分类"))
                auth_required = category_name == "Me"
                category = await self.uow.navigation.get_category_by_name(category_name)
                if not category:
                    category = await self.uow.navigation.create_category(category_name, auth_required)

                for item in group.get("children", []):
                    try:
                        validated_url = validate_url(
                            item.get("url", ""),
                            allowed_schemes=("http", "https", "mailto"),
                        )
                    except ValueError:
                        continue
                    await self.uow.navigation.add_link(category_name, item.get("title", ""), validated_url, None)
            await self.uow.commit()
            return {"message": f"导入成功，共 {len(icons)} 个分类"}
        except Exception as exc:
            logger.error("SunPanel import failed: %s", exc, exc_info=True)
            raise BadRequestError("导入失败，请检查文件格式") from exc

    async def _import_native(self, payload: dict) -> dict:
        try:
            import_data = payload.get("data", payload)
            if "categories" not in import_data:
                raise BadRequestError("缺少 categories 字段")

            for category_data in import_data["categories"]:
                category_name = _normalize_category_name(category_data["name"])
                category = await self.uow.navigation.get_category_by_name(category_name)
                if not category:
                    category = await self.uow.navigation.create_category(
                        category_name,
                        category_data.get("auth_required", False),
                    )

                for link_data in category_data.get("links", []):
                    link_id = link_data.get("id")
                    if link_id:
                        existing_link = await self.uow.navigation.get_link_by_id(link_id)
                        if existing_link:
                            logger.warning(
                                "Skipping duplicate link ID during import: %s - %s",
                                link_id,
                                link_data.get("title", ""),
                            )
                            continue

                    try:
                        validated_url = validate_url(
                            link_data.get("url", ""),
                            allowed_schemes=("http", "https", "mailto"),
                        )
                    except ValueError as exc:
                        logger.warning("Skipping invalid URL during import: %s - %s", link_data.get("url", ""), exc)
                        continue

                    try:
                        await self.uow.navigation.add_link(
                            category_name,
                            link_data.get("title", ""),
                            validated_url,
                            link_data.get("icon"),
                            link_id,
                        )
                    except Exception as exc:
                        logger.warning(
                            "Failed to add link during import: %s - %s",
                            link_data.get("title", ""),
                            exc,
                        )
                        continue

            await self.uow.commit()
            return {"message": "导入成功"}
        except BadRequestError:
            raise
        except Exception as exc:
            logger.error("Import failed: %s", exc, exc_info=True)
            raise BadRequestError("导入失败，请检查文件格式") from exc


class CreateCategoryUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, name: str, auth_required: bool, username: str) -> dict:
        name = _normalize_category_name(name)
        existing = await self.uow.navigation.get_category_by_name(name)
        if existing:
            raise BadRequestError("分类已存在")

        result = await self.uow.navigation.create_category(name, auth_required)
        await self.uow.logs.record_update(
            "add",
            "category",
            name,
            f"私密: {'是' if auth_required else '否'}",
            username,
        )
        await self.uow.commit()
        return {"message": "添加成功", "category": {"name": result.name, "auth_required": result.auth_required}}


class UpdateCategoryUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, category_name: str, new_name: str, auth_required: bool, username: str) -> dict:
        category_name = _normalize_category_name(category_name)
        new_name = _normalize_category_name(new_name)
        if new_name != category_name:
            existing = await self.uow.navigation.get_category_by_name(new_name)
            if existing:
                raise BadRequestError("分类名称已存在")

        result = await self.uow.navigation.update_category(category_name, new_name, auth_required)
        if not result:
            raise NotFoundError("分类不存在")

        details = f"重命名为: {new_name}" if new_name != category_name else f"私密: {'是' if auth_required else '否'}"
        await self.uow.logs.record_update("update", "category", category_name, details, username)
        await self.uow.commit()
        return {"message": "更新成功", "category": {"name": result.name, "auth_required": result.auth_required}}


class DeleteCategoryUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, category_name: str, username: str) -> dict:
        category_name = _normalize_category_name(category_name)
        success = await self.uow.navigation.delete_category(category_name)
        if not success:
            raise NotFoundError("分类不存在")

        await self.uow.logs.record_update("delete", "category", category_name, "", username)
        await self.uow.commit()
        return {"message": "删除成功"}


class BatchReorderCategoriesUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, category_names: list[str]) -> dict:
        category_names = [_normalize_category_name(name) for name in category_names]
        success = await self.uow.navigation.batch_reorder_categories(category_names)
        if not success:
            raise BadRequestError("批量排序失败")
        await self.uow.commit()
        return {"message": "排序成功"}
