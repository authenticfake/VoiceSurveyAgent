from __future__ import annotations

import os
import shutil
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine


print(">>> LOADED REQ-007 conftest <<<")


def _bootstrap_combined_src() -> None:
    """
    Clike / Harper kit testing:
    - REQ-007 contiene solo il delta (es. app.contacts.exclusions)
    - le dipendenze (REQ<=006) stanno in ./src (promosso)
    Quindi creiamo un "combined src" = src promosso + overlay del kit,
    e lo mettiamo PRIMO in sys.path.
    """
    here = Path(__file__).resolve()
    kit_root = here.parents[1]          # .../runs/kit/REQ-007
    project_root = here.parents[4]      # repo root

    promoted_src = project_root / "src"
    kit_src = kit_root / "src"
    combined_src = kit_root / ".combined_src"

    if not promoted_src.exists():
        raise RuntimeError(f"Promoted src not found: {promoted_src}")
    if not kit_src.exists():
        raise RuntimeError(f"Kit src not found: {kit_src}")

    if not combined_src.exists():
        combined_src.mkdir(parents=True, exist_ok=True)
        shutil.copytree(promoted_src, combined_src, dirs_exist_ok=True)
        shutil.copytree(kit_src, combined_src, dirs_exist_ok=True)

    sys.path.insert(0, str(combined_src))

    # reset eventuali import sporchi di app
    for name in list(sys.modules.keys()):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


_bootstrap_combined_src()


def _db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://afranco:Andrea.1@localhost:5432/voicesurveyagent",
    )


@pytest_asyncio.fixture(scope="function")
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    # NullPool evita riuso connessione tra loop diversi
    engine = create_async_engine(_db_url(), poolclass=NullPool, echo=False)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(
    async_engine: AsyncEngine, setup_database: None
) -> AsyncGenerator[AsyncSession, None]:
    async with async_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest_asyncio.fixture
async def async_session(async_engine):
    async with async_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


from app.auth.models import Base
from app.email.models import EmailTemplate  # noqa: F401  (se non è già importato da infra.db.models)


# @pytest_asyncio.fixture
# async def setup_database(async_engine):
#     """
#     Create and drop all tables for each test.
#     All ORM models MUST be imported so metadata knows FK dependencies.
#     """

#     # Register ALL tables in metadata
#     from app.contacts.models import Contact  # noqa: F401
#     from app.campaigns.models import Campaign  # noqa: F401
#     from app.email.models import EmailTemplate  # noqa: F401

#     async with async_engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)
#         await conn.run_sync(Base.metadata.create_all)

@pytest_asyncio.fixture(scope="function")
async def setup_database(async_engine: AsyncEngine) -> None:
    """
    Recreate DB schema for each test function.
    Ensures DB schema matches ORM models (incl. new columns like completion_message).
    """

    # IMPORTANT: import all models so Base.metadata is complete
    from app.auth.models import Base
    from app.campaigns.models import Campaign  # noqa: F401
    from app.contacts.models import Contact  # noqa: F401
    from app.email.models import EmailTemplate  # noqa: F401
    from app.contacts.exclusions.models import ExclusionListEntry  # noqa: F401

    from sqlalchemy import text
    from uuid import uuid4

    async with async_engine.begin() as conn:
        # Schema dedicato per il singolo run di test (niente privilegi su public necessari)
        schema = f"test_{uuid4().hex}"

        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.execute(text(f'SET search_path TO "{schema}"'))

        # Crea tutte le tabelle nello schema di test
        await conn.run_sync(Base.metadata.create_all)

        # IMPORTANT: assicurati che anche le query successive usino lo stesso schema.
        # (search_path resta valido su questa connessione/transaction)
        yield

        # Cleanup schema a fine test (qui sei owner, quindi ok)
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))