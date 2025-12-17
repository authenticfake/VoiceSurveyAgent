"""
RBAC dependencies for FastAPI.

Compat goals:
- Keep working with older REQ-* code that imports require_* symbols.
- Allow tests to patch `app.auth.middleware.get_current_user`.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Iterable, Set

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

import app.auth.middleware as auth_mw
from app.auth.middleware import AuthenticatedUser, security


class Role(str, Enum):
    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"

    @classmethod
    def from_string(cls, value: str) -> "Role":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown role: {value!r}") from exc

    def has_permission(self, required: "Role") -> bool:
        order = {
            Role.VIEWER: 0,
            Role.CAMPAIGN_MANAGER: 1,
            Role.ADMIN: 2,
        }
        return order[self] >= order[required]


async def _get_current_user_proxy(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser:
    """
    Proxy that calls `app.auth.middleware.get_current_user` at runtime.

    This is critical because tests patch:
        patch("app.auth.middleware.get_current_user", ...)
    """
    return await auth_mw.get_current_user(request, credentials)


def check_role_permission(user_role: str, required_role: Role) -> bool:
    """Check if a user role has permission for a required role."""
    try:
        role = Role.from_string(user_role)
        return role.has_permission(required_role)
    except ValueError:
        return False


async def require_authenticated_user(
    user: Annotated[AuthenticatedUser, Depends(_get_current_user_proxy)],
) -> AuthenticatedUser:
    """Any authenticated user (viewer included)."""
    return user


# Back-compat alias used by REQ-004 router imports
async def require_viewer(
    user: Annotated[AuthenticatedUser, Depends(_get_current_user_proxy)],
) -> AuthenticatedUser:
    """Viewer-level access (and above). In practice: any authenticated user."""
    return user


async def require_campaign_manager(
    user: Annotated[AuthenticatedUser, Depends(_get_current_user_proxy)],
) -> AuthenticatedUser:
    """Only campaign_manager (and optionally admin)."""
    role = getattr(user, "role", None) or "viewer"
    if role not in {"campaign_manager", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Insufficient permissions"},
        )
    return user


class RBACChecker:
    """Generic RBAC dependency factory."""

    def __init__(self, allowed_roles: str | Iterable[str]) -> None:
        if isinstance(allowed_roles, str):
            self.allowed_roles: Set[str] = {allowed_roles}
        else:
            self.allowed_roles = {r for r in allowed_roles}

    async def __call__(
        self,
        user: Annotated[AuthenticatedUser, Depends(_get_current_user_proxy)],
    ) -> AuthenticatedUser:
        role = getattr(user, "role", None) or "viewer"
        if role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Insufficient permissions"},
            )
        return user


__all__ = [
    "Role",
    "check_role_permission",
    "require_authenticated_user",
    "require_viewer",
    "require_campaign_manager",
    "RBACChecker",
]
