"""
Authentication and authorization module.

REQ-002: OIDC authentication integration
REQ-003: RBAC authorization middleware
"""

from app.auth.middleware import (
    AuthenticatedUser,
    CurrentUser,
    get_current_user,
    JWTTokenValidator,
)
from app.auth.rbac import (
    check_role_permission,
    log_access_denied,
    require_admin,
    require_campaign_manager,
    require_role,
    require_viewer,
    Role,
    RolePermissions,
    RBACChecker,
)

__all__ = [
    # Middleware exports
    "AuthenticatedUser",
    "CurrentUser",
    "get_current_user",
    "JWTTokenValidator",
    # RBAC exports
    "check_role_permission",
    "log_access_denied",
    "require_admin",
    "require_campaign_manager",
    "require_role",
    "require_viewer",
    "Role",
    "RolePermissions",
    "RBACChecker",
]