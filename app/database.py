"""Database connection and session management."""

from functools import lru_cache

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.config import get_settings

Base = declarative_base()


def _build_engine():
    settings = get_settings()
    database_url = settings.database_url
    engine = create_async_engine(
        database_url,
        echo=False,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        poolclass=NullPool if "sqlite" in database_url else None,
    )

    if "sqlite" in database_url:

        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


@lru_cache(maxsize=1)
def get_engine():
    """Return the process-wide SQLAlchemy engine."""
    return _build_engine()


@lru_cache(maxsize=1)
def get_async_session_factory():
    """Return the process-wide async session factory."""
    return async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Dependency for getting a database session."""
    async with get_async_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_db_connection():
    """Verify that the configured database is reachable."""
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))
