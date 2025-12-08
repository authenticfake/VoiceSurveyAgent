"""Tests for OIDC client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.auth.errors import (
    AuthenticationError,
    OIDCConfigurationError,
    TokenExpiredError,
    TokenValidationError,
)
from app.auth.oidc import OIDCClient, OIDCConfig, TokenPayload, TokenResponse


class TestOIDCConfig:
    """Tests for OIDC configuration."""

    def test_config_creation(self) -> None:
        """Test creating OIDC config."""
        config = OIDCConfig(
            issuer="https://example.com/",
            client_id="client-123",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )
        assert config.issuer == "https://example.com/"
        assert config.client_id == "client-123"
        assert config.scopes == ["openid", "email", "profile"]

    def test_config_custom_scopes(self) -> None:
        """Test config with custom scopes."""
        config = OIDCConfig(
            issuer="https://example.com/",
            client_id="client-123",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
            scopes=["openid", "custom"],
        )
        assert config.scopes == ["openid", "custom"]


class TestOIDCClient:
    """Tests for OIDC client."""

    @pytest.fixture
    def client(self, oidc_config: OIDCConfig) -> OIDCClient:
        """Create OIDC client for testing."""
        return OIDCClient(oidc_config)

    def test_get_authorization_url(self, client: OIDCClient) -> None:
        """Test generating authorization URL."""
        url = client.get_authorization_url("test-state", "test-nonce")
        assert "https://test.example.com/authorize" in url
        assert "response_type=code" in url
        assert "client_id=test-client-id" in url
        assert "state=test-state" in url
        assert "nonce=test-nonce" in url

    def test_get_authorization_url_without_endpoint(self) -> None:
        """Test authorization URL without configured endpoint."""
        config = OIDCConfig(
            issuer="https://example.com/",
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )
        client = OIDCClient(config)
        with pytest.raises(OIDCConfigurationError):
            client.get_authorization_url("state")

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, client: OIDCClient) -> None:
        """Test successful code exchange."""
        mock_response = {
            "access_token": "access-123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "id_token": "id-token-123",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )

            tokens = await client.exchange_code("auth-code")
            assert tokens.access_token == "access-123"
            assert tokens.id_token == "id-token-123"

    @pytest.mark.asyncio
    async def test_exchange_code_without_endpoint(self) -> None:
        """Test code exchange without token endpoint."""
        config = OIDCConfig(
            issuer="https://example.com/",
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )
        client = OIDCClient(config)
        with pytest.raises(OIDCConfigurationError):
            await client.exchange_code("code")


class TestTokenPayload:
    """Tests for token payload."""

    def test_payload_creation(self) -> None:
        """Test creating token payload."""
        payload = TokenPayload(
            sub="user-123",
            email="user@example.com",
            name="User",
            exp=9999999999,
        )
        assert payload.sub == "user-123"
        assert payload.email == "user@example.com"

    def test_payload_extra_fields(self) -> None:
        """Test payload with extra fields."""
        payload = TokenPayload(
            sub="user-123",
            custom_claim="value",
        )
        assert payload.sub == "user-123"