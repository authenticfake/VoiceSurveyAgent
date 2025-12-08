"""Tests for authentication router."""

import pytest
from httpx import AsyncClient

from app.auth.models import User

class TestAuthRouter:
    """Tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient) -> None:
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_login_returns_authorization_url(
        self, client: AsyncClient
    ) -> None:
        """Test login endpoint returns authorization URL."""
        response = await client.get("/api/auth/login")
        assert response.status_code == 200

        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert len(data["state"]) > 0

    @pytest.mark.asyncio
    async def test_callback_invalid_state(self, client: AsyncClient) -> None:
        """Test callback with invalid state returns error."""
        response = await client.get(
            "/api/auth/callback",
            params={"code": "test-code", "state": "invalid-state"},
        )
        assert response.status_code == 400
        assert "Invalid or expired state" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(
        self, client: AsyncClient
    ) -> None:
        """Test getting current user without auth returns 401."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting current user with valid token."""
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert data["role"] == test_user.role.value

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_token(
        self, client: AsyncClient
    ) -> None:
        """Test getting current user with invalid token returns 401."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(
        self, client: AsyncClient
    ) -> None:
        """Test refresh with invalid token returns 401."""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-refresh-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test logout endpoint."""
        response = await client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 204