"""
Tests for authentication router.

Tests API endpoints for OIDC authentication flow.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import jwt
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.schemas import UserRole
from app.campaigns.models import User, UserRoleEnum
from app.config import Settings


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        database_url="postgresql://test:test@localhost:5432/test",
        oidc_issuer="https://auth.example.com",
        oidc_client_id="test-client",
        oidc_client_secret="test-secret",
        oidc_redirect_uri="http://localhost:8000/api/auth/callback",
        jwt_secret_key="test-secret-key-for-testing-only",
        jwt_algorithm="HS256",
        jwt_expiration_minutes=60,
        jwt_issuer="voicesurveyagent",
        jwt_audience="voicesurveyagent-api",
    )


@pytest.fixture
def valid_token(mock_settings: Settings) -> str:
    """Create a valid JWT token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "test-user-sub",
        "iat": now.timestamp(),
        "exp": (now + timedelta(hours=1)).timestamp(),
        "iss": "voicesurveyagent",
        "aud": "voicesurveyagent-api",
        "email": "test@example.com",
        "name": "Test User",
        "role": "campaign_manager",
        "user_id": str(uuid4()),
    }
    return jwt.encode(payload, mock_settings.jwt_secret_key, algorithm="HS256")


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app."""
    from app.main import app
    return app


class TestLoginEndpoint:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    async def test_login_initiates_oidc_flow(self, app: FastAPI) -> None:
        """Test login endpoint returns authorization URL."""
        oidc_discovery = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "userinfo_endpoint": "https://auth.example.com/userinfo",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
        }

        with patch("app.auth.service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = oidc_discovery
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("app.auth.service.PyJWKClient"):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/auth/login")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert "https://auth.example.com/authorize" in data["authorization_url"]


class TestProfileEndpoint:
    """Tests for profile endpoint."""

    @pytest.mark.asyncio
    async def test_get_profile_authenticated(
        self,
        app: FastAPI,
        mock_settings: Settings,
        valid_token: str,
    ) -> None:
        """Test getting profile for authenticated user."""
        user_id = uuid4()
        mock_user = User(
            id=user_id,
            oidc_sub="test-user-sub",
            email="test@example.com",
            name="Test User",
            role=UserRoleEnum.CAMPAIGN_MANAGER,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.auth.middleware.get_db_session") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result

            async def mock_session_gen():
                yield mock_db

            mock_get_db.return_value = mock_session_gen()

            with patch("app.config.get_settings", return_value=mock_settings):
                with patch("app.auth.router.get_auth_service") as mock_auth_service:
                    mock_service = AsyncMock()
                    mock_service.get_user_by_id.return_value = mock_user
                    mock_auth_service.return_value = mock_service

                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
                        response = await client.get(
                            "/api/auth/me",
                            headers={"Authorization": f"Bearer {valid_token}"},
                        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "campaign_manager"

    @pytest.mark.asyncio
    async def test_get_profile_unauthenticated(self, app: FastAPI) -> None:
        """Test getting profile without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/auth/me")

        assert response.status_code == 401


class TestLogoutEndpoint:
    """Tests for logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_authenticated(
        self,
        app: FastAPI,
        mock_settings: Settings,
        valid_token: str,
    ) -> None:
        """Test logout for authenticated user."""
        mock_user = User(
            id=uuid4(),
            oidc_sub="test-user-sub",
            email="test@example.com",
            name="Test User",
            role=UserRoleEnum.CAMPAIGN_MANAGER,
        )

        with patch("app.auth.middleware.get_db_session") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result

            async def mock_session_gen():
                yield mock_db

            mock_get_db.return_value = mock_session_gen()

            with patch("app.config.get_settings", return_value=mock_settings):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.post(
                        "/api/auth/logout",
                        headers={"Authorization": f"Bearer {valid_token}"},
                    )

        assert response.status_code == 204