# BEGIN FILE: runs/kit/REQ-007/test/conftest.py
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
    Ensure PYTHONPATH resolution matches the project approach:
    - promoted code lives in repo ./src
    - kit code lives in runs/kit/REQ-007/src
    - tests should import from a combined folder where kit overrides promoted
    """
    here = Path(__file__).resolve()
    kit_root = here.parents[1]  # .../runs/kit/REQ-007
    project_root = here.parents[4]  # repo root

    promoted_src = project_root / "src"
    kit_src = kit_root / "src"
    combined_src = kit_root / ".combined_src"

    if not promoted_src.exists():
        raise RuntimeError(f"Promoted src not found: {promoted_src}")
    if not kit_src.exists():
        raise RuntimeError(f"Kit src not found: {kit_src}")

    # Rebuild combined_src each run to avoid stale imports
    if combined_src.exists():
        shutil.rmtree(combined_src, ignore_errors=True)
    combined_src.mkdir(parents=True, exist_ok=True)

    # Copy promoted first, then overlay kit
    shutil.copytree(promoted_src, combined_src, dirs_exist_ok=True)
    shutil.copytree(kit_src, combined_src, dirs_exist_ok=True)

    sys.path.insert(0, str(combined_src))

    # Reset eventuali import sporchi di app
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
async def setup_database(async_engine: AsyncEngine) -> AsyncGenerator[str, None]:
    """
    Create a dedicated schema for each test function and create all tables inside it.

    NOTE: The schema must be visible to *other* connections (sessions open their own
    connections), therefore we COMMIT the schema/table creation before yielding.
    """
    # IMPORTANT: import all models so Base.metadata is complete
    from uuid import uuid4

    from app.auth.models import Base
    from app.campaigns.models import Campaign  # noqa: F401
    from app.contacts.models import Contact  # noqa: F401
    from app.contacts.exclusions.models import ExclusionListEntry  # noqa: F401
    from app.email.models import EmailTemplate  # noqa: F401

    schema = f"test_{uuid4().hex}"

    async with async_engine.connect() as conn:
        # Create schema + tables and COMMIT so other connections can see them
        trans = await conn.begin()
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.execute(text(f'SET search_path TO "{schema}"'))
        await conn.run_sync(Base.metadata.create_all)
        await trans.commit()

    try:
        yield schema
    finally:
        async with async_engine.connect() as conn:
            trans = await conn.begin()
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            await trans.commit()


# BEGIN PATCH: runs/kit/REQ-007/test/conftest.py

@pytest_asyncio.fixture(scope="function")
async def db_session(
    async_engine: AsyncEngine, setup_database: str
) -> AsyncGenerator[AsyncSession, None]:
    async with async_engine.connect() as conn:
        trans = await conn.begin()  # <-- PRIMA begin()
        await conn.execute(text(f'SET search_path TO "{setup_database}"'))  # <-- POI SET
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest_asyncio.fixture
async def async_session(
    async_engine: AsyncEngine, setup_database: str
) -> AsyncGenerator[AsyncSession, None]:
    async with async_engine.connect() as conn:
        trans = await conn.begin()  # <-- PRIMA begin()
        await conn.execute(text(f'SET search_path TO "{setup_database}"'))  # <-- POI SET
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()

# END PATCH

