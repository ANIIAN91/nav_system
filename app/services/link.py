"""Link and Category service"""
import uuid
from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category, Link
from app.utils.cache import cache, CACHE_LINKS_ALL, CACHE_LINKS_PUBLIC, invalidate_links_cache

class LinkService:
    """Service for managing links and categories"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_categories(self, include_auth_required: bool = True) -> List[dict]:
        """Get all categories with their links (cached for 60s)"""
        cache_key = CACHE_LINKS_ALL if include_auth_required else CACHE_LINKS_PUBLIC
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        query = select(Category).options(selectinload(Category.links)).order_by(Category.sort_order)
        if not include_auth_required:
            query = query.where(Category.auth_required == False)
        result = await self.db.execute(query)
        categories = result.scalars().all()

        data = {
            "categories": [
                {
                    "name": cat.name,
                    "auth_required": cat.auth_required,
                    "links": [
                        {
                            "id": str(link.id),
                            "title": link.title,
                            "url": link.url,
                            "icon": link.icon
                        }
                        for link in sorted(cat.links, key=lambda x: x.sort_order)
                    ]
                }
                for cat in categories
            ]
        }
        cache.set(cache_key, data, ttl=60)
        return data

    async def get_category_by_name(self, name: str) -> Optional[Category]:
        """Get category by name"""
        result = await self.db.execute(select(Category).where(Category.name == name))
        return result.scalar_one_or_none()

    async def create_category(self, name: str, auth_required: bool = False) -> Category:
        """Create a new category"""
        max_order = await self._get_max_category_order()
        category = Category(name=name, auth_required=auth_required, sort_order=max_order + 1)
        self.db.add(category)
        await self.db.flush()
        invalidate_links_cache()
        return category

    async def update_category(self, old_name: str, new_name: str, auth_required: bool) -> Optional[Category]:
        """Update a category"""
        category = await self.get_category_by_name(old_name)
        if not category:
            return None
        category.name = new_name
        category.auth_required = auth_required
        await self.db.flush()
        invalidate_links_cache()
        return category

    async def delete_category(self, name: str) -> bool:
        """Delete a category"""
        category = await self.get_category_by_name(name)
        if not category:
            return False
        await self.db.delete(category)
        invalidate_links_cache()
        return True

    async def reorder_category(self, name: str, direction: str) -> bool:
        """Reorder a category (up or down)"""
        categories = (await self.db.execute(
            select(Category).order_by(Category.sort_order)
        )).scalars().all()

        for i, cat in enumerate(categories):
            if cat.name == name:
                if direction == "up" and i > 0:
                    categories[i].sort_order, categories[i-1].sort_order = \
                        categories[i-1].sort_order, categories[i].sort_order
                    invalidate_links_cache()
                    return True
                elif direction == "down" and i < len(categories) - 1:
                    categories[i].sort_order, categories[i+1].sort_order = \
                        categories[i+1].sort_order, categories[i].sort_order
                    invalidate_links_cache()
                    return True
        return False

    async def add_link(self, category_name: str, title: str, url: str, icon: Optional[str] = None, link_id: Optional[str] = None) -> dict:
        """Add a link to a category"""
        category = await self.get_category_by_name(category_name)
        if not category:
            category = await self.create_category(category_name)

        max_order = await self._get_max_link_order(category.id)
        link = Link(
            id=link_id if link_id else str(uuid.uuid4()),
            category_id=category.id,
            title=title,
            url=url,
            icon=icon,
            sort_order=max_order + 1
        )
        self.db.add(link)
        await self.db.flush()
        invalidate_links_cache()
        return {"id": str(link.id), "title": link.title, "url": link.url, "icon": link.icon}

    async def get_link_by_id(self, link_id: str) -> Optional[Link]:
        """Get link by ID"""
        result = await self.db.execute(select(Link).where(Link.id == link_id))
        return result.scalar_one_or_none()

    async def update_link(self, link_id: str, title: str, url: str, icon: Optional[str],
                          new_category_name: Optional[str] = None) -> Optional[dict]:
        """Update a link"""
        link = await self.get_link_by_id(link_id)
        if not link:
            return None

        link.title = title
        link.url = url
        link.icon = icon

        if new_category_name:
            new_category = await self.get_category_by_name(new_category_name)
            if new_category and new_category.id != link.category_id:
                link.category_id = new_category.id
                link.sort_order = await self._get_max_link_order(new_category.id) + 1

        await self.db.flush()
        invalidate_links_cache()
        return {"id": str(link.id), "title": link.title, "url": link.url, "icon": link.icon}

    async def delete_link(self, link_id: str) -> bool:
        """Delete a link"""
        link = await self.get_link_by_id(link_id)
        if not link:
            return False
        await self.db.delete(link)
        invalidate_links_cache()
        return True

    async def reorder_link(self, link_id: str, direction: str) -> bool:
        """Reorder a link within its category"""
        link = await self.get_link_by_id(link_id)
        if not link:
            return False

        links = (await self.db.execute(
            select(Link).where(Link.category_id == link.category_id).order_by(Link.sort_order)
        )).scalars().all()

        for i, l in enumerate(links):
            if str(l.id) == link_id:
                if direction == "up" and i > 0:
                    links[i].sort_order, links[i-1].sort_order = links[i-1].sort_order, links[i].sort_order
                    invalidate_links_cache()
                    return True
                elif direction == "down" and i < len(links) - 1:
                    links[i].sort_order, links[i+1].sort_order = links[i+1].sort_order, links[i].sort_order
                    invalidate_links_cache()
                    return True
        return False

    async def batch_reorder_links(self, link_ids: List[str]) -> bool:
        """Batch reorder links by ID list"""
        if not link_ids:
            return False

        # Get all links and update their sort_order based on the new order
        for index, link_id in enumerate(link_ids):
            link = await self.get_link_by_id(link_id)
            if link:
                link.sort_order = index

        await self.db.flush()
        invalidate_links_cache()
        return True

    async def batch_reorder_categories(self, category_names: List[str]) -> bool:
        """Batch reorder categories by name list"""
        if not category_names:
            return False

        # Get all categories and update their sort_order based on the new order
        for index, name in enumerate(category_names):
            category = await self.get_category_by_name(name)
            if category:
                category.sort_order = index

        await self.db.flush()
        invalidate_links_cache()
        return True

    async def _get_max_category_order(self) -> int:
        """Get max sort order for categories"""
        result = await self.db.execute(select(Category.sort_order).order_by(Category.sort_order.desc()).limit(1))
        max_order = result.scalar()
        return max_order if max_order else 0

    async def _get_max_link_order(self, category_id: int) -> int:
        """Get max sort order for links in a category"""
        result = await self.db.execute(
            select(Link.sort_order).where(Link.category_id == category_id).order_by(Link.sort_order.desc()).limit(1)
        )
        max_order = result.scalar()
        return max_order if max_order else 0
