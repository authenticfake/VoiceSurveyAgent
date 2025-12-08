"""
Authentication and authorization module.

Provides OIDC integration, JWT validation, and RBAC middleware.
"""

from app.auth.middleware import AuthMiddleware
from app.auth.rbac import (
    RequireRole,
    get_current_user,
    require_admin,
    require_campaign_manager,
    require_viewer,
)
from app.auth.schemas import TokenPayload, UserRole

__all__ = [
    "AuthMiddleware",
    "RequireRole",
    "get_current_user",
    "require_admin",
    "require_campaign_manager",
    "require_viewer",
    "TokenPayload",
    "UserRole",
]