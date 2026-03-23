"""Settings service tests."""

import json

import pytest

from app.models import SiteSettings
from app.schemas.site_settings import SiteSettingsUpdateRequest
from app.services.settings import SettingsService
from app.utils.cache import get_cached_settings, reset_cache_backend, set_cache_backend


@pytest.mark.asyncio
async def test_settings_service_returns_defaults(test_db):
    """Missing settings should be hydrated from defaults."""
    data = await SettingsService(test_db).get_public_settings(use_cache=False)

    assert data["site_title"] == "个人主页导航"
    assert data["protected_article_paths"] == []
    assert data["version"]
    assert "analytics_code" not in data


@pytest.mark.asyncio
async def test_settings_service_updates_typed_row_and_cache(test_db):
    """Updates should write the typed row and clear cache."""
    service = SettingsService(test_db)
    await service.get_public_settings(use_cache=True)
    assert get_cached_settings() is not None

    updated = await service.update_settings(
        SiteSettingsUpdateRequest(
            site_title="New Title",
            protected_article_paths=["private", "private", "notes\\secret"],
        )
    )
    await test_db.commit()

    row = (await test_db.get(SiteSettings, 1))
    assert row is not None
    assert row.site_title == "New Title"
    assert json.loads(row.protected_article_paths_json) == ["private", "notes/secret"]
    assert updated["site_title"] == "New Title"
    assert get_cached_settings() is None


@pytest.mark.asyncio
async def test_settings_service_supports_swappable_cache_backend(test_db):
    """Settings service should work with a replaced cache backend."""

    class RecordingCacheBackend:
        def __init__(self):
            self.storage = {}
            self.get_calls = 0
            self.set_calls = 0
            self.delete_calls = 0

        def get(self, key):
            self.get_calls += 1
            return self.storage.get(key)

        def set(self, key, value, ttl=60):
            self.set_calls += 1
            self.storage[key] = value

        def delete(self, key):
            self.delete_calls += 1
            self.storage.pop(key, None)

        def clear(self):
            self.storage.clear()

        def invalidate_pattern(self, pattern):
            keys_to_delete = [key for key in self.storage if key.startswith(pattern)]
            for key in keys_to_delete:
                del self.storage[key]

    backend = RecordingCacheBackend()
    set_cache_backend(backend)

    try:
        service = SettingsService(test_db)
        first = await service.get_public_settings(use_cache=True)
        second = await service.get_public_settings(use_cache=True)
        await service.update_settings(SiteSettingsUpdateRequest(site_title="Cached Title"))

        assert first["site_title"] == second["site_title"]
        assert backend.set_calls == 1
        assert backend.get_calls >= 2
        assert backend.delete_calls == 1
    finally:
        reset_cache_backend()
