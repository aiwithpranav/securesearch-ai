from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _async_url(url: str) -> str:
    """Use the psycopg 3 driver. Before .env exists, use a harmless placeholder
    (no connection is opened until a query runs)."""
    if url == "CHANGE_ME":
        return "postgresql+psycopg://placeholder:placeholder@localhost:5432/placeholder"
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


engine = create_async_engine(_async_url(settings.database_url), echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one database session per request.
    Services call commit() themselves; nothing is saved by accident."""
    async with async_session() as session:
        yield session
