"""
Authentication and authorization module.

Provides OIDC integration, JWT validation, and RBAC middleware.
"""

from app.auth.rbac import (
    AdminUser,
    CampaignManagerUser,
    RequireRole,
    ViewerUser,
    get_current_user,
    require_admin,
    require_campaign_manager,
    require_viewer,
)
from app.auth.schemas import TokenPayload, UserContext, UserRole
from app.auth.service import AuthService

__all__ = [
    "AdminUser",
    "AuthService",
    "CampaignManagerUser",
    "RequireRole",
    "TokenPayload",
    "UserContext",
    "UserRole",
    "ViewerUser",
    "get_current_user",
    "require_admin",
    "require_campaign_manager",
    "require_viewer",
]