"""
RBAC (Role-Based Access Control) module.

Provides role extraction, permission checking, and route decorators
for enforcing minimum required roles on API endpoints.
"""

import functools
from datetime import datetime
from enum import IntEnum
from typing import Annotated, Callable, TypeVar

from fastapi import Depends, HTTPException, Request, status

from app.auth.middleware import CurrentUser
from app.auth.schemas import UserRole
from app.shared.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable)


class RoleLevel(IntEnum):
    """Role hierarchy levels for permission comparison.
    
    Higher values indicate more privileges.
    """
    VIEWER = 10
    CAMPAIGN_MANAGER = 20
    ADMIN = 30


ROLE_HIERARCHY: dict[UserRole, RoleLevel] = {
    UserRole.VIEWER: RoleLevel.VIEWER,
    UserRole.CAMPAIGN_MANAGER: RoleLevel.CAMPAIGN_MANAGER,
    UserRole.ADMIN: RoleLevel.ADMIN,
}


class RBACError(Exception):
    """Base exception for RBAC-related errors."""
    pass


class InsufficientPermissionsError(RBACError):
    """Raised when user lacks required permissions."""
    
    def __init__(
        self,
        user_role: UserRole,
        required_role: UserRole,
        endpoint: str,
        user_id: str | None = None,
    ):
        self.user_role = user_role
        self.required_role = required_role
        self.endpoint = endpoint
        self.user_id = user_id
        super().__init__(
            f"User with role '{user_role.value}' lacks permission for endpoint "
            f"'{endpoint}' (requires '{required_role.value}')"
        )


def get_role_level(role: UserRole) -> RoleLevel:
    """Get the hierarchy level for a role.
    
    Args:
        role: The user role to check.
        
    Returns:
        The corresponding role level.
    """
    return ROLE_HIERARCHY.get(role, RoleLevel.VIEWER)


def has_minimum_role(user_role: UserRole, required_role: UserRole) -> bool:
    """Check if user role meets minimum required role.
    
    Args:
        user_role: The user's current role.
        required_role: The minimum required role.
        
    Returns:
        True if user has sufficient permissions.
    """
    return get_role_level(user_role) >= get_role_level(required_role)


def can_modify_campaigns(role: UserRole) -> bool:
    """Check if role can modify campaigns.
    
    Campaign modification is restricted to campaign_manager and admin roles.
    
    Args:
        role: The user role to check.
        
    Returns:
        True if role can modify campaigns.
    """
    return role in (UserRole.CAMPAIGN_MANAGER, UserRole.ADMIN)


def is_admin(role: UserRole) -> bool:
    """Check if role is admin.
    
    Args:
        role: The user role to check.
        
    Returns:
        True if role is admin.
    """
    return role == UserRole.ADMIN


class AccessDeniedLog:
    """Structured log entry for access denied events."""
    
    def __init__(
        self,
        user_id: str,
        endpoint: str,
        user_role: UserRole,
        required_role: UserRole,
        timestamp: datetime | None = None,
    ):
        self.user_id = user_id
        self.endpoint = endpoint
        self.user_role = user_role
        self.required_role = required_role
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "event": "access_denied",
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "user_role": self.user_role.value,
            "required_role": self.required_role.value,
            "timestamp": self.timestamp.isoformat(),
        }


def log_access_denied(
    user_id: str,
    endpoint: str,
    user_role: UserRole,
    required_role: UserRole,
) -> None:
    """Log an access denied event.
    
    Args:
        user_id: The ID of the user who was denied.
        endpoint: The endpoint that was accessed.
        user_role: The user's role.
        required_role: The required role for the endpoint.
    """
    log_entry = AccessDeniedLog(
        user_id=user_id,
        endpoint=endpoint,
        user_role=user_role,
        required_role=required_role,
    )
    logger.warning(
        "Access denied",
        extra=log_entry.to_dict(),
    )


class RoleChecker:
    """Dependency class for checking user roles.
    
    This class is designed to be used as a FastAPI dependency
    to enforce role requirements on endpoints.
    """
    
    def __init__(self, required_role: UserRole):
        """Initialize role checker.
        
        Args:
            required_role: The minimum required role for access.
        """
        self.required_role = required_role
    
    async def __call__(
        self,
        request: Request,
        current_user: CurrentUser,
    ) -> CurrentUser:
        """Check if current user has required role.
        
        Args:
            request: The FastAPI request object.
            current_user: The authenticated user context.
            
        Returns:
            The current user if authorized.
            
        Raises:
            HTTPException: If user lacks required permissions.
        """
        if not has_minimum_role(current_user.role, self.required_role):
            log_access_denied(
                user_id=str(current_user.user_id),
                endpoint=str(request.url.path),
                user_role=current_user.role,
                required_role=self.required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_permissions",
                    "message": f"This endpoint requires '{self.required_role.value}' role or higher",
                    "required_role": self.required_role.value,
                    "user_role": current_user.role.value,
                },
            )
        return current_user


def require_role(required_role: UserRole) -> RoleChecker:
    """Create a role checker dependency.
    
    This is a factory function that creates a RoleChecker instance
    for use as a FastAPI dependency.
    
    Args:
        required_role: The minimum required role.
        
    Returns:
        A RoleChecker instance configured for the required role.
        
    Example:
        @router.get("/admin/config")
        async def get_config(
            user: Annotated[UserContext, Depends(require_role(UserRole.ADMIN))]
        ):
            ...
    """
    return RoleChecker(required_role)


# Pre-configured role checkers for common use cases
require_viewer = require_role(UserRole.VIEWER)
require_campaign_manager = require_role(UserRole.CAMPAIGN_MANAGER)
require_admin = require_role(UserRole.ADMIN)


# Type aliases for dependency injection
ViewerUser = Annotated[CurrentUser, Depends(require_viewer)]
CampaignManagerUser = Annotated[CurrentUser, Depends(require_campaign_manager)]
AdminUser = Annotated[CurrentUser, Depends(require_admin)]


def rbac_decorator(required_role: UserRole) -> Callable[[F], F]:
    """Decorator for enforcing RBAC on route handlers.
    
    This decorator can be used as an alternative to dependency injection
    for enforcing role requirements. It wraps the route handler and
    performs role checking before execution.
    
    Args:
        required_role: The minimum required role.
        
    Returns:
        A decorator function.
        
    Example:
        @router.get("/admin/settings")
        @rbac_decorator(UserRole.ADMIN)
        async def get_settings(current_user: CurrentUser):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get("current_user")
            if current_user is None:
                # Try to find it in args (less common)
                for arg in args:
                    if hasattr(arg, "role") and hasattr(arg, "user_id"):
                        current_user = arg
                        break
            
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            if not has_minimum_role(current_user.role, required_role):
                # Get request from kwargs if available for logging
                request = kwargs.get("request")
                endpoint = str(request.url.path) if request else "unknown"
                
                log_access_denied(
                    user_id=str(current_user.user_id),
                    endpoint=endpoint,
                    user_role=current_user.role,
                    required_role=required_role,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "insufficient_permissions",
                        "message": f"This endpoint requires '{required_role.value}' role or higher",
                        "required_role": required_role.value,
                        "user_role": current_user.role.value,
                    },
                )
            
            return await func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator