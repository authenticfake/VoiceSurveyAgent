"""
Database session management with async SQLAlchemy.

REQ-002: OIDC authentication integration

NOTE (retro-compat):
Some later REQs import `Base` from `app.shared.database`.
REQ-002 originally provided only the async engine/session manager.
We expose a SQLAlchemy Declarative Base here to keep backward compatibility.
"""
# --- ADD: declarative Base (retro-compat) -------------------------------------
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base (shared across kits).

    NOTE: Required by newer kits (e.g. REQ-006 app.email.models) that import:
        from app.shared.database import Base
    """
    pass


# --- BEGIN PATCH: Base compatibility layer (REQ-006+) ---

from sqlalchemy.orm import DeclarativeBase

# IMPORTANT:
# Many kits historically define Base in app.auth.models.
# Newer kits (e.g. REQ-006 email/models) import Base from app.shared.database.
# To keep ONE metadata across the whole "app" namespace, we alias Base to auth.models.Base if present.
try:
    from app.auth.models import Base as _AuthBase  # type: ignore
except Exception:  # pragma: no cover
    _AuthBase = None  # type: ignore[assignment]

if _AuthBase is not None:
    Base = _AuthBase  # noqa: N816
else:
    class Base(DeclarativeBase):
        """Fallback Base if auth.models.Base is not available."""
        pass

__all__ = [
    # legacy exports (whatever is already here)
    # + new export
    "Base",
]

# --- END PATCH ---

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base (retro-compatible export)."""


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
