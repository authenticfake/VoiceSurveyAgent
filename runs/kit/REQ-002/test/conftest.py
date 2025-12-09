"""
Pytest configuration and fixtures for REQ-002 tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.jwt import JWTService
from app.auth.models import Base, User
from app.auth.oidc import OIDCClient
from app.auth.repository import UserRepository
from app.auth.schemas import OIDCTokenResponse, OIDCUserInfo
from app.auth.service import AuthService
from app.config import Settings
from app.main import app
from app.shared.database import get_db_session


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        app_env="dev",
        debug=True,
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer_url="https://test-idp.example.com",
        oidc_client_id="test-client",
        oidc_client_secret="test-secret",
        oidc_redirect_uri="http://localhost:8000/api/auth/callback",
        jwt_secret_key="test-secret-key-for-testing-only",
        jwt_access_token_expire_minutes=60,
        jwt_refresh_token_expire_days=7,
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
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session


@pytest.fixture
def test_user_data() -> dict[str, Any]:
    """Test user data."""
    return {
        "id": uuid4(),
        "oidc_sub": "oidc|test123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "campaign_manager",
    }


@pytest_asyncio.fixture
async def test_user(
    db_session: AsyncSession,
    test_user_data: dict[str, Any],
) -> User:
    """Create test user in database."""
    user = User(
        id=test_user_data["id"],
        oidc_sub=test_user_data["oidc_sub"],
        email=test_user_data["email"],
        name=test_user_data["name"],
        role=test_user_data["role"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def jwt_service(test_settings: Settings) -> JWTService:
    """Create JWT service with test settings."""
    return JWTService(settings=test_settings)


@pytest.fixture
def mock_oidc_client() -> MagicMock:
    """Create mock OIDC client."""
    client = MagicMock(spec=OIDCClient)
    client.generate_state.return_value = "test-state-12345"
    client.get_authorization_url.return_value = (
        "https://test-idp.example.com/authorize?client_id=test"
    )
    return client


@pytest.fixture
def mock_oidc_token_response() -> OIDCTokenResponse:
    """Create mock OIDC token response."""
    return OIDCTokenResponse(
        access_token="oidc-access-token",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="oidc-refresh-token",
        id_token="oidc-id-token",
    )


@pytest.fixture
def mock_oidc_userinfo() -> OIDCUserInfo:
    """Create mock OIDC userinfo response."""
    return OIDCUserInfo(
        sub="oidc|test123",
        email="test@example.com",
        email_verified=True,
        name="Test User",
        preferred_username="testuser",
    )


@pytest.fixture
def user_repository(db_session: AsyncSession) -> UserRepository:
    """Create user repository."""
    return UserRepository(session=db_session)


@pytest_asyncio.fixture
async def auth_service(
    db_session: AsyncSession,
    test_settings: Settings,
    mock_oidc_client: MagicMock,
) -> AuthService:
    """Create auth service with mocked OIDC client."""
    return AuthService(
        session=db_session,
        settings=test_settings,
        oidc_client=mock_oidc_client,
    )


@pytest.fixture
def valid_access_token(
    jwt_service: JWTService,
    test_user_data: dict[str, Any],
) -> str:
    """Create valid access token."""
    return jwt_service.create_access_token(
        user_id=test_user_data["id"],
        oidc_sub=test_user_data["oidc_sub"],
        email=test_user_data["email"],
        role=test_user_data["role"],
    )


@pytest.fixture
def valid_refresh_token(
    jwt_service: JWTService,
    test_user_data: dict[str, Any],
) -> str:
    """Create valid refresh token."""
    return jwt_service.create_refresh_token(
        user_id=test_user_data["id"],
        oidc_sub=test_user_data["oidc_sub"],
    )


@pytest.fixture
def expired_access_token(test_settings: Settings, test_user_data: dict[str, Any]) -> str:
    """Create expired access token."""
    import jwt

    now = datetime.now(timezone.utc)
    payload = {
        "sub": test_user_data["oidc_sub"],
        "exp": now - timedelta(hours=1),  # Expired
        "iat": now - timedelta(hours=2),
        "type": "access",
        "user_id": str(test_user_data["id"]),
        "email": test_user_data["email"],
        "role": test_user_data["role"],
    }
    return jwt.encode(
        payload,
        test_settings.jwt_secret_key,
        algorithm=test_settings.jwt_algorithm,
    )


@pytest_asyncio.fixture
async def async_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API tests."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()