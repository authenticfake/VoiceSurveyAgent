"""Tests for auth service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.auth.domain import UserRole
from app.auth.errors import AuthenticationError
from app.auth.oidc import OIDCClient, OIDCConfig, TokenPayload, TokenResponse
from app.auth.repository import InMemoryUserRepository
from app.auth.service import AuthService


class TestAuthService:
    """Tests for AuthService."""

    @pytest.fixture
    def service(
        self, mock_oidc_client: OIDCClient, user_repository: InMemoryUserRepository
    ) -> AuthService:
        """Create auth service for testing."""
        return AuthService(mock_oidc_client, user_repository)

    def test_generate_state(self, service: AuthService) -> None:
        """Test state generation."""
        state1 = service.generate_state()
        state2 = service.generate_state()

        assert len(state1) > 20
        assert state1 != state2

    def test_generate_nonce(self, service: AuthService) -> None:
        """Test nonce generation."""
        nonce = service.generate_nonce()
        assert len(nonce) > 20

    def test_get_login_url(self, service: AuthService) -> None:
        """Test getting login URL."""
        url = service.get_login_url("test-state")
        assert "test-state" in url
        assert "authorize" in url

    @pytest.mark.asyncio
    async def test_handle_callback_success(self, service: AuthService) -> None:
        """Test successful callback handling."""
        mock_tokens = TokenResponse(
            access_token="access-123",
            token_type="Bearer",
            id_token="id-token-123",
        )
        mock_payload = TokenPayload(
            sub="user-sub",
            email="user@example.com",
            name="Test User",
        )

        with patch.object(
            service._oidc_client, "exchange_code", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.return_value = mock_tokens

            with patch.object(
                service._oidc_client, "validate_id_token", new_callable=AsyncMock
            ) as mock_validate:
                mock_validate.return_value = mock_payload

                user, tokens = await service.handle_callback("auth-code")

                assert user.oidc_sub == "user-sub"
                assert user.email == "user@example.com"
                assert tokens.access_token == "access-123"

    @pytest.mark.asyncio
    async def test_handle_callback_no_id_token(self, service: AuthService) -> None:
        """Test callback without ID token."""
        mock_tokens = TokenResponse(
            access_token="access-123",
            token_type="Bearer",
        )

        with patch.object(
            service._oidc_client, "exchange_code", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.return_value = mock_tokens

            with pytest.raises(AuthenticationError) as exc_info:
                await service.handle_callback("auth-code")

            assert "No ID token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_state(self, service: AuthService) -> None:
        """Test callback with invalid state."""
        with pytest.raises(AuthenticationError) as exc_info:
            await service.handle_callback(
                "code", expected_state="expected", received_state="different"
            )

        assert "Invalid state" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_callback_creates_user(self, service: AuthService) -> None:
        """Test callback creates new user."""
        mock_tokens = TokenResponse(
            access_token="access-123",
            token_type="Bearer",
            id_token="id-token-123",
        )
        mock_payload = TokenPayload(
            sub="new-user-sub",
            email="newuser@example.com",
            name="New User",
        )

        with patch.object(
            service._oidc_client, "exchange_code", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.return_value = mock_tokens

            with patch.object(
                service._oidc_client, "validate_id_token", new_callable=AsyncMock
            ) as mock_validate:
                mock_validate.return_value = mock_payload

                user, _ = await service.handle_callback("auth-code")

                # Verify user was created
                found = await service._user_repo.get_by_oidc_sub("new-user-sub")
                assert found is not None
                assert found.email == "newuser@example.com"