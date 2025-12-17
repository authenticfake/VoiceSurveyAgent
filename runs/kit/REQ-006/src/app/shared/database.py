# BEGIN FILE: runs/kit/REQ-006/src/app/shared/database.py
"""
Database shim (REQ-006).

Obiettivo:
- non tocchiamo REQ-002
- ma forniamo `Base` e `get_db_session` dove alcuni moduli lo cercano.
"""

from __future__ import annotations

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

# Base retrocompatibile: usiamo la Base "ufficiale" già usata dai test
from app.auth.models import Base  # noqa: F401


class DatabaseSessionProtocol(Protocol):
    async def __call__(self) -> AsyncGenerator[AsyncSession, None]: ...


class DatabaseManager:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or get_settings().database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
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
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session() as session:
            yield session


_db_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_database_manager().get_session():
        yield session
# END FILE
