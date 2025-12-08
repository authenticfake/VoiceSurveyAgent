"""Database session management with async SQLAlchemy."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

def create_engine() -> AsyncEngine:
    """Create async database engine."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.debug,
    )

def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

# Global engine and session factory
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine

def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of request context."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None