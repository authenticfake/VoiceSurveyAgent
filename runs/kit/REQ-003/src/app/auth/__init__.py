"""
Authentication and authorization module.

Exports OIDC authentication, JWT validation, and RBAC components.
"""

from app.auth.middleware import (
    AuthMiddleware,
    CurrentUser,
    get_current_user,
    get_optional_user,
)
from app.auth.rbac import (
    AdminUser,
    CampaignManagerUser,
    Permission,
    RBACMiddleware,
    ViewerUser,
    get_role_permissions,
    has_minimum_role,
    has_permission,
    require_permission,
    require_role,
)
from app.auth.schemas import (
    OIDCConfig,
    TokenPayload,
    UserContext,
    UserRole,
)
from app.auth.service import AuthService

__all__ = [
    # Middleware
    "AuthMiddleware",
    "CurrentUser",
    "get_current_user",
    "get_optional_user",
    # RBAC
    "AdminUser",
    "CampaignManagerUser",
    "Permission",
    "RBACMiddleware",
    "ViewerUser",
    "get_role_permissions",
    "has_minimum_role",
    "has_permission",
    "require_permission",
    "require_role",
    # Schemas
    "OIDCConfig",
    "TokenPayload",
    "UserContext",
    "UserRole",
    # Service
    "AuthService",
]