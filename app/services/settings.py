"""Site settings service."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import GITHUB_URL, VERSION
from app.core import normalize_article_path
from app.models import SiteSettings
from app.schemas.site_settings import SiteSettingsUpdateRequest
from app.utils.cache import get_cached_settings, invalidate_settings_cache, set_cached_settings

DEFAULT_SETTINGS = {
    "icp": "",
    "copyright": "",
    "article_page_title": "文章",
    "site_title": "个人主页导航",
    "link_size": "medium",
    "protected_article_paths": [],
    "github_url": GITHUB_URL,
    "timezone": "Asia/Shanghai",
}

PUBLIC_SETTING_KEYS = (
    "icp",
    "copyright",
    "article_page_title",
    "site_title",
    "link_size",
    "github_url",
    "timezone",
    "version",
)


class SettingsService:
    """Settings read and write boundary."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_settings(self, use_cache: bool = True) -> dict:
        """Return the hydrated site settings payload."""
        if use_cache:
            cached = get_cached_settings()
            if cached is not None:
                return self._with_version(dict(cached))

        row = await self._get_typed_row()
        if row is not None:
            payload = self._row_to_dict(row)
        else:
            payload = dict(DEFAULT_SETTINGS)

        hydrated = self._hydrate_defaults(payload)
        if use_cache:
            set_cached_settings(hydrated)
        return self._with_version(dict(hydrated))

    async def get_public_settings(self, use_cache: bool = True) -> dict:
        """Return public site settings."""
        settings = await self.get_settings(use_cache=use_cache)
        return {key: settings[key] for key in PUBLIC_SETTING_KEYS}

    async def update_settings(self, payload: SiteSettingsUpdateRequest) -> dict:
        """Persist settings into the typed row."""
        current = await self.get_settings(use_cache=False)
        current.pop("version", None)
        updates = payload.model_dump(exclude_none=True)
        merged = {**current, **updates}
        normalized = self._hydrate_defaults(merged)

        row = await self._ensure_typed_row()
        row.site_title = normalized["site_title"]
        row.article_page_title = normalized["article_page_title"]
        row.icp = normalized["icp"]
        row.copyright = normalized["copyright"]
        row.link_size = normalized["link_size"]
        row.timezone = normalized["timezone"]
        row.github_url = normalized["github_url"]
        row.protected_article_paths_json = json.dumps(
            normalized["protected_article_paths"], ensure_ascii=False
        )

        await self.db.flush()
        invalidate_settings_cache()
        return self._with_version(dict(normalized))

    async def _get_typed_row(self) -> SiteSettings | None:
        result = await self.db.execute(select(SiteSettings).where(SiteSettings.id == 1))
        return result.scalar_one_or_none()

    async def _ensure_typed_row(self) -> SiteSettings:
        row = await self._get_typed_row()
        if row is not None:
            return row

        seed = self._hydrate_defaults({})
        row = SiteSettings(
            id=1,
            site_title=seed["site_title"],
            article_page_title=seed["article_page_title"],
            icp=seed["icp"],
            copyright=seed["copyright"],
            link_size=seed["link_size"],
            timezone=seed["timezone"],
            github_url=seed["github_url"],
            protected_article_paths_json=json.dumps(seed["protected_article_paths"], ensure_ascii=False),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    def _row_to_dict(self, row: SiteSettings) -> dict:
        try:
            protected_paths = json.loads(row.protected_article_paths_json or "[]")
        except json.JSONDecodeError:
            protected_paths = []
        return {
            "icp": row.icp or "",
            "copyright": row.copyright or "",
            "article_page_title": row.article_page_title or DEFAULT_SETTINGS["article_page_title"],
            "site_title": row.site_title or DEFAULT_SETTINGS["site_title"],
            "link_size": row.link_size or DEFAULT_SETTINGS["link_size"],
            "protected_article_paths": protected_paths,
            "github_url": row.github_url or DEFAULT_SETTINGS["github_url"],
            "timezone": row.timezone or DEFAULT_SETTINGS["timezone"],
        }

    def _hydrate_defaults(self, payload: dict) -> dict:
        hydrated = {**DEFAULT_SETTINGS, **payload}
        protected_paths = hydrated.get("protected_article_paths") or []
        normalized_paths = []
        for path in protected_paths:
            normalized = normalize_article_path(path)
            if normalized and normalized not in normalized_paths:
                normalized_paths.append(normalized)
        hydrated["protected_article_paths"] = normalized_paths
        return hydrated

    @staticmethod
    def _with_version(payload: dict) -> dict:
        payload["version"] = VERSION
        return payload
