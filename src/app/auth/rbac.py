"""
Role-Based Access Control (RBAC) middleware and decorators.

REQ-003: RBAC authorization middleware
"""

from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

from fastapi import Depends, HTTPException, Request, status

from app.auth.middleware import CurrentUser, get_current_user
from app.auth.models import UserRole
from app.shared.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class Role(str, Enum):
    """User roles with hierarchical ordering."""

    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"

    @classmethod
    def from_string(cls, role_str: str) -> "Role":
        """Convert string to Role enum.

        Args:
            role_str: Role string value.

        Returns:
            Corresponding Role enum.

        Raises:
            ValueError: If role string is invalid.
        """
        try:
            return cls(role_str)
        except ValueError:
            raise ValueError(f"Invalid role: {role_str}")

    def has_permission(self, required_role: "Role") -> bool:
        """Check if this role has permission for the required role.

        Role hierarchy: admin > campaign_manager > viewer

        Args:
            required_role: The minimum required role.

        Returns:
            True if this role has sufficient permissions.
        """
        hierarchy = {
            Role.ADMIN: 3,
            Role.CAMPAIGN_MANAGER: 2,
            Role.VIEWER: 1,
        }
        return hierarchy.get(self, 0) >= hierarchy.get(required_role, 0)


class RBACChecker:
    """Dependency class for role-based access control checks."""

    def __init__(self, minimum_role: Role) -> None:
        """Initialize RBAC checker.

        Args:
            minimum_role: Minimum role required for access.
        """
        self.minimum_role = minimum_role

    async def __call__(
        self,
        request: Request,
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        """Check if current user has required role.

        Args:
            request: FastAPI request object.
            current_user: Current authenticated user.

        Returns:
            Current user if authorized.

        Raises:
            HTTPException: If user lacks required role.
        """
        user_role = Role.from_string(current_user.role)

        if not user_role.has_permission(self.minimum_role):
            # Log denied access attempt
            logger.warning(
                "Access denied",
                extra={
                    "user_id": str(current_user.id),
                    "user_email": current_user.email,
                    "user_role": current_user.role,
                    "required_role": self.minimum_role.value,
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{self.minimum_role.value}' or higher required",
                    "required_role": self.minimum_role.value,
                    "current_role": current_user.role,
                },
            )

        logger.debug(
            "Access granted",
            extra={
                "user_id": str(current_user.id),
                "endpoint": str(request.url.path),
                "method": request.method,
            },
        )
        return current_user


# Pre-configured dependency instances for common role requirements
require_admin = RBACChecker(Role.ADMIN)
require_campaign_manager = RBACChecker(Role.CAMPAIGN_MANAGER)
require_viewer = RBACChecker(Role.VIEWER)


def require_role(minimum_role: Role) -> RBACChecker:
    """Create an RBAC checker for a specific role.

    Args:
        minimum_role: Minimum role required for access.

    Returns:
        RBACChecker instance configured for the role.

    Example:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: CurrentUser = Depends(require_role(Role.ADMIN))
        ):
            return {"message": "Admin access granted"}
    """
    return RBACChecker(minimum_role)


def check_role_permission(user_role: str, required_role: Role) -> bool:
    """Check if a user role has permission for a required role.

    Args:
        user_role: User's role as string.
        required_role: Required role for the operation.

    Returns:
        True if user has sufficient permissions.
    """
    try:
        role = Role.from_string(user_role)
        return role.has_permission(required_role)
    except ValueError:
        return False


def log_access_denied(
    user_id: str,
    user_email: str,
    user_role: str,
    endpoint: str,
    method: str,
    required_role: str,
    client_ip: str = "unknown",
) -> None:
    """Log an access denied event.

    Args:
        user_id: ID of the user who was denied.
        user_email: Email of the user.
        user_role: Role of the user.
        endpoint: Endpoint that was accessed.
        method: HTTP method used.
        required_role: Role that was required.
        client_ip: Client IP address.
    """
    logger.warning(
        "Access denied",
        extra={
            "user_id": user_id,
            "user_email": user_email,
            "user_role": user_role,
            "required_role": required_role,
            "endpoint": endpoint,
            "method": method,
            "client_ip": client_ip,
            "event_type": "access_denied",
        },
    )


class RolePermissions:
    """Configuration class for role-based permissions.

    Defines what operations each role can perform.
    """

    # Campaign operations
    CAMPAIGN_CREATE = {Role.ADMIN, Role.CAMPAIGN_MANAGER}
    CAMPAIGN_READ = {Role.ADMIN, Role.CAMPAIGN_MANAGER, Role.VIEWER}
    CAMPAIGN_UPDATE = {Role.ADMIN, Role.CAMPAIGN_MANAGER}
    CAMPAIGN_DELETE = {Role.ADMIN, Role.CAMPAIGN_MANAGER}
    CAMPAIGN_ACTIVATE = {Role.ADMIN, Role.CAMPAIGN_MANAGER}

    # Contact operations
    CONTACT_UPLOAD = {Role.ADMIN, Role.CAMPAIGN_MANAGER}
    CONTACT_READ = {Role.ADMIN, Role.CAMPAIGN_MANAGER, Role.VIEWER}
    CONTACT_EXPORT = {Role.ADMIN, Role.CAMPAIGN_MANAGER}

    # Admin operations
    ADMIN_CONFIG_READ = {Role.ADMIN}
    ADMIN_CONFIG_UPDATE = {Role.ADMIN}
    ADMIN_EXCLUSION_REMOVE = {Role.ADMIN}

    # Stats and reporting
    STATS_READ = {Role.ADMIN, Role.CAMPAIGN_MANAGER, Role.VIEWER}
    EXPORT_DATA = {Role.ADMIN, Role.CAMPAIGN_MANAGER}

    @classmethod
    def can_perform(cls, user_role: str, permission_set: set[Role]) -> bool:
        """Check if a user role can perform an operation.

        Args:
            user_role: User's role as string.
            permission_set: Set of roles allowed for the operation.

        Returns:
            True if user's role is in the permission set.
        """
        try:
            role = Role.from_string(user_role)
            return role in permission_set
        except ValueError:
            return False