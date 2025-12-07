from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional

from fastapi import Depends, Header

from app.api.http.errors import forbidden, unauthorized
from app.auth.domain.models import Role, User
from app.auth.domain.repository import UserRepository
from app.auth.domain.role_mapper import RoleMapper
from app.auth.domain.service import OIDCClientProtocol
from app.auth.errors import AuthenticationError
from app.auth.domain.models import OIDCProfile


@dataclass(slots=True)
class CurrentUserProvider:
    oidc_client: OIDCClientProtocol
    user_repo: UserRepository
    role_mapper: RoleMapper

    async def __call__(self, authorization: Optional[str] = Header(default=None)) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            raise unauthorized("Missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            raise unauthorized("Empty bearer token")
        claims = await self.oidc_client.verify_id_token(token)
        if not claims.email:
            raise AuthenticationError("Token missing email claim")
        user = await self.user_repo.get_by_oidc_sub(claims.subject)
        if user:
            return user
        profile = OIDCProfile(sub=claims.subject, email=claims.email, name=claims.name)
        role = self.role_mapper.map_role(claims.raw_claims)
        return await self.user_repo.upsert_from_oidc_profile(profile, role)


@dataclass(slots=True)
class RBACDependencies:
    current_user: CurrentUserProvider

    def require_roles(self, *roles: Role) -> Callable[[User], User]:
        async def _checker(user: User = Depends(self.current_user)) -> User:
            if user.role not in roles:
                raise forbidden(f"Route requires roles: {[role.value for role in roles]}")
            return user

        return _checker