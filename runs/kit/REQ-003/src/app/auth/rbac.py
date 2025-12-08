"""
RBAC (Role-Based Access Control) module.

Provides role extraction, permission checking, and route decorators
for enforcing authorization based on user roles.
"""

from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, status

from app.auth.schemas import UserRole
from app.shared.logging import get_logger

logger = get_logger(__name__)


class Permission(str, Enum):
    """Permission enumeration for fine-grained access control."""

    # Campaign permissions
    CAMPAIGN_CREATE = "campaign:create"
    CAMPAIGN_READ = "campaign:read"
    CAMPAIGN_UPDATE = "campaign:update"
    CAMPAIGN_DELETE = "campaign:delete"
    CAMPAIGN_ACTIVATE = "campaign:activate"

    # Contact permissions
    CONTACT_READ = "contact:read"
    CONTACT_UPLOAD = "contact:upload"
    CONTACT_EXPORT = "contact:export"

    # Exclusion permissions
    EXCLUSION_READ = "exclusion:read"
    EXCLUSION_MANAGE = "exclusion:manage"

    # Admin permissions
    ADMIN_CONFIG_READ = "admin:config:read"
    ADMIN_CONFIG_WRITE = "admin:config:write"

    # Stats permissions
    STATS_READ = "stats:read"
    STATS_EXPORT = "stats:export"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: {
        # Admin has all permissions
        Permission.CAMPAIGN_CREATE,
        Permission.CAMPAIGN_READ,
        Permission.CAMPAIGN_UPDATE,
        Permission.CAMPAIGN_DELETE,
        Permission.CAMPAIGN_ACTIVATE,
        Permission.CONTACT_READ,
        Permission.CONTACT_UPLOAD,
        Permission.CONTACT_EXPORT,
        Permission.EXCLUSION_READ,
        Permission.EXCLUSION_MANAGE,
        Permission.ADMIN_CONFIG_READ,
        Permission.ADMIN_CONFIG_WRITE,
        Permission.STATS_READ,
        Permission.STATS_EXPORT,
    },
    UserRole.CAMPAIGN_MANAGER: {
        # Campaign manager can manage campaigns and contacts
        Permission.CAMPAIGN_CREATE,
        Permission.CAMPAIGN_READ,
        Permission.CAMPAIGN_UPDATE,
        Permission.CAMPAIGN_DELETE,
        Permission.CAMPAIGN_ACTIVATE,
        Permission.CONTACT_READ,
        Permission.CONTACT_UPLOAD,
        Permission.CONTACT_EXPORT,
        Permission.EXCLUSION_READ,
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
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_role_permissions(role)


def has_any_permission(role: UserRole, permissions: set[Permission]) -> bool:
    """Check if a role has any of the specified permissions."""
    role_perms = get_role_permissions(role)
    return bool(role_perms & permissions)


def has_all_permissions(role: UserRole, permissions: set[Permission]) -> bool:
    """Check if a role has all of the specified permissions."""
    role_perms = get_role_permissions(role)
    return permissions <= role_perms


class RBACChecker:
    """
    RBAC checker for FastAPI dependency injection.

    Validates that the current user has the required role or permission.
    """

    def __init__(
        self,
        minimum_role: UserRole | None = None,
        required_permission: Permission | None = None,
        any_of_permissions: set[Permission] | None = None,
        all_of_permissions: set[Permission] | None = None,
    ) -> None:
        """
        Initialize RBAC checker.

        Args:
            minimum_role: Minimum role required (uses role hierarchy)
            required_permission: Single permission required
            any_of_permissions: Any of these permissions grants access
            all_of_permissions: All of these permissions required
        """
        self.minimum_role = minimum_role
        self.required_permission = required_permission
        self.any_of_permissions = any_of_permissions
        self.all_of_permissions = all_of_permissions

    async def __call__(self, request: Request) -> None:
        """
        Validate RBAC requirements.

        Raises:
            HTTPException: If user lacks required authorization
        """
        # Get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user is None:
            logger.warning(
                "RBAC check failed: no user in request state",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user_role = user.role
        user_id = str(user.id)
        endpoint = f"{request.method} {request.url.path}"

        # Check minimum role
        if self.minimum_role is not None:
            if not self._check_role_hierarchy(user_role, self.minimum_role):
                self._log_denied(user_id, endpoint, f"minimum_role={self.minimum_role}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires {self.minimum_role.value} role or higher",
                )

        # Check single permission
        if self.required_permission is not None:
            if not has_permission(user_role, self.required_permission):
                self._log_denied(
                    user_id, endpoint, f"permission={self.required_permission}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {self.required_permission.value}",
                )

        # Check any of permissions
        if self.any_of_permissions is not None:
            if not has_any_permission(user_role, self.any_of_permissions):
                perms = [p.value for p in self.any_of_permissions]
                self._log_denied(user_id, endpoint, f"any_of={perms}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of: {', '.join(perms)}",
                )

        # Check all of permissions
        if self.all_of_permissions is not None:
            if not has_all_permissions(user_role, self.all_of_permissions):
                perms = [p.value for p in self.all_of_permissions]
                self._log_denied(user_id, endpoint, f"all_of={perms}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires all of: {', '.join(perms)}",
                )

        logger.debug(
            "RBAC check passed",
            extra={
                "user_id": user_id,
                "role": user_role.value,
                "endpoint": endpoint,
            },
        )

    def _check_role_hierarchy(
        self, user_role: UserRole, minimum_role: UserRole
    ) -> bool:
        """Check if user role meets minimum role requirement."""
        hierarchy = {
            UserRole.ADMIN: 3,
            UserRole.CAMPAIGN_MANAGER: 2,
            UserRole.VIEWER: 1,
        }
        return hierarchy.get(user_role, 0) >= hierarchy.get(minimum_role, 0)

    def _log_denied(self, user_id: str, endpoint: str, reason: str) -> None:
        """Log denied access attempt."""
        logger.warning(
            "Access denied",
            extra={
                "user_id": user_id,
                "endpoint": endpoint,
                "reason": reason,
            },
        )


# Convenience dependency factories
def require_admin() -> RBACChecker:
    """Require admin role."""
    return RBACChecker(minimum_role=UserRole.ADMIN)


def require_campaign_manager() -> RBACChecker:
    """Require campaign_manager role or higher."""
    return RBACChecker(minimum_role=UserRole.CAMPAIGN_MANAGER)


def require_viewer() -> RBACChecker:
    """Require viewer role or higher (any authenticated user)."""
    return RBACChecker(minimum_role=UserRole.VIEWER)


def require_permission(permission: Permission) -> RBACChecker:
    """Require a specific permission."""
    return RBACChecker(required_permission=permission)


def require_any_permission(*permissions: Permission) -> RBACChecker:
    """Require any of the specified permissions."""
    return RBACChecker(any_of_permissions=set(permissions))


def require_all_permissions(*permissions: Permission) -> RBACChecker:
    """Require all of the specified permissions."""
    return RBACChecker(all_of_permissions=set(permissions))


# Decorator-based RBAC for non-FastAPI contexts
def rbac_required(
    minimum_role: UserRole | None = None,
    permission: Permission | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for RBAC enforcement.

    Can be used on service methods that receive a user context.

    Args:
        minimum_role: Minimum role required
        permission: Specific permission required

    Returns:
        Decorated function that checks RBAC before execution
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Look for user in kwargs or first arg
            user = kwargs.get("user") or kwargs.get("current_user")
            if user is None and args:
                # Check if first arg has a user attribute
                first_arg = args[0]
                if hasattr(first_arg, "user"):
                    user = first_arg.user

            if user is None:
                raise ValueError("No user context found for RBAC check")

            user_role = user.role

            if minimum_role is not None:
                hierarchy = {
                    UserRole.ADMIN: 3,
                    UserRole.CAMPAIGN_MANAGER: 2,
                    UserRole.VIEWER: 1,
                }
                if hierarchy.get(user_role, 0) < hierarchy.get(minimum_role, 0):
                    raise PermissionError(
                        f"Requires {minimum_role.value} role or higher"
                    )

            if permission is not None:
                if not has_permission(user_role, permission):
                    raise PermissionError(
                        f"Missing required permission: {permission.value}"
                    )

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            user = kwargs.get("user") or kwargs.get("current_user")
            if user is None and args:
                first_arg = args[0]
                if hasattr(first_arg, "user"):
                    user = first_arg.user

            if user is None:
                raise ValueError("No user context found for RBAC check")

            user_role = user.role

            if minimum_role is not None:
                hierarchy = {
                    UserRole.ADMIN: 3,
                    UserRole.CAMPAIGN_MANAGER: 2,
                    UserRole.VIEWER: 1,
                }
                if hierarchy.get(user_role, 0) < hierarchy.get(minimum_role, 0):
                    raise PermissionError(
                        f"Requires {minimum_role.value} role or higher"
                    )

            if permission is not None:
                if not has_permission(user_role, permission):
                    raise PermissionError(
                        f"Missing required permission: {permission.value}"
                    )

            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator