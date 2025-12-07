from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from app.auth.domain.models import Role, User
from app.auth.domain.service import AuthResult


@dataclass
class AuthenticatedUserResponse:
    id: str
    email: str
    name: str
    role: Role
    last_login_at: datetime | None = None

    @classmethod
    def from_domain(cls, user: User) -> "AuthenticatedUserResponse":
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
            last_login_at=user.updated_at,
        )


@dataclass
class RoleMappingRule:
    source_field: str
    value_map: Mapping[str, Role]
    default_role: Role

    def resolve(self, claims: Mapping[str, Any]) -> Role:
        candidate = claims.get(self.source_field)
        if candidate is None:
            return self.default_role
        values = candidate if isinstance(candidate, list) else [candidate]
        for value in values:
            normalized = str(value).lower()
            if normalized in self.value_map:
                return self.value_map[normalized]
        return self.default_role