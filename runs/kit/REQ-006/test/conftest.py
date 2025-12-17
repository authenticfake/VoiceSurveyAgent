"""
Pytest configuration and fixtures for REQ-006 tests.

REQ-006: Contact CSV upload and parsing
"""

# --- BEGIN: resolve Base/User without depending on app.auth.models -----------------
from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

def _try_import(path: str, names: list[str]):
    mod = __import__(path, fromlist=names)
    return tuple(getattr(mod, n) for n in names)

# 1) Try common locations for Base/User across kits
_Base = None
_User = None

for mod_path, base_name, user_name in [
    ("app.auth.models", "Base", "User"),
    ("app.auth.model", "Base", "User"),
    ("app.models", "Base", "User"),
    ("app.shared.models", "Base", "User"),
]:
    try:
        _Base, _User = _try_import(mod_path, [base_name, user_name])
        break
    except Exception:
        continue

# 2) Fallback Base/User for tests (keeps REQ-006 isolated)
if _Base is None:
    class Base(DeclarativeBase):
        pass
else:
    Base = _Base  # type: ignore[misc]

if _User is None:
    class User(Base):  # type: ignore[misc]
        __tablename__ = "users"

        id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
        oidc_sub = Column(String(255), nullable=False, unique=True)
        email = Column(String(255), nullable=False)
        name = Column(String(255), nullable=False)
        role = Column(String(50), nullable=False)
else:
    User = _User  # type: ignore[misc]
# --- END: resolve Base/User ---------------------------------------------------------


import os
import sys
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REQ006_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "app"))

# Assicura che REQ-006 abbia priorità nella ricerca dei subpackage (es. app.contacts.*)
import app  # noqa: E402

if hasattr(app, "__path__"):
    paths = list(app.__path__)
    if REQ006_APP in paths:
        paths.remove(REQ006_APP)
    paths.insert(0, REQ006_APP)
    app.__path__[:] = paths

# Se app.contacts era già stato risolto altrove, lo eliminiamo così verrà ricaricato correttamente
sys.modules.pop("app.contacts", None)

# MODELS: IMPORTANT
# Base viene dai modelli auth (kit precedenti). La FK in Campaign punta a email_templates:
# dobbiamo registrare email.models prima del create_all, altrimenti NoReferencedTableError.

from app.campaigns.models import Campaign  # noqa: E402
from app.contacts.models import Contact  # noqa: E402
from app.shared.database import get_db_session  # noqa: E402


# Use test database URL or fallback to SQLite for unit tests.
# IMPORTANT: PostgreSQL in unit tests tende a lasciare enum/types e dare drop_all "dependent objects",
# oltre a causare UniqueViolation se non isoli correttamente. Per i test unit REQ-006 usiamo SQLite.
_env_url = os.environ.get("TEST_DATABASE_URL")
if _env_url and _env_url.startswith("postgres"):
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
else:
    TEST_DATABASE_URL = _env_url or "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

import pytest_asyncio

    
@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        oidc_sub=f"test|{uuid4()}",
        email="testuser@example.com",
        name="Test User",
        role="campaign_manager",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a test viewer user."""
    user = User(
        id=uuid4(),
        oidc_sub=f"test|{uuid4()}",
        email="viewer@example.com",
        name="Viewer User",
        role="viewer",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Create authentication headers for test user."""
    return {
        "Authorization": f"Bearer test_token_{test_user.id}",
        "X-Test-User-Id": str(test_user.id),
        "X-Test-User-Role": test_user.role,
    }


@pytest.fixture
def viewer_auth_headers(viewer_user: User) -> dict[str, str]:
    """Create authentication headers for viewer user."""
    return {
        "Authorization": f"Bearer test_token_{viewer_user.id}",
        "X-Test-User-Id": str(viewer_user.id),
        "X-Test-User-Role": viewer_user.role,
    }


@pytest.fixture(autouse=True)
def override_db_session(db_session: AsyncSession):
    """Override the database session dependency for tests."""
    from app.main import app

    async def get_test_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = get_test_db_session
    yield
    app.dependency_overrides.clear()
