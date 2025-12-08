"""OIDC integration for authentication."""

from __future__ import annotations

import time
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from pydantic import BaseModel, Field

from app.auth.errors import (
    AuthenticationError,
    OIDCConfigurationError,
    TokenExpiredError,
    TokenValidationError,
)


class OIDCConfig(BaseModel):
    """OIDC provider configuration."""

    issuer: str = Field(..., description="OIDC issuer URL")
    client_id: str = Field(..., description="OAuth2 client ID")
    client_secret: str = Field(..., description="OAuth2 client secret")
    redirect_uri: str = Field(..., description="OAuth2 redirect URI")
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    scopes: list[str] = Field(
        default=["openid", "email", "profile"], description="OAuth2 scopes"
    )

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class TokenPayload(BaseModel):
    """Decoded token payload."""

    sub: str = Field(..., description="Subject identifier")
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    iss: Optional[str] = None
    aud: Optional[str | list[str]] = None

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None


class OIDCClient:
    """OIDC client for authentication flows."""

    def __init__(self, config: OIDCConfig) -> None:
        """Initialize OIDC client with configuration."""
        self.config = config
        self._jwks: Optional[dict[str, Any]] = None
        self._jwks_fetched_at: float = 0
        self._jwks_ttl: float = 3600  # Cache JWKS for 1 hour
        self._discovery_doc: Optional[dict[str, Any]] = None

    async def discover(self) -> None:
        """Fetch OIDC discovery document and populate endpoints."""
        discovery_url = f"{self.config.issuer.rstrip('/')}/.well-known/openid-configuration"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(discovery_url, timeout=10.0)
                response.raise_for_status()
                self._discovery_doc = response.json()
            except httpx.HTTPError as e:
                raise OIDCConfigurationError(
                    f"Failed to fetch OIDC discovery document: {e}"
                ) from e

        # Populate endpoints from discovery
        self.config.authorization_endpoint = self._discovery_doc.get(
            "authorization_endpoint"
        )
        self.config.token_endpoint = self._discovery_doc.get("token_endpoint")
        self.config.userinfo_endpoint = self._discovery_doc.get("userinfo_endpoint")
        self.config.jwks_uri = self._discovery_doc.get("jwks_uri")

        if not self.config.token_endpoint:
            raise OIDCConfigurationError("Token endpoint not found in discovery document")
        if not self.config.jwks_uri:
            raise OIDCConfigurationError("JWKS URI not found in discovery document")

    def get_authorization_url(self, state: str, nonce: Optional[str] = None) -> str:
        """Generate authorization URL for login redirect."""
        if not self.config.authorization_endpoint:
            raise OIDCConfigurationError("Authorization endpoint not configured")

        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
        }
        if nonce:
            params["nonce"] = nonce

        return f"{self.config.authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchange authorization code for tokens."""
        if not self.config.token_endpoint:
            raise OIDCConfigurationError("Token endpoint not configured")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,
                )
                response.raise_for_status()
                return TokenResponse(**response.json())
            except httpx.HTTPStatusError as e:
                raise AuthenticationError(
                    f"Token exchange failed: {e.response.text}"
                ) from e
            except httpx.HTTPError as e:
                raise AuthenticationError(f"Token exchange failed: {e}") from e

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JWKS from provider with caching."""
        now = time.time()
        if self._jwks and (now - self._jwks_fetched_at) < self._jwks_ttl:
            return self._jwks

        if not self.config.jwks_uri:
            raise OIDCConfigurationError("JWKS URI not configured")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.config.jwks_uri, timeout=10.0)
                response.raise_for_status()
                self._jwks = response.json()
                self._jwks_fetched_at = now
                return self._jwks
            except httpx.HTTPError as e:
                raise OIDCConfigurationError(f"Failed to fetch JWKS: {e}") from e

    async def validate_id_token(self, id_token: str) -> TokenPayload:
        """Validate ID token and return decoded payload."""
        jwks = await self._fetch_jwks()

        try:
            # Decode without verification first to get header
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")

            # Find matching key
            rsa_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break

            if not rsa_key:
                raise TokenValidationError("Unable to find matching key in JWKS")

            # Verify and decode
            payload = jwt.decode(
                id_token,
                rsa_key,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=self.config.issuer,
            )

            return TokenPayload(**payload)

        except ExpiredSignatureError as e:
            raise TokenExpiredError("ID token has expired") from e
        except JWTError as e:
            raise TokenValidationError(f"Invalid ID token: {e}") from e

    async def validate_access_token(self, access_token: str) -> TokenPayload:
        """Validate access token (JWT format) and return decoded payload."""
        jwks = await self._fetch_jwks()

        try:
            unverified_header = jwt.get_unverified_header(access_token)
            kid = unverified_header.get("kid")

            rsa_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break

            if not rsa_key:
                raise TokenValidationError("Unable to find matching key in JWKS")

            # For access tokens, audience validation may differ
            payload = jwt.decode(
                access_token,
                rsa_key,
                algorithms=["RS256"],
                issuer=self.config.issuer,
                options={"verify_aud": False},  # Access token audience may differ
            )

            return TokenPayload(**payload)

        except ExpiredSignatureError as e:
            raise TokenExpiredError("Access token has expired") from e
        except JWTError as e:
            raise TokenValidationError(f"Invalid access token: {e}") from e

    async def get_userinfo(self, access_token: str) -> dict[str, Any]:
        """Fetch user info from OIDC provider."""
        if not self.config.userinfo_endpoint:
            raise OIDCConfigurationError("Userinfo endpoint not configured")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.config.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise AuthenticationError(f"Failed to fetch userinfo: {e}") from e