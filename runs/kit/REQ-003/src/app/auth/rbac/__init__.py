"""
RBAC Authorization Module for VoiceSurveyAgent.

This module provides role-based access control functionality including:
- Role definitions and hierarchy
- Permission decorators for route protection
- Access denial logging
"""

from app.auth.rbac.roles import Role, RoleHierarchy
from app.auth.rbac.permissions import (
    require_role,
    require_any_role,
    get_current_user_role,
)
from app.auth.rbac.logging import log_access_denied

__all__ = [
    "Role",
    "RoleHierarchy",
    "require_role",
    "require_any_role",
    "get_current_user_role",
    "log_access_denied",
]