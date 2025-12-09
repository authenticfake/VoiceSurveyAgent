"""
OIDC client for identity provider integration.

REQ-002: OIDC authentication integration
"""

import secrets
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

from app.config import Settings, get_settings
from app.shared.exceptions import OIDCError
from app.shared.logging import get_logger
from app.auth.schemas import OIDCTokenResponse, OIDCUserInfo

logger = get_logger(__name__)


class OIDCClientProtocol(Protocol):
    """Protocol for OIDC client operations."""

    def get_authorization_url(self, state: str) -> str: ...
    async def exchange_code(self, code: str) -> OIDCTokenResponse: ...
    async def get_userinfo(self, access_token: str) -> OIDCUserInfo: ...
    async def refresh_token(self, refresh_token: str) -> OIDCTokenResponse: ...
    def generate_state(self) -> str: ...


class OIDCClient:
    """OIDC client for identity provider integration."""

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize OIDC client.

        Args:
            settings: Application settings. Uses default if not provided.
            http_client: HTTP client for making requests. Creates new if not provided.
        """
        self._settings = settings or get_settings()
        self._http_client = http_client
        self._owns_client = http_client is None
        self._discovery_cache: dict[str, Any] | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _discover(self) -> dict[str, Any]:
        """Fetch OIDC discovery document.

        Returns:
            Discovery document with endpoint URLs.

        Raises:
            OIDCError: If discovery fails.
        """
        if self._discovery_cache is not None:
            return self._discovery_cache

        discovery_url = f"{self._settings.oidc_issuer_url}/.well-known/openid-configuration"
        client = await self._get_http_client()

        try:
            response = await client.get(discovery_url)
            response.raise_for_status()
            self._discovery_cache = response.json()
            return self._discovery_cache
        except httpx.HTTPError as e:
            logger.error(
                "OIDC discovery failed",
                extra={"url": discovery_url, "error": str(e)},
            )
            raise OIDCError(
                message="Failed to fetch OIDC discovery document",
                details={"url": discovery_url, "error": str(e)},
            ) from e

    def generate_state(self) -> str:
        """Generate a cryptographically secure state parameter.

        Returns:
            Random state string for CSRF protection.
        """
        return secrets.token_urlsafe(32)

    def get_authorization_url(self, state: str) -> str:
        """Build the authorization URL for OIDC login.

        Args:
            state: CSRF state parameter.

        Returns:
            Full authorization URL to redirect user.
        """
        # Use a well-known authorization endpoint pattern
        # In production, this would come from discovery
        auth_endpoint = f"{self._settings.oidc_issuer_url}/authorize"

        params = {
            "response_type": "code",
            "client_id": self._settings.oidc_client_id,
            "redirect_uri": self._settings.oidc_redirect_uri,
            "scope": self._settings.oidc_scopes,
            "state": state,
        }

        return f"{auth_endpoint}?{urlencode(params)}"

    async def get_authorization_url_with_discovery(self, state: str) -> str:
        """Build authorization URL using discovery document.

        Args:
            state: CSRF state parameter.

        Returns:
            Full authorization URL to redirect user.
        """
        discovery = await self._discover()
        auth_endpoint = discovery.get("authorization_endpoint")

        if not auth_endpoint:
            raise OIDCError(
                message="Authorization endpoint not found in discovery",
                details={"discovery": discovery},
            )

        params = {
            "response_type": "code",
            "client_id": self._settings.oidc_client_id,
            "redirect_uri": self._settings.oidc_redirect_uri,
            "scope": self._settings.oidc_scopes,
            "state": state,
        }

        return f"{auth_endpoint}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OIDCTokenResponse:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback.

        Returns:
            Token response with access and refresh tokens.

        Raises:
            OIDCError: If token exchange fails.
        """
        # Use well-known token endpoint pattern
        token_endpoint = f"{self._settings.oidc_issuer_url}/oauth/token"

        client = await self._get_http_client()

        try:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._settings.oidc_redirect_uri,
                    "client_id": self._settings.oidc_client_id,
                    "client_secret": self._settings.oidc_client_secret,
                },
            )
            response.raise_for_status()
            return OIDCTokenResponse.model_validate(response.json())
        except httpx.HTTPError as e:
            logger.error(
                "OIDC token exchange failed",
                extra={"error": str(e)},
            )
            raise OIDCError(
                message="Failed to exchange authorization code",
                details={"error": str(e)},
            ) from e

    async def exchange_code_with_discovery(self, code: str) -> OIDCTokenResponse:
        """Exchange authorization code using discovery document.

        Args:
            code: Authorization code from callback.

        Returns:
            Token response with access and refresh tokens.

        Raises:
            OIDCError: If token exchange fails.
        """
        discovery = await self._discover()
        token_endpoint = discovery.get("token_endpoint")

        if not token_endpoint:
            raise OIDCError(
                message="Token endpoint not found in discovery",
                details={"discovery": discovery},
            )

        client = await self._get_http_client()

        try:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._settings.oidc_redirect_uri,
                    "client_id": self._settings.oidc_client_id,
                    "client_secret": self._settings.oidc_client_secret,
                },
            )
            response.raise_for_status()
            return OIDCTokenResponse.model_validate(response.json())
        except httpx.HTTPError as e:
            logger.error(
                "OIDC token exchange failed",
                extra={"error": str(e)},
            )
            raise OIDCError(
                message="Failed to exchange authorization code",
                details={"error": str(e)},
            ) from e

    async def get_userinfo(self, access_token: str) -> OIDCUserInfo:
        """Fetch user information from OIDC provider.

        Args:
            access_token: OIDC access token.

        Returns:
            User information from the IdP.

        Raises:
            OIDCError: If userinfo request fails.
        """
        # Use well-known userinfo endpoint pattern
        userinfo_endpoint = f"{self._settings.oidc_issuer_url}/userinfo"

        client = await self._get_http_client()

        try:
            response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return OIDCUserInfo.model_validate(response.json())
        except httpx.HTTPError as e:
            logger.error(
                "OIDC userinfo request failed",
                extra={"error": str(e)},
            )
            raise OIDCError(
                message="Failed to fetch user information",
                details={"error": str(e)},
            ) from e

    async def get_userinfo_with_discovery(self, access_token: str) -> OIDCUserInfo:
        """Fetch user information using discovery document.

        Args:
            access_token: OIDC access token.

        Returns:
            User information from the IdP.

        Raises:
            OIDCError: If userinfo request fails.
        """
        discovery = await self._discover()
        userinfo_endpoint = discovery.get("userinfo_endpoint")

        if not userinfo_endpoint:
            raise OIDCError(
                message="Userinfo endpoint not found in discovery",
                details={"discovery": discovery},
            )

        client = await self._get_http_client()

        try:
            response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return OIDCUserInfo.model_validate(response.json())
        except httpx.HTTPError as e:
            logger.error(
                "OIDC userinfo request failed",
                extra={"error": str(e)},
            )
            raise OIDCError(
                message="Failed to fetch user information",
                details={"error": str(e)},
            ) from e

    async def refresh_token(self, refresh_token: str) -> OIDCTokenResponse:
        """Refresh access token using refresh token.

        Args:
            refresh_token: OIDC refresh token.

        Returns:
            New token response.

        Raises:
            OIDCError: If token refresh fails.
        """
        # Use well-known token endpoint pattern
        token_endpoint = f"{self._settings.oidc_issuer_url}/oauth/token"

        client = await self._get_http_client()

        try:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self._settings.oidc_client_id,
                    "client_secret": self._settings.oidc_client_secret,
                },
            )
            response.raise_for_status()
            return OIDCTokenResponse.model_validate(response.json())
        except httpx.HTTPError as e:
            logger.error(
                "OIDC token refresh failed",
                extra={"error": str(e)},
            )
            raise OIDCError(
                message="Failed to refresh token",
                details={"error": str(e)},
            ) from e