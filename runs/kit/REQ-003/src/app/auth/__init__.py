"""
Authentication and authorization module.

Exports RBAC components for use throughout the application.
"""

from app.auth.rbac import (
    AdminUser,
    CampaignManagerUser,
    RBACError,
    RoleChecker,
    RoleLevel,
    ViewerUser,
    can_modify_campaigns,
    has_minimum_role,
    is_admin,
    rbac_decorator,
    require_admin,
    require_campaign_manager,
    require_role,
    require_viewer,
)
from app.auth.schemas import UserRole

__all__ = [
    # Role types
    "UserRole",
    "RoleLevel",
    # Permission checks
    "has_minimum_role",
    "can_modify_campaigns",
    "is_admin",
    # Dependencies
    "require_role",
    "require_viewer",
    "require_campaign_manager",
    "require_admin",
    "RoleChecker",
    # Type aliases
    "ViewerUser",
    "CampaignManagerUser",
    "AdminUser",
    # Decorator
    "rbac_decorator",
    # Exceptions
    "RBACError",
]