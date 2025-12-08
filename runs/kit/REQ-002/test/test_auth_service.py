"""
Unit tests for authentication service.

Tests OIDC flow, JWT validation, and user management.
"""

import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from jose import jwt

from app.auth.exceptions import (
    ExpiredTokenError,
    InvalidStateError,
    InvalidTokenError,
    OIDCError,
)
from app.auth.schemas import TokenPayload, UserRole
from app.auth.service import AuthService


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
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
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def auth_service(mock_settings, mock_db_session):
    """Create auth service instance."""
    return AuthService(settings=mock_settings, db_session=mock_db_session)


class TestGenerateAuthorizationUrl:
    """Tests for authorization URL generation."""

    def test_generates_valid_url(self, auth_service):
        """Test that authorization URL is generated correctly."""
        url, state = auth_service.generate_authorization_url()

        assert "https://idp.example.com/authorize" in url
        assert "client_id=test-client-id" in url
        assert "response_type=code" in url
        assert "scope=openid+profile+email" in url or "scope=openid%20profile%20email" in url
        assert f"state={state}" in url
        assert len(state) > 20  # State should be sufficiently random

    def test_generates_unique_states(self, auth_service):
        """Test that each call generates unique state."""
        _, state1 = auth_service.generate_authorization_url()
        _, state2 = auth_service.generate_authorization_url()

        assert state1 != state2

    def test_custom_redirect_url(self, auth_service):
        """Test custom redirect URL override."""
        custom_url = "http://custom.example.com/callback"
        url, _ = auth_service.generate_authorization_url(redirect_url=custom_url)

        assert custom_url in url


class TestValidateState:
    """Tests for CSRF state validation."""

    def test_valid_state(self, auth_service):
        """Test validation of valid state."""
        _, state = auth_service.generate_authorization_url()

        assert auth_service.validate_state(state) is True

    def test_invalid_state(self, auth_service):
        """Test validation of invalid state."""
        assert auth_service.validate_state("invalid-state") is False

    def test_state_consumed_after_validation(self, auth_service):
        """Test that state can only be used once."""
        _, state = auth_service.generate_authorization_url()

        assert auth_service.validate_state(state) is True
        assert auth_service.validate_state(state) is False

    def test_expired_state(self, auth_service):
        """Test that expired state is rejected."""
        _, state = auth_service.generate_authorization_url()

        # Manually expire the state
        auth_service._state_store[state] = datetime.now(timezone.utc) - timedelta(minutes=1)

        assert auth_service.validate_state(state) is False


class TestExchangeCodeForTokens:
    """Tests for token exchange."""

    @pytest.mark.asyncio
    async def test_invalid_state_raises_error(self, auth_service):
        """Test that invalid state raises error."""
        with pytest.raises(InvalidStateError):
            await auth_service.exchange_code_for_tokens(
                code="test-code",
                state="invalid-state",
            )

    @pytest.mark.asyncio
    async def test_successful_exchange(self, auth_service):
        """Test successful token exchange."""
        _, state = auth_service.generate_authorization_url()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "test-refresh-token",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(auth_service, "_jwks_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await auth_service.exchange_code_for_tokens(
                code="test-code",
                state=state,
            )

        assert result["access_token"] == "test-access-token"
        assert result["refresh_token"] == "test-refresh-token"


class TestValidateToken:
    """Tests for JWT token validation."""

    @pytest.fixture
    def mock_jwks(self):
        """Create mock JWKS response."""
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "test-key-id",
                    "use": "sig",
                    "n": "test-n",
                    "e": "AQAB",
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_invalid_token_format(self, auth_service):
        """Test that invalid token format raises error."""
        with pytest.raises(InvalidTokenError):
            await auth_service.validate_token("not-a-valid-jwt")

    @pytest.mark.asyncio
    async def test_missing_key_raises_error(self, auth_service, mock_jwks):
        """Test that missing key raises error."""
        # Create a token with unknown kid
        token = jwt.encode(
            {"sub": "test", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "secret",
            algorithm="HS256",
            headers={"kid": "unknown-key-id"},
        )

        with patch.object(auth_service, "_fetch_jwks", return_value=mock_jwks):
            with pytest.raises(InvalidTokenError, match="Unable to find matching key"):
                await auth_service.validate_token(token)


class TestGetOrCreateUser:
    """Tests for user creation and retrieval."""

    @pytest.mark.asyncio
    async def test_creates_new_user(self, auth_service, mock_db_session):
        """Test that new user is created when not found."""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        token_payload = TokenPayload(
            sub="new-user-sub",
            email="new@example.com",
            name="New User",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            iss="https://idp.example.com",
            aud="test-client-id",
        )

        user = await auth_service.get_or_create_user(token_payload)

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_returns_existing_user(self, auth_service, mock_db_session):
        """Test that existing user is returned."""
        existing_user = MagicMock()
        existing_user.id = uuid4()
        existing_user.oidc_sub = "existing-sub"
        existing_user.email = "existing@example.com"
        existing_user.name = "Existing User"
        existing_user.role = "viewer"

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_user

        token_payload = TokenPayload(
            sub="existing-sub",
            email="existing@example.com",
            name="Existing User",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            iss="https://idp.example.com",
            aud="test-client-id",
        )

        user = await auth_service.get_or_create_user(token_payload)

        assert user == existing_user
        mock_db_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_user_info_if_changed(self, auth_service, mock_db_session):
        """Test that user info is updated if changed."""
        existing_user = MagicMock()
        existing_user.id = uuid4()
        existing_user.oidc_sub = "existing-sub"
        existing_user.email = "old@example.com"
        existing_user.name = "Old Name"
        existing_user.role = "viewer"

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_user

        token_payload = TokenPayload(
            sub="existing-sub",
            email="new@example.com",
            name="New Name",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            iss="https://idp.example.com",
            aud="test-client-id",
        )

        await auth_service.get_or_create_user(token_payload)

        assert existing_user.email == "new@example.com"
        assert existing_user.name == "New Name"
        mock_db_session.commit.assert_called()