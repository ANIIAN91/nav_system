"""Pytest configuration and fixtures"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_db
from app.main import app
from app.config import get_settings

settings = get_settings()

# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest_asyncio.fixture
async def client(test_db):
    """Create test client"""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers():
    """Get auth headers for testing"""
    from app.utils.security import create_access_token
    from datetime import timedelta
    token = create_access_token(
        data={"sub": "testuser"},
        expires_delta=timedelta(hours=1)
    )
    return {"Authorization": f"Bearer {token}"}
