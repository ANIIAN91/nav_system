"""SQLAlchemy-backed navigation repository."""

import uuid

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category, Link


class SqlAlchemyNavigationRepository:
    """Persistence adapter for navigation categories and links."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_categories(self, include_auth_required: bool = True) -> list[Category]:
        query = select(Category).options(selectinload(Category.links)).order_by(Category.sort_order)
        if not include_auth_required:
            query = query.where(Category.auth_required.is_(False))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_category_names(self) -> list[str]:
        result = await self.db.execute(select(Category.name))
        return list(result.scalars().all())

    async def get_category_by_name(self, name: str) -> Category | None:
        result = await self.db.execute(select(Category).where(Category.name == name))
        return result.scalar_one_or_none()

    async def get_max_category_order(self) -> int:
        result = await self.db.execute(select(Category.sort_order).order_by(Category.sort_order.desc()).limit(1))
        return result.scalar() or 0

    async def create_category(self, name: str, auth_required: bool, sort_order: int) -> Category:
        category = Category(name=name, auth_required=auth_required, sort_order=sort_order)
        self.db.add(category)
        await self.db.flush()
        return category

    async def update_category(self, category: Category, new_name: str, auth_required: bool) -> Category:
        category.name = new_name
        category.auth_required = auth_required
        await self.db.flush()
        return category

    async def delete_category(self, category: Category) -> None:
        await self.db.delete(category)

    async def reorder_categories(self, order_map: dict[str, int]) -> None:
        await self.db.execute(
            Category.__table__.update()
            .where(Category.name.in_(order_map.keys()))
            .values(sort_order=case(order_map, value=Category.name, else_=Category.sort_order))
        )
        await self.db.flush()

    async def get_link_by_id(self, link_id: str) -> Link | None:
        result = await self.db.execute(select(Link).where(Link.id == link_id))
        return result.scalar_one_or_none()

    async def get_link_rows_by_ids(self, link_ids: list[str]) -> list[tuple[str, int]]:
        result = await self.db.execute(select(Link.id, Link.category_id).where(Link.id.in_(link_ids)))
        return list(result.all())

    async def list_link_ids_in_category(self, category_id: int) -> list[str]:
        result = await self.db.execute(select(Link.id).where(Link.category_id == category_id))
        return list(result.scalars().all())

    async def list_links_by_category(self, category_id: int) -> list[Link]:
        result = await self.db.execute(
            select(Link).where(Link.category_id == category_id).order_by(Link.sort_order)
        )
        return list(result.scalars().all())

    async def get_max_link_order(self, category_id: int) -> int:
        result = await self.db.execute(
            select(Link.sort_order).where(Link.category_id == category_id).order_by(Link.sort_order.desc()).limit(1)
        )
        return result.scalar() or 0

    async def create_link(
        self,
        category_id: int,
        title: str,
        url: str,
        icon: str | None,
        sort_order: int,
        link_id: str | None = None,
    ) -> Link:
        link = Link(
            id=link_id or str(uuid.uuid4()),
            category_id=category_id,
            title=title,
            url=url,
            icon=icon,
            sort_order=sort_order,
        )
        self.db.add(link)
        await self.db.flush()
        return link

    async def update_link(
        self,
        link: Link,
        title: str,
        url: str,
        icon: str | None,
        *,
        category_id: int | None = None,
        sort_order: int | None = None,
    ) -> Link:
        link.title = title
        link.url = url
        link.icon = icon
        if category_id is not None:
            link.category_id = category_id
        if sort_order is not None:
            link.sort_order = sort_order
        await self.db.flush()
        return link

    async def delete_link(self, link: Link) -> None:
        await self.db.delete(link)

    async def reorder_links(self, order_map: dict[str, int]) -> None:
        await self.db.execute(
            Link.__table__.update()
            .where(Link.id.in_(order_map.keys()))
            .values(sort_order=case(order_map, value=Link.id, else_=Link.sort_order))
        )
        await self.db.flush()

    async def flush(self) -> None:
        await self.db.flush()
