"""Navigation domain service."""

from app.application.ports import NavigationRepository
from app.utils.cache import CACHE_LINKS_ALL, CACHE_LINKS_PUBLIC, cache, invalidate_links_cache


class NavigationDomainService:
    """Encapsulate navigation-specific rules, shaping, and cache behavior."""

    def __init__(self, repository: NavigationRepository):
        self.repository = repository

    async def get_all_categories(self, include_auth_required: bool = True) -> dict:
        cache_key = CACHE_LINKS_ALL if include_auth_required else CACHE_LINKS_PUBLIC
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        categories = await self.repository.list_categories(include_auth_required=include_auth_required)
        payload = {"categories": [self._serialize_category(category) for category in categories]}
        cache.set(cache_key, payload, ttl=60)
        return payload

    async def get_category_by_name(self, name: str):
        return await self.repository.get_category_by_name(name)

    async def create_category(self, name: str, auth_required: bool = False):
        sort_order = await self.repository.get_max_category_order() + 1
        category = await self.repository.create_category(name, auth_required, sort_order)
        invalidate_links_cache()
        return category

    async def update_category(self, old_name: str, new_name: str, auth_required: bool):
        category = await self.repository.get_category_by_name(old_name)
        if not category:
            return None
        updated = await self.repository.update_category(category, new_name, auth_required)
        invalidate_links_cache()
        return updated

    async def delete_category(self, name: str) -> bool:
        category = await self.repository.get_category_by_name(name)
        if not category:
            return False
        await self.repository.delete_category(category)
        invalidate_links_cache()
        return True

    async def add_link(
        self,
        category_name: str,
        title: str,
        url: str,
        icon: str | None = None,
        link_id: str | None = None,
    ) -> dict:
        category = await self.repository.get_category_by_name(category_name)
        if category is None:
            category = await self.create_category(category_name)

        sort_order = await self.repository.get_max_link_order(category.id) + 1
        link = await self.repository.create_link(category.id, title, url, icon, sort_order, link_id)
        invalidate_links_cache()
        return self._serialize_link(link)

    async def get_link_by_id(self, link_id: str):
        return await self.repository.get_link_by_id(link_id)

    async def update_link(
        self,
        link_id: str,
        title: str,
        url: str,
        icon: str | None,
        new_category_name: str | None = None,
    ) -> dict | None:
        link = await self.repository.get_link_by_id(link_id)
        if not link:
            return None

        next_category_id = None
        next_sort_order = None
        if new_category_name:
            new_category = await self.repository.get_category_by_name(new_category_name)
            if new_category and new_category.id != link.category_id:
                next_category_id = new_category.id
                next_sort_order = await self.repository.get_max_link_order(new_category.id) + 1

        updated = await self.repository.update_link(
            link,
            title,
            url,
            icon,
            category_id=next_category_id,
            sort_order=next_sort_order,
        )
        invalidate_links_cache()
        return self._serialize_link(updated)

    async def delete_link(self, link_id: str) -> bool:
        link = await self.repository.get_link_by_id(link_id)
        if not link:
            return False
        await self.repository.delete_link(link)
        invalidate_links_cache()
        return True

    async def reorder_link(self, link_id: str, direction: str) -> bool:
        link = await self.repository.get_link_by_id(link_id)
        if not link:
            return False

        links = await self.repository.list_links_by_category(link.category_id)
        for index, current in enumerate(links):
            if str(current.id) != link_id:
                continue
            if direction == "up" and index > 0:
                current.sort_order, links[index - 1].sort_order = links[index - 1].sort_order, current.sort_order
                await self.repository.flush()
                invalidate_links_cache()
                return True
            if direction == "down" and index < len(links) - 1:
                current.sort_order, links[index + 1].sort_order = links[index + 1].sort_order, current.sort_order
                await self.repository.flush()
                invalidate_links_cache()
                return True
            return False
        return False

    async def batch_reorder_links(self, link_ids: list[str]) -> bool:
        if not link_ids or len(set(link_ids)) != len(link_ids):
            return False

        rows = await self.repository.get_link_rows_by_ids(link_ids)
        if len(rows) != len(link_ids):
            return False

        category_ids = {row.category_id for row in rows}
        if len(category_ids) != 1:
            return False

        category_id = next(iter(category_ids))
        category_link_ids = set(await self.repository.list_link_ids_in_category(category_id))
        if category_link_ids != set(link_ids):
            return False

        order_map = {link_id: index for index, link_id in enumerate(link_ids)}
        await self.repository.reorder_links(order_map)
        invalidate_links_cache()
        return True

    async def batch_reorder_categories(self, category_names: list[str]) -> bool:
        if not category_names or len(set(category_names)) != len(category_names):
            return False

        existing_names = set(await self.repository.list_category_names())
        if existing_names != set(category_names):
            return False

        order_map = {name: index for index, name in enumerate(category_names)}
        await self.repository.reorder_categories(order_map)
        invalidate_links_cache()
        return True

    @staticmethod
    def _serialize_category(category) -> dict:
        return {
            "name": category.name,
            "auth_required": category.auth_required,
            "links": [
                NavigationDomainService._serialize_link(link)
                for link in sorted(category.links, key=lambda item: item.sort_order)
            ],
        }

    @staticmethod
    def _serialize_link(link) -> dict:
        return {
            "id": str(link.id),
            "title": link.title,
            "url": link.url,
            "icon": link.icon,
        }
