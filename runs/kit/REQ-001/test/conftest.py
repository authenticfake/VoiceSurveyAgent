import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.http.auth.router import build_auth_router
from app.auth.domain.models import IDTokenClaims, OIDCProfile, Role, TokenSet, User
from app.auth.domain.repository import UserRepository
from app.auth.domain.role_mapper import ConfigurableRoleMapper
from app.auth.domain.service import AuthService, OIDCClientProtocol
from app.auth.rbac import CurrentUserProvider, RBACDependencies


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    async def get_by_oidc_sub(self, sub: str) -> User | None:
        return self._users.get(sub)

    async def upsert_from_oidc_profile(self, profile: OIDCProfile, role: Role) -> User:
        now = datetime.now(timezone.utc)
        user = self._users.get(profile.sub)
        if user:
            updated = User(
                id=user.id,
                oidc_sub=user.oidc_sub,
                email=profile.email,
                name=profile.name or user.name,
                role=role,
                created_at=user.created_at,
                updated_at=now,
            )
        else:
            updated = User(
                id=uuid4(),
                oidc_sub=profile.sub,
                email=profile.email,
                name=profile.name or profile.email,
                role=role,
                created_at=now,
                updated_at=now,
            )
        self._users[profile.sub] = updated
        return updated


class FakeOIDCClient(OIDCClientProtocol):
    def __init__(self) -> None:
        self._claims_by_token: dict[str, dict[str, Any]] = {}
        self._claims_by_code: dict[str, dict[str, Any]] = {}

    def prime_code(self, code: str, claims: dict[str, Any]) -> None:
        self._claims_by_code[code] = claims

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> TokenSet:
        claims = self._claims_by_code.get(code)
        if not claims:
            claims = {
                "sub": f"user-{code}",
                "email": f"{code}@example.com",
                "name": f"User {code}",
                "roles": ["viewer"],
                "iss": "https://issuer",
                "aud": ["client"],
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            }
        token = f"id-token-{code}"
        self._claims_by_token[token] = claims
        return TokenSet(
            access_token=f"access-token-{code}",
            id_token=token,
            expires_in=3600,
            token_type="Bearer",
        )

    async def verify_id_token(self, id_token: str) -> IDTokenClaims:
        claims = self._claims_by_token.get(id_token)
        if not claims:
            raise ValueError("unknown token")
        return IDTokenClaims(
            subject=claims["sub"],
            email=claims.get("email"),
            name=claims.get("name"),
            issuer=claims.get("iss", "https://issuer"),
            audience=tuple(claims.get("aud", ["client"])),
            issued_at=datetime.fromtimestamp(claims.get("iat"), tz=timezone.utc),
            expires_at=datetime.fromtimestamp(claims.get("exp"), tz=timezone.utc),
            raw_claims=claims,
        )


@pytest.fixture()
def role_mapper() -> ConfigurableRoleMapper:
    return ConfigurableRoleMapper(
        mapping={
            "roles": {
                "admin": Role.admin,
                "campaign_manager": Role.campaign_manager,
                "viewer": Role.viewer,
            }
        },
        default_role=Role.viewer,
    )


@pytest_asyncio.fixture()
async def test_app(role_mapper: ConfigurableRoleMapper):
    repo = InMemoryUserRepository()
    oidc_client = FakeOIDCClient()
    auth_service = AuthService(repo, oidc_client, role_mapper)
    current_user = CurrentUserProvider(oidc_client=oidc_client, user_repo=repo, role_mapper=role_mapper)
    router = build_auth_router(auth_service, RBACDependencies(current_user=current_user))
    app = FastAPI()
    app.include_router(router)
    yield app


@pytest_asyncio.fixture()
async def client(test_app: FastAPI):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client