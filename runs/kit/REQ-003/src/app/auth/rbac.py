"""
RBAC (Role-Based Access Control) authorization module.

Provides decorators and utilities for enforcing role-based access control
on FastAPI routes.
"""

import functools
from datetime import datetime
from enum import Enum
from typing import Annotated, Callable, TypeVar

from fastapi import Depends, HTTPException, Request, status

from app.auth.middleware import CurrentUser
from app.auth.schemas import UserRole
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable)


class Permission(str, Enum):
    """Permission enumeration for fine-grained access control."""
    
    # Campaign permissions
    CAMPAIGN_READ = "campaign:read"
    CAMPAIGN_CREATE = "campaign:create"
    CAMPAIGN_UPDATE = "campaign:update"
    CAMPAIGN_DELETE = "campaign:delete"
    CAMPAIGN_ACTIVATE = "campaign:activate"
    
    # Contact permissions
    CONTACT_READ = "contact:read"
    CONTACT_UPLOAD = "contact:upload"
    CONTACT_EXPORT = "contact:export"
    
    # Admin permissions
    ADMIN_CONFIG_READ = "admin:config:read"
    ADMIN_CONFIG_UPDATE = "admin:config:update"
    ADMIN_EXCLUSION_MANAGE = "admin:exclusion:manage"
    
    # Stats permissions
    STATS_READ = "stats:read"
    STATS_EXPORT = "stats:export"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: {
        # Admin has all permissions
        Permission.CAMPAIGN_READ,
        Permission.CAMPAIGN_CREATE,
        Permission.CAMPAIGN_UPDATE,
        Permission.CAMPAIGN_DELETE,
        Permission.CAMPAIGN_ACTIVATE,
        Permission.CONTACT_READ,
        Permission.CONTACT_UPLOAD,
        Permission.CONTACT_EXPORT,
        Permission.ADMIN_CONFIG_READ,
        Permission.ADMIN_CONFIG_UPDATE,
        Permission.ADMIN_EXCLUSION_MANAGE,
        Permission.STATS_READ,
        Permission.STATS_EXPORT,
    },
    UserRole.CAMPAIGN_MANAGER: {
        # Campaign manager can manage campaigns and contacts
        Permission.CAMPAIGN_READ,
        Permission.CAMPAIGN_CREATE,
        Permission.CAMPAIGN_UPDATE,
        Permission.CAMPAIGN_DELETE,
        Permission.CAMPAIGN_ACTIVATE,
        Permission.CONTACT_READ,
        Permission.CONTACT_UPLOAD,
        Permission.CONTACT_EXPORT,
        Permission.STATS_READ,
        Permission.STATS_EXPORT,
    },
    UserRole.VIEWER: {
        # Viewer has read-only access
        Permission.CAMPAIGN_READ,
        Permission.CONTACT_READ,
        Permission.STATS_READ,
    },
}


def get_role_permissions(role: UserRole) -> set[Permission]:
    """Get permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_role_permissions(role)


def has_minimum_role(user_role: UserRole, required_role: UserRole) -> bool:
    """
    Check if user role meets minimum required role.
    
    Role hierarchy: admin > campaign_manager > viewer
    """
    role_hierarchy = {
        UserRole.ADMIN: 3,
        UserRole.CAMPAIGN_MANAGER: 2,
        UserRole.VIEWER: 1,
    }
    return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)


class AccessDeniedLog:
    """Structure for logging access denied events."""
    
    def __init__(
        self,
        user_id: str,
        user_role: str,
        endpoint: str,
        method: str,
        required_role: str | None = None,
        required_permission: str | None = None,
        timestamp: datetime | None = None,
    ):
        self.user_id = user_id
        self.user_role = user_role
        self.endpoint = endpoint
        self.method = method
        self.required_role = required_role
        self.required_permission = required_permission
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "event": "access_denied",
            "user_id": self.user_id,
            "user_role": self.user_role,
            "endpoint": self.endpoint,
            "method": self.method,
            "required_role": self.required_role,
            "required_permission": self.required_permission,
            "timestamp": self.timestamp.isoformat(),
        }


def log_access_denied(
    request: Request,
    user_id: str,
    user_role: str,
    required_role: str | None = None,
    required_permission: str | None = None,
) -> None:
    """Log access denied event with structured data."""
    log_entry = AccessDeniedLog(
        user_id=user_id,
        user_role=user_role,
        endpoint=str(request.url.path),
        method=request.method,
        required_role=required_role,
        required_permission=required_permission,
    )
    logger.warning("Access denied", extra=log_entry.to_dict())


def require_role(minimum_role: UserRole) -> Callable:
    """
    Dependency factory that enforces minimum role requirement.
    
    Usage:
        @router.get("/admin/config")
        async def get_config(user: CurrentUser = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    async def role_checker(
        request: Request,
        user: CurrentUser,
    ) -> CurrentUser:
        if not has_minimum_role(user.role, minimum_role):
            log_access_denied(
                request=request,
                user_id=str(user.id),
                user_role=user.role.value,
                required_role=minimum_role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {minimum_role.value}",
            )
        return user
    
    return role_checker


def require_permission(permission: Permission) -> Callable:
    """
    Dependency factory that enforces specific permission requirement.
    
    Usage:
        @router.post("/campaigns")
        async def create_campaign(
            user: CurrentUser = Depends(require_permission(Permission.CAMPAIGN_CREATE))
        ):
            ...
    """
    async def permission_checker(
        request: Request,
        user: CurrentUser,
    ) -> CurrentUser:
        if not has_permission(user.role, permission):
            log_access_denied(
                request=request,
                user_id=str(user.id),
                user_role=user.role.value,
                required_permission=permission.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required permission: {permission.value}",
            )
        return user
    
    return permission_checker


# Convenience type aliases for common role requirements
AdminUser = Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))]
CampaignManagerUser = Annotated[CurrentUser, Depends(require_role(UserRole.CAMPAIGN_MANAGER))]
ViewerUser = Annotated[CurrentUser, Depends(require_role(UserRole.VIEWER))]


class RBACMiddleware:
    """
    RBAC middleware for route-level access control.
    
    Can be used to apply role requirements to entire routers.
    """
    
    def __init__(self, minimum_role: UserRole):
        self.minimum_role = minimum_role
    
    async def __call__(
        self,
        request: Request,
        user: CurrentUser,
    ) -> CurrentUser:
        if not has_minimum_role(user.role, self.minimum_role):
            log_access_denied(
                request=request,
                user_id=str(user.id),
                user_role=user.role.value,
                required_role=self.minimum_role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {self.minimum_role.value}",
            )
        return user