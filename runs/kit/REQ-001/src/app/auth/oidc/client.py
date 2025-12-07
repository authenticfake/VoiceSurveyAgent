from __future__ import annotations

from typing import Any, Dict

import httpx
import jwt
from jwt import InvalidTokenError

from app.auth.errors import AuthError, AuthErrorCode
from app.auth.oidc.jwks import JWKSCache, jwk_to_pem
from app.infra.config.settings import Settings


class OidcClient:
    """Handles OIDC token exchange and ID token validation."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._jwks_cache = JWKSCache(settings.oidc_jwks_url)

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "client_id": self._settings.oidc_client_id,
            "client_secret": self._settings.oidc_client_secret.get_secret_value(),
            "code": code,
            "redirect_uri": redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with httpx.AsyncClient(
            timeout=self._settings.http_timeout_seconds
        ) as client:
            response = await client.post(
                self._settings.oidc_token_url, data=data, headers=headers
            )
            if response.status_code >= 400:
                raise AuthError(
                    AuthErrorCode.OIDC_EXCHANGE_FAILED,
                    f"OIDC token exchange failed: {response.text}",
                )
            return response.json()

    async def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        if not kid:
            raise AuthError(
                AuthErrorCode.INVALID_TOKEN, "Missing kid header in ID token"
            )
        jwk = await self._jwks_cache.get_key(kid)
        if not jwk:
            raise AuthError(
                AuthErrorCode.INVALID_TOKEN,
                f"No JWKS entry for kid '{kid}'",
            )
        pem_key = jwk_to_pem(jwk)
        try:
            claims = jwt.decode(
                id_token,
                key=pem_key,
                algorithms=[jwk.get("alg", "RS256")],
                audience=self._settings.oidc_client_id,
                issuer=self._settings.oidc_issuer,
                options={"require": ["exp", "sub"]},
            )
        except InvalidTokenError as exc:
            raise AuthError(AuthErrorCode.INVALID_TOKEN, str(exc)) from exc
        return claims