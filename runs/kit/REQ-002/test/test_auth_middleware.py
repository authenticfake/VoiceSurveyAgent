"""
Unit tests for authentication middleware.

Tests JWT validation middleware for FastAPI requests.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.exceptions import InvalidTokenError, MissingTokenError
from app.auth.middleware import AuthMiddleware, get_current_user
from app.auth.schemas import UserContext, UserRole


@pytest.fixture
def mock_request():
    """Create mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_credentials():
    """Create mock HTTP credentials."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def auth_middleware():
    """Create auth middleware instance."""
    return AuthMiddleware()


class TestAuthMiddleware:
    """Tests for AuthMiddleware."""

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_error(
        self,
        auth_middleware,
        mock_request,
        mock_db_session,
    ):
        """Test that missing credentials raises MissingTokenError."""
        with pytest.raises(MissingTokenError):
            await auth_middleware(mock_request, None, mock_db_session)

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_context(
        self,
        auth_middleware,
        mock_request,
        mock_credentials,
        mock_db_session,
    ):
        """Test that valid token returns user context."""
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

            # Reset the middleware's cached service
            auth_middleware._auth_service = None

            result = await auth_middleware(
                mock_request,
                mock_credentials,
                mock_db_session,
            )

        assert isinstance(result, UserContext)
        assert result.id == user_id
        assert result.email == "test@example.com"
        assert result.role == UserRole.VIEWER

    @pytest.mark.asyncio
    async def test_invalid_token_raises_error(
        self,
        auth_middleware,
        mock_request,
        mock_credentials,
        mock_db_session,
    ):
        """Test that invalid token raises error."""
        with patch("app.auth.middleware.AuthService") as MockAuthService:
            mock_service = AsyncMock()
            mock_service.validate_token.side_effect = InvalidTokenError()
            MockAuthService.return_value = mock_service

            # Reset the middleware's cached service
            auth_middleware._auth_service = None

            with pytest.raises(InvalidTokenError):
                await auth_middleware(
                    mock_request,
                    mock_credentials,
                    mock_db_session,
                )

    @pytest.mark.asyncio
    async def test_sets_request_state(
        self,
        auth_middleware,
        mock_request,
        mock_credentials,
        mock_db_session,
    ):
        """Test that user info is set on request state."""
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.oidc_sub = "test-sub"
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.role = "admin"

        mock_token_payload = MagicMock()
        mock_token_payload.sub = "test-sub"
        mock_token_payload.email = "test@example.com"
        mock_token_payload.name = "Test User"

        with patch("app.auth.middleware.AuthService") as MockAuthService:
            mock_service = AsyncMock()
            mock_service.validate_token.return_value = mock_token_payload
            mock_service.get_or_create_user.return_value = mock_user
            MockAuthService.return_value = mock_service

            auth_middleware._auth_service = None

            await auth_middleware(
                mock_request,
                mock_credentials,
                mock_db_session,
            )

        assert mock_request.state.user_id == str(user_id)
        assert mock_request.state.user_role == "admin"