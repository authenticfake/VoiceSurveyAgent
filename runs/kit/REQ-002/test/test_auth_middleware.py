"""
Tests for authentication middleware.

Tests JWT validation and user context extraction.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user, get_token_payload
from app.auth.schemas import TokenPayload, UserRole
from app.campaigns.models import User, UserRoleEnum
from app.config import Settings
from app.shared.exceptions import AuthenticationError


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        database_url="postgresql://test:test@localhost:5432/test",
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
        "role": "viewer",
    }
    return jwt.encode(payload, mock_settings.jwt_secret_key, algorithm="HS256")


@pytest.fixture
def expired_token(mock_settings: Settings) -> str:
    """Create an expired JWT token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "test-user-sub",
        "iat": (now - timedelta(hours=2)).timestamp(),
        "exp": (now - timedelta(hours=1)).timestamp(),
        "iss": "voicesurveyagent",
        "aud": "voicesurveyagent-api",
    }
    return jwt.encode(payload, mock_settings.jwt_secret_key, algorithm="HS256")


class TestGetTokenPayload:
    """Tests for token payload extraction."""

    @pytest.mark.asyncio
    async def test_valid_token(
        self,
        mock_settings: Settings,
        valid_token: str,
    ) -> None:
        """Test extracting payload from valid token."""
        result = await get_token_payload(
            authorization=f"Bearer {valid_token}",
            settings=mock_settings,
        )

        assert result.sub == "test-user-sub"
        assert result.email == "test@example.com"
        assert result.role == UserRole.VIEWER

    @pytest.mark.asyncio
    async def test_missing_authorization(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test missing authorization header."""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_token_payload(authorization=None, settings=mock_settings)

        assert "Missing authorization header" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_format(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test invalid authorization header format."""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_token_payload(
                authorization="Basic invalid",
                settings=mock_settings,
            )

        assert "Invalid authorization header format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_expired_token(
        self,
        mock_settings: Settings,
        expired_token: str,
    ) -> None:
        """Test expired token."""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_token_payload(
                authorization=f"Bearer {expired_token}",
                settings=mock_settings,
            )

        assert "Token has expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_token(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test invalid token."""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_token_payload(
                authorization="Bearer invalid-token",
                settings=mock_settings,
            )

        assert "Invalid token" in str(exc_info.value)


class TestGetCurrentUser:
    """Tests for current user extraction."""

    @pytest.mark.asyncio
    async def test_existing_user(self) -> None:
        """Test getting existing user from token."""
        user_id = uuid4()
        mock_user = User(
            id=user_id,
            oidc_sub="test-sub",
            email="test@example.com",
            name="Test User",
            role=UserRoleEnum.CAMPAIGN_MANAGER,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        token = TokenPayload(
            sub="test-sub",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            email="test@example.com",
            name="Test User",
        )

        result = await get_current_user(token=token, db=mock_db)

        assert result.id == user_id
        assert result.email == "test@example.com"
        assert result.role == UserRole.CAMPAIGN_MANAGER

    @pytest.mark.asyncio
    async def test_create_user_on_first_login(self) -> None:
        """Test creating user on first login."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        token = TokenPayload(
            sub="new-user-sub",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            email="new@example.com",
            name="New User",
        )

        result = await get_current_user(token=token, db=mock_db)

        # Verify user was added to session
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.refresh.assert_called_once()

        assert result.oidc_sub == "new-user-sub"
        assert result.role == UserRole.VIEWER  # Default role


class TestAuthEndpoints:
    """Integration tests for auth endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test FastAPI app."""
        from app.main import app
        return app

    @pytest.mark.asyncio
    async def test_health_check(self, app: FastAPI) -> None:
        """Test health check endpoint."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, app: FastAPI) -> None:
        """Test protected endpoint without token returns 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/auth/me")

        assert response.status_code == 401
        assert "AUTHENTICATION_ERROR" in response.json()["error"]["code"]