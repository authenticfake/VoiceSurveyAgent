"""Tests for authentication middleware."""

import pytest
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import JWTHandler
from app.auth.models import User, UserRole
from app.config import Settings

class TestAuthMiddleware:
    """Tests for authentication middleware."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header(
        self, client: AsyncClient
    ) -> None:
        """Test request without authorization header returns 401."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_token_format(self, client: AsyncClient) -> None:
        """Test request with invalid token format returns 401."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "InvalidFormat token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token(
        self,
        client: AsyncClient,
        test_user: User,
        test_settings: Settings,
    ) -> None:
        """Test request with expired token returns 401."""
        # Create settings with very short expiry
        expired_settings = Settings(
            database_url=test_settings.database_url,
            jwt_secret_key=test_settings.jwt_secret_key,
            jwt_access_token_expire_minutes=-1,  # Already expired
        )
        jwt_handler = JWTHandler(expired_settings)

        # This will create a token that's already expired
        import jwt
        from datetime import datetime, timedelta, timezone

        payload = {
            "sub": str(test_user.id),
            "email": test_user.email,
            "role": test_user.role.value,
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            payload,
            test_settings.jwt_secret_key,
            algorithm="HS256",
        )

        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_token_for_nonexistent_user(
        self,
        client: AsyncClient,
        test_settings: Settings,
    ) -> None:
        """Test request with token for non-existent user returns 401."""
        jwt_handler = JWTHandler(test_settings)
        token = jwt_handler.create_access_token(
            user_id=uuid4(),  # Non-existent user
            email="nonexistent@example.com",
            role=UserRole.VIEWER.value,
        )

        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Test request with valid token returns user data."""
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email