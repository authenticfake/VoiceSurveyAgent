"""Authentication and authorization module."""

from app.auth.domain import User, UserRole, RBACPolicy
from app.auth.oidc import OIDCConfig, OIDCClient, TokenPayload
from app.auth.dependencies import (
    get_current_user,
    require_role,
    require_any_role,
    get_optional_user,
)

__all__ = [
    "User",
    "UserRole",
    "RBACPolicy",
    "OIDCConfig",
    "OIDCClient",
    "TokenPayload",
    "get_current_user",
    "require_role",
    "require_any_role",
    "get_optional_user",
]