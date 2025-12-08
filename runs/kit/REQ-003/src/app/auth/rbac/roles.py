"""
Role definitions and hierarchy for RBAC.

Defines the available roles and their hierarchical relationships
for the VoiceSurveyAgent application.
"""

from enum import Enum
from typing import Set


class Role(str, Enum):
    """
    User roles in the system.
    
    Roles are ordered by privilege level:
    - admin: Full system access
    - campaign_manager: Can create/modify campaigns
    - viewer: Read-only access
    """
    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"
    
    @classmethod
    def from_string(cls, value: str) -> "Role":
        """
        Convert string to Role enum.
        
        Args:
            value: Role string value
            
        Returns:
            Corresponding Role enum
            
        Raises:
            ValueError: If role string is invalid
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_roles = [r.value for r in cls]
            raise ValueError(
                f"Invalid role '{value}'. Valid roles: {valid_roles}"
            )


class RoleHierarchy:
    """
    Defines role hierarchy and permission inheritance.
    
    Higher privilege roles inherit permissions from lower privilege roles.
    admin > campaign_manager > viewer
    """
    
    _hierarchy: dict[Role, int] = {
        Role.ADMIN: 100,
        Role.CAMPAIGN_MANAGER: 50,
        Role.VIEWER: 10,
    }
    
    _role_permissions: dict[Role, Set[str]] = {
        Role.VIEWER: {
            "campaigns:read",
            "contacts:read",
            "stats:read",
            "calls:read",
        },
        Role.CAMPAIGN_MANAGER: {
            "campaigns:read",
            "campaigns:create",
            "campaigns:update",
            "campaigns:activate",
            "campaigns:pause",
            "contacts:read",
            "contacts:upload",
            "stats:read",
            "stats:export",
            "calls:read",
        },
        Role.ADMIN: {
            "campaigns:read",
            "campaigns:create",
            "campaigns:update",
            "campaigns:delete",
            "campaigns:activate",
            "campaigns:pause",
            "contacts:read",
            "contacts:upload",
            "exclusions:read",
            "exclusions:create",
            "exclusions:delete",
            "stats:read",
            "stats:export",
            "calls:read",
            "config:read",
            "config:update",
            "users:read",
            "users:update",
        },
    }
    
    @classmethod
    def get_privilege_level(cls, role: Role) -> int:
        """
        Get numeric privilege level for a role.
        
        Args:
            role: The role to check
            
        Returns:
            Numeric privilege level (higher = more privileges)
        """
        return cls._hierarchy.get(role, 0)
    
    @classmethod
    def has_minimum_role(cls, user_role: Role, required_role: Role) -> bool:
        """
        Check if user role meets minimum required role.
        
        Args:
            user_role: The user's current role
            required_role: The minimum required role
            
        Returns:
            True if user role has sufficient privileges
        """
        return cls.get_privilege_level(user_role) >= cls.get_privilege_level(required_role)
    
    @classmethod
    def has_permission(cls, role: Role, permission: str) -> bool:
        """
        Check if a role has a specific permission.
        
        Args:
            role: The role to check
            permission: The permission string (e.g., 'campaigns:create')
            
        Returns:
            True if role has the permission
        """
        role_perms = cls._role_permissions.get(role, set())
        return permission in role_perms
    
    @classmethod
    def get_permissions(cls, role: Role) -> Set[str]:
        """
        Get all permissions for a role.
        
        Args:
            role: The role to get permissions for
            
        Returns:
            Set of permission strings
        """
        return cls._role_permissions.get(role, set()).copy()