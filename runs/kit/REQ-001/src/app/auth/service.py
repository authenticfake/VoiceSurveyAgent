from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain.models import OidcProfile, Role, UserProfile, derive_role_from_claims
from app.auth.domain.repository import SqlAlchemyUserRepository, UserRepository
from app.auth.domain.schemas import AuthTokensResponse, UserRead
from app.auth.errors import AuthError, AuthErrorCode
from app.auth.oidc.client import OidcClient
from app.infra.config.settings import Settings


class AppTokenEncoder:
    """Encodes first-party JWTs used by backend APIs."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def encode(self, user: UserProfile) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "oidc_sub": user.oidc_sub,
            "role": user.role.value,
            "aud": self._settings.oidc_client_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self._settings.app_jwt_expires_seconds)).timestamp()),
            "iss": self._settings.app_name,
        }
        return jwt.encode(
            payload,
            self._settings.app_jwt_secret.get_secret_value(),
            algorithm=self._settings.app_jwt_algorithm,
        )


class AuthService:
    """Coordinates OIDC login and RBAC token issuance."""

    def __init__(
        self,
        settings: Settings,
        oidc_client: OidcClient,
        repository: UserRepository,
        token_encoder: AppTokenEncoder,
    ):
        self._settings = settings
        self._oidc_client = oidc_client
        self._repository = repository
        self._token_encoder = token_encoder

    def build_authorization_url(self, redirect_uri: str) -> dict[str, str]:
        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "scope": " ".join(self._settings.oidc_default_scopes),
            "client_id": self._settings.oidc_client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
        }
        url = f"{self._settings.oidc_authorization_url}?{urlencode(params)}"
        return {"authorization_url": url, "state": state, "nonce": nonce}

    async def complete_login(
        self, *, code: str, redirect_uri: str
    ) -> AuthTokensResponse:
        token_payload = await self._oidc_client.exchange_code(code, redirect_uri)
        id_token = token_payload.get("id_token")
        if not id_token:
            raise AuthError(AuthErrorCode.INVALID_TOKEN, "Missing id_token in response")
        claims = await self._oidc_client.validate_id_token(id_token)

        profile = self._build_oidc_profile(claims)
        user = await self._repository.upsert_from_oidc(profile)
        app_token = self._token_encoder.encode(user)

        return AuthTokensResponse(
            access_token=token_payload.get("access_token"),
            refresh_token=token_payload.get("refresh_token"),
            expires_in=token_payload.get("expires_in", 3600),
            id_token=id_token,
            app_access_token=app_token,
            user=UserRead.from_domain(user),
        )

    def _build_oidc_profile(self, claims: dict[str, Any]) -> OidcProfile:
        email = claims.get("email")
        name = claims.get("name") or claims.get("given_name")
        sub = claims.get("sub")
        if not email or not name or not sub:
            raise AuthError(
                AuthErrorCode.INVALID_TOKEN,
                "ID token missing required profile fields",
            )
        role = derive_role_from_claims(
            claims, self._settings.oidc_role_claim, self._settings.rbac_role_priority
        )
        return OidcProfile(sub=sub, email=email, name=name, role=role)


def build_auth_service(session: AsyncSession, settings: Settings) -> AuthService:
    repository: UserRepository = SqlAlchemyUserRepository(session)
    oidc_client = OidcClient(settings)
    encoder = AppTokenEncoder(settings)
    return AuthService(
        settings=settings,
        oidc_client=oidc_client,
        repository=repository,
        token_encoder=encoder,
    )