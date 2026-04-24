"""Pytest configuration and fixtures."""

import asyncio
import os
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-minimum-123456")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")

from app.config import get_settings
from app.database import Base, get_db
from app.services.auth import reset_auth_service_state
from app.services.rate_limit import get_rate_limiter, reset_rate_limiter
from app.utils.cache import get_cache_backend, reset_cache_backend

settings = get_settings()
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_in_memory_state():
    """Reset in-memory cache and rate limiter state between tests."""
    reset_auth_service_state()
    reset_cache_backend()
    reset_rate_limiter()
    cache_backend = get_cache_backend()
    if hasattr(cache_backend, "clear"):
        cache_backend.clear()
    rate_limiter = get_rate_limiter()
    if hasattr(rate_limiter, "clear_all"):
        rate_limiter.clear_all()
    yield
    reset_auth_service_state()
    reset_cache_backend()
    reset_rate_limiter()
    cache_backend = get_cache_backend()
    if hasattr(cache_backend, "clear"):
        cache_backend.clear()
    rate_limiter = get_rate_limiter()
    if hasattr(rate_limiter, "clear_all"):
        rate_limiter.clear_all()


@pytest_asyncio.fixture
async def test_db():
    """Create test database."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client."""
    from app.main import app

    async def override_get_db():
        yield test_db

    @asynccontextmanager
    async def override_session_factory():
        yield test_db

    original_session_factory = app.state.session_factory
    app.dependency_overrides[get_db] = override_get_db
    app.state.session_factory = override_session_factory
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            yield async_client
    finally:
        app.state.session_factory = original_session_factory
        app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Get auth headers for testing."""
    from datetime import timedelta

    from app.utils.security import create_access_token

    token = create_access_token(data={"sub": "testuser"}, expires_delta=timedelta(hours=1))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def isolated_articles_dir(tmp_path, monkeypatch):
    """Use a temporary articles directory for filesystem tests."""
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()

    monkeypatch.setattr(settings, "articles_dir", articles_dir)
    return articles_dir
