"""Favicon privacy tests: hashed file names, opt-in public fallback, legacy icon migration."""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import Base
from app.models import Category, Link
from app.utils import favicon
from app.utils.favicon import fetch_favicon, icon_filename
from scripts.migrate_icon_names import migrate_icon_names


def test_icon_filename_does_not_reveal_domain():
    name = icon_filename("github.com", ".ico")
    assert name.endswith(".ico")
    assert "github" not in name
    assert name == icon_filename("GitHub.com", ".ico")
    assert name != icon_filename("gitlab.com", ".ico")


def test_icon_filename_is_keyed_by_secret(monkeypatch):
    original = icon_filename("github.com", ".ico")
    monkeypatch.setattr(get_settings(), "secret_key", "another-secret-key-32-chars-0000000")
    assert icon_filename("github.com", ".ico") != original


@pytest.fixture
def recorded_requests(monkeypatch, tmp_path):
    requested: list[str] = []

    async def fake_safe_get(url, *, headers, timeout):
        requested.append(url)
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(favicon, "_safe_get", fake_safe_get)
    monkeypatch.setattr(favicon, "is_safe_url", lambda url: (True, ""))
    monkeypatch.setattr(get_settings(), "static_dir", tmp_path)
    return requested


@pytest.mark.asyncio
async def test_public_fallback_disabled_by_default(recorded_requests):
    assert get_settings().favicon_public_fallback is False

    result = await fetch_favicon("https://example.com")

    assert result["icon"] is None
    assert not any("duckduckgo.com" in url or "google.com" in url for url in recorded_requests)


@pytest.mark.asyncio
async def test_public_fallback_can_be_enabled(recorded_requests, monkeypatch):
    monkeypatch.setattr(get_settings(), "favicon_public_fallback", True)

    await fetch_favicon("https://example.com")

    assert any("icons.duckduckgo.com" in url for url in recorded_requests)
    assert any("google.com/s2/favicons" in url for url in recorded_requests)


@pytest.mark.asyncio
async def test_migrate_icon_names_renames_legacy_files(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    (icons_dir / "github_com.png").write_bytes(b"icon-bytes")
    (icons_dir / "custom.png").write_bytes(b"custom")

    async with session_factory() as db:
        category = Category(name="Dev", auth_required=True, sort_order=1)
        db.add(category)
        await db.flush()
        db.add_all([
            Link(id="a", category_id=category.id, title="GitHub", url="https://github.com", icon="github_com.png"),
            Link(id="b", category_id=category.id, title="Docs", url="https://github.com/docs", icon="github_com.png"),
            Link(id="c", category_id=category.id, title="Custom", url="https://example.com", icon="custom.png"),
        ])
        await db.commit()

    new_name = icon_filename("github.com", ".png")
    dry_run = await migrate_icon_names(session_factory, icons_dir, dry_run=True)
    assert dry_run == {"github_com.png": new_name}
    assert (icons_dir / "github_com.png").exists()

    renamed = await migrate_icon_names(session_factory, icons_dir, dry_run=False)
    assert renamed == {"github_com.png": new_name}
    assert not (icons_dir / "github_com.png").exists()
    assert (icons_dir / new_name).read_bytes() == b"icon-bytes"
    assert (icons_dir / "custom.png").exists()

    async with session_factory() as db:
        icons = dict((await db.execute(select(Link.id, Link.icon))).all())
    assert icons == {"a": new_name, "b": new_name, "c": "custom.png"}

    await engine.dispose()
