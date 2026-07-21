"""
Async database engine + session management.

Using SQLite (via aiosqlite) by default so the project runs with zero
external setup — `docker compose up` or even just `uvicorn app.main:app`
works out of the box. Because everything goes through SQLAlchemy's async
ORM, switching DATABASE_URL to a Postgres connection string later (e.g. for
multi-instance production deployment) requires no application code changes.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug and settings.environment == "development",
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create tables if they don't exist. Fine for SQLite/dev.
    For production with Postgres, use Alembic migrations instead."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped DB session and
    guarantees it's closed afterward, even on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
