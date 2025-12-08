"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.auth.models import Base, User, UserRole
from app.config import Settings
from app.main import create_app
from app.shared.database import get_db_session

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_settings() -> Settings:
    """Test settings with in-memory database."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer_url="https://test.auth0.com",
        oidc_client_id="test-client-id",
        oidc_client_secret="test-client-secret",
        jwt_secret_key="test-secret-key-for-testing-only",
        debug=True,
    )

@pytest_asyncio.fixture
async def db_engine(test_settings: Settings) -> AsyncGenerator[Any, None]:
    """Create test database engine."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        oidc_sub="test-oidc-sub-123",
        email="test@example.com",
        name="Test User",
        role=UserRole.CAMPAIGN_MANAGER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        id=uuid4(),
        oidc_sub="admin-oidc-sub-456",
        email="admin@example.com",
        name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a viewer test user."""
    user = User(
        id=uuid4(),
        oidc_sub="viewer-oidc-sub-789",
        email="viewer@example.com",
        name="Viewer User",
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    app = create_app()

    # Override database session dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

@pytest.fixture
def auth_headers(test_user: User, test_settings: Settings) -> dict[str, str]:
    """Create authorization headers with valid token."""
    from app.auth.jwt import JWTHandler

    jwt_handler = JWTHandler(test_settings)
    token = jwt_handler.create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        role=test_user.role.value,
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_auth_headers(admin_user: User, test_settings: Settings) -> dict[str, str]:
    """Create authorization headers for admin user."""
    from app.auth.jwt import JWTHandler

    jwt_handler = JWTHandler(test_settings)
    token = jwt_handler.create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        role=admin_user.role.value,
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def viewer_auth_headers(viewer_user: User, test_settings: Settings) -> dict[str, str]:
    """Create authorization headers for viewer user."""
    from app.auth.jwt import JWTHandler

    jwt_handler = JWTHandler(test_settings)
    token = jwt_handler.create_access_token(
        user_id=viewer_user.id,
        email=viewer_user.email,
        role=viewer_user.role.value,
    )
    return {"Authorization": f"Bearer {token}"}