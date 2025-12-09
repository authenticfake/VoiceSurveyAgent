"""
Pytest configuration and fixtures for REQ-006 tests.

REQ-006: Contact CSV upload and parsing
"""

import os
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.auth.models import Base, User
from app.campaigns.models import Campaign
from app.contacts.models import Contact
from app.shared.database import get_db_session


# Use test database URL or fallback to SQLite for unit tests
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)


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
        oidc_sub="test|user123",
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
        oidc_sub="test|viewer123",
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
    """Create authentication headers for test user.

    Note: In a real test environment, this would generate a valid JWT.
    For unit tests, we mock the authentication middleware.
    """
    # This is a placeholder - actual implementation depends on auth setup
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


# Override database session dependency for tests
@pytest.fixture(autouse=True)
def override_db_session(db_session: AsyncSession):
    """Override the database session dependency for tests."""
    from app.main import app

    async def get_test_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = get_test_db_session
    yield
    app.dependency_overrides.clear()