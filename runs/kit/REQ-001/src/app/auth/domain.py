from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable, Optional


class UserRole(str, Enum):
    """Application RBAC roles.

    These values are persisted and used in JWT/claims.
    """

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"


@dataclass
class User:
    """Domain representation of an authenticated user.

    Persistence details are left to infrastructure-layer implementations.
    """

    id: str
    oidc_sub: str
    email: str
    name: str
    role: UserRole


@runtime_checkable
class UserRepository(Protocol):
    """Persistence abstraction for User entities.

    A real implementation (e.g., SQLAlchemy-backed) should be provided
    in the infrastructure layer and injected into the authenticator.
    Tests may use in-memory fakes that implement this protocol.
    """

    def get_by_oidc_sub(self, oidc_sub: str) -> Optional[User]:
        ...

    def upsert_from_oidc(
        self,
        oidc_sub: str,
        email: str,
        name: str,
        role: UserRole,
    ) -> User:
        ...


def map_roles_from_claims(claims: dict) -> UserRole:
    """Map IdP/group claims to an application role.

    This is intentionally simple and configuration-free for slice‑1.
    Adjust this mapping as needed for a real IdP.

    Precedence:
    - If `role` claim present and valid -> use directly.
    - Else if `groups` or `roles` contain known markers -> map.
    - Else -> default to VIEWER.
    """
    # Explicit role claim from IdP, if aligned
    explicit_role = claims.get("role")
    if isinstance(explicit_role, str):
        try:
            return UserRole(explicit_role)
        except ValueError:
            # Fall back to group mapping
            pass

    groups = claims.get("groups") or claims.get("roles") or []
    if isinstance(groups, str):
        groups = [groups]

    normalized = {str(g).lower() for g in groups}

    if {"admin", "oidc_admin"}.intersection(normalized):
        return UserRole.ADMIN
    if {"campaign_manager", "survey_manager"}.intersection(normalized):
        return UserRole.CAMPAIGN_MANAGER

    return UserRole.VIEWER