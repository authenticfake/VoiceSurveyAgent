from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.auth.domain.models import IDTokenClaims, OIDCProfile, Role, TokenSet, User
from app.auth.domain.repository import UserRepository
from app.auth.domain.role_mapper import RoleMapper
from app.auth.errors import AuthenticationError
from app.api.http.auth.schemas import OIDCCallbackRequest


class OIDCClientProtocol(Protocol):
    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> TokenSet:
        ...

    async def verify_id_token(self, id_token: str) -> IDTokenClaims:
        ...


@dataclass(slots=True)
class AuthResult:
    user: User
    token_set: TokenSet
    claims: IDTokenClaims


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        oidc_client: OIDCClientProtocol,
        role_mapper: RoleMapper,
    ) -> None:
        self._user_repo = user_repo
        self._oidc_client = oidc_client
        self._role_mapper = role_mapper

    async def complete_login(self, payload: OIDCCallbackRequest) -> AuthResult:
        token_set = await self._oidc_client.exchange_code(
            code=payload.code,
            redirect_uri=str(payload.redirect_uri),
            code_verifier=payload.code_verifier,
        )
        claims = await self._oidc_client.verify_id_token(token_set.id_token)
        email = claims.email
        if not email:
            raise AuthenticationError("ID token missing email claim")
        profile = OIDCProfile(
            sub=claims.subject,
            email=email,
            name=claims.name,
            roles=self._extract_roles(claims),
        )
        role = self._role_mapper.map_role(claims.raw_claims)
        user = await self._user_repo.upsert_from_oidc_profile(profile, role)
        return AuthResult(user=user, token_set=token_set, claims=claims)

    @staticmethod
    def _extract_roles(claims: IDTokenClaims) -> list[str]:
        roles = claims.raw_claims.get("roles") or claims.raw_claims.get("groups")
        if roles is None:
            return []
        if isinstance(roles, str):
            return [roles]
        if isinstance(roles, list):
            return [str(role) for role in roles]
        return []

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)