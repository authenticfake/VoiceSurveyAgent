"""
Tests for authentication API router.

REQ-002: OIDC authentication integration
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from app.auth.models import User
from app.auth.schemas import OIDCTokenResponse, OIDCUserInfo


class TestAuthRouter:
    """Tests for authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_login_endpoint(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test login endpoint returns authorization URL."""
        response = await async_client.get("/api/auth/login")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert len(data["state"]) > 0

    @pytest.mark.asyncio
    async def test_callback_endpoint_invalid_state(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test callback with invalid state."""
        response = await async_client.get(
            "/api/auth/callback",
            params={"code": "auth-code", "state": "invalid-state"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"]["code"] == "INVALID_STATE"

    @pytest.mark.asyncio
    async def test_callback_endpoint_success(
        self,
        async_client: AsyncClient,
        mock_oidc_token_response: OIDCTokenResponse,
        mock_oidc_userinfo: OIDCUserInfo,
    ) -> None:
        """Test successful callback flow."""
        # First, initiate login to get a valid state
        login_response = await async_client.get("/api/auth/login")
        state = login_response.json()["state"]

        # Mock OIDC client methods
        with patch("app.auth.service.OIDCClient") as MockOIDCClient:
            mock_client = MagicMock()
            mock_client.exchange_code = AsyncMock(return_value=mock_oidc_token_response)
            mock_client.get_userinfo = AsyncMock(return_value=mock_oidc_userinfo)
            mock_client.generate_state.return_value = state
            mock_client.get_authorization_url.return_value = "https://idp/authorize"
            MockOIDCClient.return_value = mock_client

            response = await async_client.get(
                "/api/auth/callback",
                params={"code": "auth-code", "state": state},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert "user" in data

    @pytest.mark.asyncio
    async def test_refresh_endpoint_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        valid_refresh_token: str,
    ) -> None:
        """Test token refresh endpoint."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": valid_refresh_token},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_refresh_endpoint_invalid_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_endpoint_with_access_token(
        self,
        async_client: AsyncClient,
        valid_access_token: str,
    ) -> None:
        """Test refresh with access token fails."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": valid_access_token},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_me_endpoint_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        valid_access_token: str,
    ) -> None:
        """Test get current user profile."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert data["role"] == test_user.role

    @pytest.mark.asyncio
    async def test_me_endpoint_unauthorized(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test get profile without authentication."""
        response = await async_client.get("/api/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_health_endpoint(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test health check endpoint."""
        response = await async_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}