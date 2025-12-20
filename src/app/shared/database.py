"""
Database session management with async SQLAlchemy.
"""
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol
from sqlalchemy.orm import DeclarativeBase

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
#REQ-010 START
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey",
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session.

    Yields:
        Async database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
#REQ-010 END

from app.config import get_settings

class Base(DeclarativeBase):
    """
    Canonical SQLAlchemy Declarative Base for ORM models.

    - This does NOT change the async engine/session behavior below.
    - It only provides Base.metadata to register ORM tables (create_all/drop_all in tests).
    """


class DatabaseSessionProtocol(Protocol):
    """Protocol for database session dependency."""

    async def __call__(self) -> AsyncGenerator[AsyncSession, None]: ...


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize database manager.

        Args:
            database_url: Optional database URL override.
        """
        self._database_url = database_url or get_settings().database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Get or create the database engine."""
        if self._engine is None:
            self._engine = create_async_engine(
                self._database_url,
                echo=get_settings().debug,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Create a new database session context."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Dependency for FastAPI to get a database session."""
        async with self.session() as session:
            yield session

    async def close(self) -> None:
        """Close the database engine."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async for session in get_database_manager().get_session():
        yield session

db_manager = get_database_manager()

__all__ = [
    "Base",
    "DatabaseManager",
    "DatabaseSessionProtocol",
    "db_manager",
    "get_database_manager",
    "get_db_session",
]