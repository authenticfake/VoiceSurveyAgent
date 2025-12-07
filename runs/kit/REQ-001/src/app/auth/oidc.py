from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
from jose import jwt
from jose.exceptions import JWTError

from app.auth.domain import UserRole, UserRepository, map_roles_from_claims
from app.infra.config import get_settings


@dataclass
class OIDCConfig:
    """Configuration values required for OIDC auth-code flow."""

    issuer: str
    client_id: str
    client_secret: str
    auth_endpoint: str
    token_endpoint: str
    jwks_uri: str
    redirect_uri: str
    audience: Optional[str] = None
    # Space-separated OIDC scopes requested during login
    scope: str = "openid profile email"


class OIDCError(Exception):
    """Raised when an OIDC-related operation fails."""


class IDTokenValidationError(OIDCError):
    """Raised when ID token validation fails."""


class OIDCAuthenticator:
    """Handle OIDC auth-code flow and ID token validation."""

    def __init__(
        self,
        user_repository: UserRepository,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._user_repository = user_repository
        self._http_client = http_client

    @property
    def config(self) -> OIDCConfig:
        settings = get_settings()
        return OIDCConfig(
            issuer=settings.oidc_issuer,
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret,
            auth_endpoint=settings.oidc_auth_endpoint,
            token_endpoint=settings.oidc_token_endpoint,
            jwks_uri=settings.oidc_jwks_uri,
            redirect_uri=settings.oidc_redirect_uri,
            audience=settings.oidc_audience,
            scope=settings.oidc_scope,
        )

    def build_authorization_url(self, state: str) -> str:
        """Return the IdP authorization URL for frontend redirection."""
        from urllib.parse import urlencode

        cfg = self.config
        query = urlencode(
            {
                "response_type": "code",
                "client_id": cfg.client_id,
                "redirect_uri": cfg.redirect_uri,
                "scope": cfg.scope,
                "state": state,
            }
        )
        return f"{cfg.auth_endpoint}?{query}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens via the IdP token endpoint."""
        cfg = self.config
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg.redirect_uri,
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
        }

        async with self._ensure_client() as client:
            response = await client.post(
                cfg.token_endpoint,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
        if response.status_code != 200:
            raise OIDCError(
                f"Token endpoint returned {response.status_code}: {response.text}"
            )
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise OIDCError("Unable to decode token endpoint response as JSON") from exc

    async def authenticate_via_code(self, code: str):
        """Full auth-code flow: exchange code, validate ID token, upsert user."""
        token_response = await self.exchange_code_for_tokens(code)
        id_token = token_response.get("id_token")
        if not id_token:
            raise IDTokenValidationError("id_token missing in token response")

        claims = await self.validate_id_token(id_token)
        user = self._upsert_user_from_claims(claims)
        return user, id_token

    async def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        """Validate and decode an ID token using JWKS and standard checks."""
        cfg = self.config
        jwks = await self._fetch_jwks()
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        key = None
        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwk
                break
        if key is None:
            raise IDTokenValidationError("Unable to find matching JWK for token kid")

        try:
            claims = jwt.decode(
                id_token,
                key,
                algorithms=[header.get("alg", "RS256")],
                audience=cfg.audience or cfg.client_id,
                issuer=cfg.issuer,
            )
        except JWTError as exc:
            raise IDTokenValidationError(str(exc)) from exc

        return claims

    async def validate_bearer_token(self, token: str) -> Dict[str, Any]:
        """Validate a bearer ID token supplied in Authorization header.

        This is used for API request authentication after login.
        """
        return await self.validate_id_token(token)

    def _upsert_user_from_claims(self, claims: Dict[str, Any]):
        sub = claims.get("sub")
        email = claims.get("email") or ""
        name = claims.get("name") or claims.get("preferred_username") or email or sub
        if not sub:
            raise IDTokenValidationError("ID token missing 'sub' claim")

        role: UserRole = map_roles_from_claims(claims)
        return self._user_repository.upsert_from_oidc(
            oidc_sub=sub,
            email=email,
            name=name,
            role=role,
        )

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from IdP, with simple in-process caching.

        For slice‑1 we use an in-memory LRU cache keyed by JWKS URI.
        """
        cfg = self.config
        jwks = await _cached_fetch_jwks(cfg.jwks_uri, self._ensure_client)
        return jwks

    def _ensure_client(self):
        """Return a context manager for an AsyncClient.

        If a client was injected, re-use it for the duration of this call.
        Otherwise, create a one-off client.
        """

        if self._http_client is not None:
            return _ExistingClientContext(self._http_client)
        return httpx.AsyncClient()


class _ExistingClientContext:
    """Context manager wrapper for a pre-existing AsyncClient.

    This avoids closing injected clients when used with `async with`.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:  # type: ignore[override]
        return self._client

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        # Do not close the shared client.
        return None


@lru_cache(maxsize=8)
def _jwks_cache_key(jwks_uri: str) -> str:  # pragma: no cover - trivial
    return jwks_uri


async def _cached_fetch_jwks(
    jwks_uri: str, client_factory
) -> Dict[str, Any]:
    """Fetch JWKS with simple LRU caching per-process."""
    cache_key = _jwks_cache_key(jwks_uri)
    if hasattr(_cached_fetch_jwks, "_cache"):  # type: ignore[attr-defined]
        cache: Dict[str, Dict[str, Any]] = getattr(
            _cached_fetch_jwks, "_cache"
        )  # type: ignore[attr-defined]
    else:
        cache = {}
        setattr(_cached_fetch_jwks, "_cache", cache)  # type: ignore[attr-defined]

    if cache_key in cache:
        return cache[cache_key]

    async with client_factory() as client:
        response = await client.get(jwks_uri, timeout=5.0)
    response.raise_for_status()
    jwks = response.json()
    cache[cache_key] = jwks
    return jwks