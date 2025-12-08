"""OIDC client for authentication."""

import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings, get_settings
from app.shared.exceptions import OIDCError
from app.shared.logging import get_logger

logger = get_logger(__name__)

@dataclass
class OIDCConfiguration:
    """OIDC provider configuration from discovery endpoint."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    end_session_endpoint: str | None = None

@dataclass
class OIDCTokens:
    """Tokens received from OIDC provider."""

    access_token: str
    id_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None

@dataclass
class OIDCUserInfo:
    """User information from OIDC provider."""

    sub: str
    email: str
    name: str
    email_verified: bool = False
    picture: str | None = None

class OIDCClient:
    """OIDC client for handling authentication flows."""

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._http_client = http_client
        self._config: OIDCConfiguration | None = None
        self._jwks: dict[str, Any] | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def get_configuration(self) -> OIDCConfiguration:
        """Fetch OIDC configuration from discovery endpoint."""
        if self._config is not None:
            return self._config

        discovery_url = f"{self._settings.oidc_issuer_url}/.well-known/openid-configuration"
        client = await self._get_http_client()

        try:
            response = await client.get(discovery_url)
            response.raise_for_status()
            data = response.json()

            self._config = OIDCConfiguration(
                issuer=data["issuer"],
                authorization_endpoint=data["authorization_endpoint"],
                token_endpoint=data["token_endpoint"],
                userinfo_endpoint=data["userinfo_endpoint"],
                jwks_uri=data["jwks_uri"],
                end_session_endpoint=data.get("end_session_endpoint"),
            )
            return self._config
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch OIDC configuration: {e}")
            raise OIDCError(
                "Failed to fetch OIDC configuration",
                {"url": discovery_url, "error": str(e)},
            ) from e

    async def get_jwks(self) -> dict[str, Any]:
        """Fetch JWKS from provider."""
        if self._jwks is not None:
            return self._jwks

        config = await self.get_configuration()
        client = await self._get_http_client()

        try:
            response = await client.get(config.jwks_uri)
            response.raise_for_status()
            self._jwks = response.json()
            return self._jwks
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise OIDCError(
                "Failed to fetch JWKS",
                {"url": config.jwks_uri, "error": str(e)},
            ) from e

    def generate_state(self) -> str:
        """Generate a secure random state parameter."""
        return secrets.token_urlsafe(32)

    async def get_authorization_url(self, state: str) -> str:
        """Build the authorization URL for login."""
        config = await self.get_configuration()

        params = {
            "client_id": self._settings.oidc_client_id,
            "redirect_uri": self._settings.oidc_redirect_uri,
            "response_type": "code",
            "scope": self._settings.oidc_scopes,
            "state": state,
        }

        return f"{config.authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OIDCTokens:
        """Exchange authorization code for tokens."""
        config = await self.get_configuration()
        client = await self._get_http_client()

        data = {
            "grant_type": "authorization_code",
            "client_id": self._settings.oidc_client_id,
            "client_secret": self._settings.oidc_client_secret,
            "code": code,
            "redirect_uri": self._settings.oidc_redirect_uri,
        }

        try:
            response = await client.post(
                config.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()

            return OIDCTokens(
                access_token=token_data["access_token"],
                id_token=token_data["id_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                refresh_token=token_data.get("refresh_token"),
                scope=token_data.get("scope"),
            )
        except httpx.HTTPError as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            raise OIDCError(
                "Failed to exchange authorization code",
                {"error": str(e)},
            ) from e

    async def refresh_tokens(self, refresh_token: str) -> OIDCTokens:
        """Refresh access token using refresh token."""
        config = await self.get_configuration()
        client = await self._get_http_client()

        data = {
            "grant_type": "refresh_token",
            "client_id": self._settings.oidc_client_id,
            "client_secret": self._settings.oidc_client_secret,
            "refresh_token": refresh_token,
        }

        try:
            response = await client.post(
                config.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()

            return OIDCTokens(
                access_token=token_data["access_token"],
                id_token=token_data.get("id_token", ""),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                refresh_token=token_data.get("refresh_token", refresh_token),
                scope=token_data.get("scope"),
            )
        except httpx.HTTPError as e:
            logger.error(f"Failed to refresh tokens: {e}")
            raise OIDCError(
                "Failed to refresh tokens",
                {"error": str(e)},
            ) from e

    async def get_userinfo(self, access_token: str) -> OIDCUserInfo:
        """Fetch user information from userinfo endpoint."""
        config = await self.get_configuration()
        client = await self._get_http_client()

        try:
            response = await client.get(
                config.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()

            return OIDCUserInfo(
                sub=data["sub"],
                email=data.get("email", ""),
                name=data.get("name", data.get("preferred_username", "")),
                email_verified=data.get("email_verified", False),
                picture=data.get("picture"),
            )
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch user info: {e}")
            raise OIDCError(
                "Failed to fetch user information",
                {"error": str(e)},
            ) from e