"""
Tests for authentication middleware.

REQ-002: OIDC authentication integration
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.auth.models import User


class TestAuthMiddleware:
    """Tests for authentication middleware."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that protected endpoints require authentication."""
        response = await async_client.get("/api/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"]["code"] == "MISSING_TOKEN"

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(
        self,
        async_client: AsyncClient,
        test_user: User,
        valid_access_token: str,
    ) -> None:
        """Test that valid tokens allow access."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["role"] == test_user.role

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_expired_token(
        self,
        async_client: AsyncClient,
        expired_access_token: str,
    ) -> None:
        """Test that expired tokens are rejected."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_access_token}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"]["code"] == "TOKEN_EXPIRED"

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that invalid tokens are rejected."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"]["code"] == "INVALID_TOKEN"

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_refresh_token(
        self,
        async_client: AsyncClient,
        valid_refresh_token: str,
    ) -> None:
        """Test that refresh tokens cannot be used for API access."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_refresh_token}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"]["code"] == "INVALID_TOKEN"