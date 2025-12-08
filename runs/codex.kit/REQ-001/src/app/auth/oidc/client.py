import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from jose import jwt

from app.auth.domain.models import IDTokenClaims, TokenSet
from app.auth.domain.service import OIDCClientProtocol
from app.auth.errors import AuthenticationError, OIDCConfigurationError
from app.auth.oidc.config import OIDCConfig


@dataclass
class _JWKSCache:
    keys: dict[str, Any] | None = None
    expires_at: datetime | None = None

    def is_valid(self) -> bool:
        return self.keys is not None and self.expires_at is not None and self.expires_at > datetime.now(timezone.utc)


class OIDCClient(OIDCClientProtocol):
    def __init__(
        self,
        config: OIDCConfig,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not config.token_endpoint or not config.jwks_uri:
            raise OIDCConfigurationError("OIDC token endpoint and JWKS URI must be configured")
        self._config = config
        self._http = http_client or httpx.AsyncClient(timeout=config.timeout_seconds)
        self._jwks_cache = _JWKSCache()
        self._lock = asyncio.Lock()

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> TokenSet:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier

        response = await self._http.post(
            self._config.token_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400:
            raise AuthenticationError(f"OIDC token endpoint error: {response.text}")
        payload = response.json()
        try:
            token_set = TokenSet(
                access_token=payload["access_token"],
                id_token=payload["id_token"],
                refresh_token=payload.get("refresh_token"),
                expires_in=int(payload.get("expires_in", 0)),
                token_type=payload.get("token_type", "Bearer"),
            )
        except KeyError as exc:
            raise AuthenticationError(f"OIDC response missing field: {exc}") from exc
        return token_set

    async def verify_id_token(self, id_token: str) -> IDTokenClaims:
        jwk_set = await self._get_jwks()
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        key = None
        for jwk in jwk_set.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwk
                break
        if key is None:
            raise AuthenticationError("Unable to find matching JWK for token")
        audience = self._config.audience or self._config.client_id
        claims = jwt.decode(
            id_token,
            key,
            audience=audience,
            issuer=self._config.issuer,
            options={"verify_aud": True, "verify_at_hash": False},
        )
        return IDTokenClaims(
            subject=claims["sub"],
            email=claims.get("email"),
            name=claims.get("name"),
            issuer=claims["iss"],
            audience=tuple(claims.get("aud") if isinstance(claims.get("aud"), list) else [claims.get("aud")]),
            issued_at=datetime.fromtimestamp(claims["iat"], tz=timezone.utc),
            expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc),
            raw_claims=claims,
        )

    async def _get_jwks(self) -> Dict[str, Any]:
        async with self._lock:
            if self._jwks_cache.is_valid():
                return self._jwks_cache.keys  # type: ignore[return-value]
            response = await self._http.get(self._config.jwks_uri)
            response.raise_for_status()
            jwks = response.json()
            self._jwks_cache = _JWKSCache(
                keys=jwks,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            )
            return jwks