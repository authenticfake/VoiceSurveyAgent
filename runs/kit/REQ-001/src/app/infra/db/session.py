from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infra.config.settings import get_settings
from app.infra.db.base import Base

_settings = get_settings()
_engine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
)
AsyncSessionFactory = async_sessionmaker(
    _engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async SQLAlchemy session."""
    async with AsyncSessionFactory() as session:
        yield session


async def init_db() -> None:
    """Create database tables for the current metadata."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)