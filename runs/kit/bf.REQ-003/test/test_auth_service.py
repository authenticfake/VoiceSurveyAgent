"""
Tests for authentication service.

Tests JWT validation and OIDC integration.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from app.auth.schemas import TokenPayload, UserRole
from app.auth.service import AuthService
from app.shared.exceptions import AuthenticationError


@pytest.fixture
def auth_service() -> AuthService:
    """Create an AuthService instance."""
    return AuthService()


@pytest.fixture
def valid_token_payload() -> dict:
    """Create a valid token payload."""
    now = datetime.now(timezone.utc)
    return {
        "sub": "test-subject-123",
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "iss": "https://idp.example.com",
        "aud": "test-client-id",
        "email": "test@example.com",
        "name": "Test User",
        "role": "campaign_manager",
    }


class TestAuthServiceValidateToken:
    """Tests for AuthService.validate_token method."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_payload(
        self, auth_service: AuthService, valid_token_payload: dict
    ) -> None:
        """Test that valid token returns TokenPayload."""
        with patch.object(auth_service, "_get_jwks_client") as mock_jwks:
            mock_client = MagicMock()
            mock_signing_key = MagicMock()
            mock_signing_key.key = "test-key"
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks.return_value = mock_client

            with patch("app.auth.service.jwt.decode") as mock_decode:
                mock_decode.return_value = valid_token_payload

                result = await auth_service.validate_token("valid-token")

                assert isinstance(result, TokenPayload)
                assert result.sub == valid_token_payload["sub"]
                assert result.email == valid_token_payload["email"]
                assert result.role == UserRole.CAMPAIGN_MANAGER

    @pytest.mark.asyncio
    async def test_expired_token_raises_error(
        self, auth_service: AuthService
    ) -> None:
        """Test that expired token raises AuthenticationError."""
        with patch.object(auth_service, "_get_jwks_client") as mock_jwks:
            mock_client = MagicMock()
            mock_signing_key = MagicMock()
            mock_signing_key.key = "test-key"
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks.return_value = mock_client

            with patch("app.auth.service.jwt.decode") as mock_decode:
                mock_decode.side_effect = jwt.ExpiredSignatureError()

                with pytest.raises(AuthenticationError) as exc_info:
                    await auth_service.validate_token("expired-token")

                assert "expired" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_invalid_audience_raises_error(
        self, auth_service: AuthService
    ) -> None:
        """Test that invalid audience raises AuthenticationError."""
        with patch.object(auth_service, "_get_jwks_client") as mock_jwks:
            mock_client = MagicMock()
            mock_signing_key = MagicMock()
            mock_signing_key.key = "test-key"
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks.return_value = mock_client

            with patch("app.auth.service.jwt.decode") as mock_decode:
                mock_decode.side_effect = jwt.InvalidAudienceError()

                with pytest.raises(AuthenticationError) as exc_info:
                    await auth_service.validate_token("bad-audience-token")

                assert "audience" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_invalid_issuer_raises_error(
        self, auth_service: AuthService
    ) -> None:
        """Test that invalid issuer raises AuthenticationError."""
        with patch.object(auth_service, "_get_jwks_client") as mock_jwks:
            mock_client = MagicMock()
            mock_signing_key = MagicMock()
            mock_signing_key.key = "test-key"
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks.return_value = mock_client

            with patch("app.auth.service.jwt.decode") as mock_decode:
                mock_decode.side_effect = jwt.InvalidIssuerError()

                with pytest.raises(AuthenticationError) as exc_info:
                    await auth_service.validate_token("bad-issuer-token")

                assert "issuer" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_invalid_token_raises_error(
        self, auth_service: AuthService
    ) -> None:
        """Test that invalid token raises AuthenticationError."""
        with patch.object(auth_service, "_get_jwks_client") as mock_jwks:
            mock_client = MagicMock()
            mock_signing_key = MagicMock()
            mock_signing_key.key = "test-key"
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_jwks.return_value = mock_client

            with patch("app.auth.service.jwt.decode") as mock_decode:
                mock_decode.side_effect = jwt.InvalidTokenError("Bad token")

                with pytest.raises(AuthenticationError) as exc_info:
                    await auth_service.validate_token("invalid-token")

                assert "invalid" in str(exc_info.value.message).lower()


class TestAuthServiceExtractRole:
    """Tests for AuthService._extract_role method."""

    def test_direct_role_claim(self, auth_service: AuthService) -> None:
        """Test extraction of role from direct claim."""
        payload = {"role": "admin"}
        
        with patch.object(auth_service, "_extract_role", wraps=auth_service._extract_role):
            result = auth_service._extract_role(payload)
            assert result == UserRole.ADMIN

    def test_keycloak_realm_access_roles(self, auth_service: AuthService) -> None:
        """Test extraction of role from Keycloak realm_access."""
        payload = {
            "realm_access": {
                "roles": ["admin", "user"]
            }
        }
        
        result = auth_service._extract_role(payload)
        assert result == UserRole.ADMIN

    def test_keycloak_resource_access_roles(self, auth_service: AuthService) -> None:
        """Test extraction of role from Keycloak resource_access."""
        with patch("app.auth.service.settings") as mock_settings:
            mock_settings.oidc_client_id = "test-client"
            mock_settings.oidc_role_claim = "role"
            
            payload = {
                "resource_access": {
                    "test-client": {
                        "roles": ["campaign_manager"]
                    }
                }
            }
            
            result = auth_service._extract_role(payload)
            assert result == UserRole.CAMPAIGN_MANAGER

    def test_role_priority_admin_first(self, auth_service: AuthService) -> None:
        """Test that admin role takes priority."""
        payload = {
            "realm_access": {
                "roles": ["viewer", "campaign_manager", "admin"]
            }
        }
        
        result = auth_service._extract_role(payload)
        assert result == UserRole.ADMIN

    def test_unknown_role_returns_none(self, auth_service: AuthService) -> None:
        """Test that unknown role returns None."""
        payload = {"role": "unknown_role"}
        
        result = auth_service._extract_role(payload)
        assert result is None

    def test_no_role_returns_none(self, auth_service: AuthService) -> None:
        """Test that missing role returns None."""
        payload = {}
        
        result = auth_service._extract_role(payload)
        assert result is None