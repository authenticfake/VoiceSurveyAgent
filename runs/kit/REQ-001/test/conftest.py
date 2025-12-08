"""Pytest configuration and fixtures for REQ-001 tests."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.domain import User, UserRole
from app.auth.oidc import OIDCClient, OIDCConfig, TokenPayload
from app.auth.repository import InMemoryUserRepository


@pytest.fixture(scope="session", autouse=True)
def set_test_env() -> Generator[None, None, None]:
    """Set test environment variables."""
    os.environ["SKIP_OIDC_DISCOVERY"] = "true"
    os.environ["OIDC_ISSUER"] = "https://test.example.com/"
    os.environ["OIDC_CLIENT_ID"] = "test-client-id"
    os.environ["OIDC_CLIENT_SECRET"] = "test-client-secret"
    os.environ["OIDC_REDIRECT_URI"] = "http://localhost:8000/api/auth/callback"
    yield


@pytest.fixture
def oidc_config() -> OIDCConfig:
    """Create test OIDC configuration."""
    return OIDCConfig(
        issuer="https://test.example.com/",
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:8000/api/auth/callback",
        authorization_endpoint="https://test.example.com/authorize",
        token_endpoint="https://test.example.com/oauth/token",
        userinfo_endpoint="https://test.example.com/userinfo",
        jwks_uri="https://test.example.com/.well-known/jwks.json",
    )


@pytest.fixture
def mock_oidc_client(oidc_config: OIDCConfig) -> OIDCClient:
    """Create mock OIDC client."""
    client = OIDCClient(oidc_config)
    return client


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    """Create in-memory user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def sample_user() -> User:
    """Create sample user for testing."""
    return User(
        id=uuid.uuid4(),
        oidc_sub="test-sub-123",
        email="test@example.com",
        name="Test User",
        role=UserRole.VIEWER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def admin_user() -> User:
    """Create admin user for testing."""
    return User(
        id=uuid.uuid4(),
        oidc_sub="admin-sub-456",
        email="admin@example.com",
        name="Admin User",
        role=UserRole.ADMIN,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def campaign_manager_user() -> User:
    """Create campaign manager user for testing."""
    return User(
        id=uuid.uuid4(),
        oidc_sub="manager-sub-789",
        email="manager@example.com",
        name="Campaign Manager",
        role=UserRole.CAMPAIGN_MANAGER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def token_payload() -> TokenPayload:
    """Create sample token payload."""
    return TokenPayload(
        sub="test-sub-123",
        email="test@example.com",
        name="Test User",
        exp=9999999999,
        iat=1000000000,
        iss="https://test.example.com/",
        aud="test-client-id",
    )


@pytest.fixture
def test_app(
    mock_oidc_client: OIDCClient,
    user_repository: InMemoryUserRepository,
) -> FastAPI:
    """Create test FastAPI application."""
    from app.api.http.auth import router as auth_router
    from app.api.http.protected import router as protected_router

    app = FastAPI()
    app.state.oidc_client = mock_oidc_client
    app.state.user_repository = user_repository

    app.include_router(auth_router, prefix="/api")
    app.include_router(protected_router, prefix="/api")

    return app


@pytest_asyncio.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_valid_token() -> str:
    """Return a mock valid token string."""
    return "mock-valid-access-token"