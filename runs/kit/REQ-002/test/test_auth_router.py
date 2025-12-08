"""
Integration tests for authentication router.

Tests REST endpoints for OIDC authentication flow.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import HttpUrl

from app.auth.schemas import AuthenticatedResponse, UserContext, UserRole
from app.main import app


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.app_name = "voicesurveyagent"
    settings.app_env = "test"
    settings.debug = False
    settings.log_level = "INFO"
    settings.database_url = "postgresql://test:test@localhost/test"
    settings.redis_url = "redis://localhost:6379/0"
    settings.oidc_issuer = "https://idp.example.com"
    settings.oidc_authorization_endpoint = "https://idp.example.com/authorize"
    settings.oidc_token_endpoint = "https://idp.example.com/token"
    settings.oidc_userinfo_endpoint = "https://idp.example.com/userinfo"
    settings.oidc_jwks_uri = "https://idp.example.com/.well-known/jwks.json"
    settings.oidc_client_id = "test-client-id"
    settings.oidc_client_secret = "test-client-secret"
    settings.oidc_redirect_uri = "http://localhost:8000/api/auth/callback"
    settings.oidc_scopes = ["openid", "profile", "email"]
    return settings


@pytest.fixture
async def client(mock_settings):
    """Create test client."""
    with patch("app.config.get_settings", return_value=mock_settings):
        with patch("app.auth.router.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                yield client


class TestLoginEndpoint:
    """Tests for /api/auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_returns_authorization_url(self, client, mock_settings):
        """Test that login returns authorization URL."""
        with patch("app.auth.router.get_auth_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.generate_authorization_url.return_value = (
                "https://idp.example.com/authorize?client_id=test&state=abc123",
                "abc123",
            )
            mock_get_service.return_value = mock_service

            response = await client.get("/api/auth/login")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data

    @pytest.mark.asyncio
    async def test_login_with_custom_redirect(self, client, mock_settings):
        """Test login with custom redirect URL."""
        with patch("app.auth.router.get_auth_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.generate_authorization_url.return_value = (
                "https://idp.example.com/authorize?redirect_uri=http://custom.com",
                "abc123",
            )
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/auth/login",
                params={"redirect_url": "http://custom.example.com/callback"},
            )

        assert response.status_code == 200


class TestCallbackEndpoint:
    """Tests for /api/auth/callback endpoint."""

    @pytest.mark.asyncio
    async def test_callback_success(self, client, mock_settings):
        """Test successful callback handling."""
        user_id = uuid4()
        mock_response = AuthenticatedResponse(
            access_token="test-access-token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test-refresh-token",
            user=UserContext(
                id=user_id,
                oidc_sub="test-sub",
                email="test@example.com",
                name="Test User",
                role=UserRole.VIEWER,
            ),
        )

        with patch("app.auth.router.get_auth_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.authenticate.return_value = mock_response
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/auth/callback",
                params={"code": "test-code", "state": "test-state"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test-access-token"
        assert data["user"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_callback_missing_params(self, client):
        """Test callback with missing parameters."""
        response = await client.get("/api/auth/callback")

        assert response.status_code == 422  # Validation error


class TestRefreshEndpoint:
    """Tests for /api/auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, client, mock_settings):
        """Test successful token refresh."""
        user_id = uuid4()
        mock_response = AuthenticatedResponse(
            access_token="new-access-token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="new-refresh-token",
            user=UserContext(
                id=user_id,
                oidc_sub="test-sub",
                email="test@example.com",
                name="Test User",
                role=UserRole.VIEWER,
            ),
        )

        with patch("app.auth.router.get_auth_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.refresh_tokens.return_value = mock_response
            mock_get_service.return_value = mock_service

            response = await client.post(
                "/api/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new-access-token"


class TestMeEndpoint:
    """Tests for /api/auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_me_requires_authentication(self, client):
        """Test that /me endpoint requires authentication."""
        response = await client.get("/api/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_returns_user_profile(self, client, mock_settings):
        """Test that /me returns user profile."""
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.oidc_sub = "test-sub"
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.role = "viewer"
        mock_user.created_at = "2024-01-01T00:00:00Z"

        mock_token_payload = MagicMock()
        mock_token_payload.sub = "test-sub"
        mock_token_payload.email = "test@example.com"
        mock_token_payload.name = "Test User"

        with patch("app.auth.middleware.AuthService") as MockAuthService:
            mock_service = AsyncMock()
            mock_service.validate_token.return_value = mock_token_payload
            mock_service.get_or_create_user.return_value = mock_user
            mock_service.get_user_by_id.return_value = mock_user
            MockAuthService.return_value = mock_service

            with patch("app.auth.router.AuthService", MockAuthService):
                response = await client.get(
                    "/api/auth/me",
                    headers={"Authorization": "Bearer test-token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"


class TestLogoutEndpoint:
    """Tests for /api/auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_requires_authentication(self, client):
        """Test that logout requires authentication."""
        response = await client.post("/api/auth/logout")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_success(self, client, mock_settings):
        """Test successful logout."""
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.oidc_sub = "test-sub"
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.role = "viewer"

        mock_token_payload = MagicMock()
        mock_token_payload.sub = "test-sub"
        mock_token_payload.email = "test@example.com"
        mock_token_payload.name = "Test User"

        with patch("app.auth.middleware.AuthService") as MockAuthService:
            mock_service = AsyncMock()
            mock_service.validate_token.return_value = mock_token_payload
            mock_service.get_or_create_user.return_value = mock_user
            MockAuthService.return_value = mock_service

            response = await client.post(
                "/api/auth/logout",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == 204