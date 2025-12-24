"""Database connection and session management"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from sqlalchemy.pool import NullPool
from app.config import get_settings

settings = get_settings()

# SQLite-specific configuration
engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    poolclass=NullPool if "sqlite" in settings.database_url else None
)

# Enable foreign key constraints for SQLite
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    if "sqlite" in settings.database_url:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    """Dependency for getting database session"""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
