from typing import Protocol

from app.auth.domain.models import OIDCProfile, Role, User


class UserRepository(Protocol):
    async def get_by_oidc_sub(self, sub: str) -> User | None:
        ...

    async def upsert_from_oidc_profile(self, profile: OIDCProfile, role: Role) -> User:
        ...