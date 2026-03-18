"""
Async SQLAlchemy engine and session factory.
Connects to the same MySQL database as the Django application.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency that yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Verify database connectivity on startup."""
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("SELECT 1")
        )


async def close_db():
    """Dispose engine on shutdown."""
    await engine.dispose()
