# runs/kit/REQ-007/test/conftest.py
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)


def _db_url() -> str:
    # usa env var se presente, altrimenti default locale
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://afranco:Andrea.1@localhost:5432/voicesurveyagent",
    )


@pytest_asyncio.fixture(scope="session")
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        _db_url(),
        echo=False,
        pool_pre_ping=True,
    )
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    1 test = 1 conn + 1 transazione esterna
    dentro una SAVEPOINT (nested) così anche se il codice fa commit,
    noi ripartiamo con una nuova SAVEPOINT e a fine test rollback totale.
    """
    async with async_engine.connect() as conn:
        trans = await conn.begin()

        session = AsyncSession(bind=conn, expire_on_commit=False)

        await conn.begin_nested()

        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_savepoint(sess, transaction) -> None:  # pragma: no cover
            # Quando finisce una SAVEPOINT, ne riapriamo un'altra automaticamente
            if transaction.nested and not transaction._parent.nested:
                conn.sync_connection.begin_nested()

        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
