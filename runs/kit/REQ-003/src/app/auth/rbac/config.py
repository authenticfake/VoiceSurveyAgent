"""
RBAC configuration management.

Provides configurable RBAC rules that can be modified without code changes.
"""

import os
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from app.auth.rbac.roles import Role


class RolePermissionConfig(BaseModel):
    """Configuration for role permissions."""
    
    role: str
    permissions: Set[str] = Field(default_factory=set)
    
    class Config:
        frozen = True


class RBACConfig(BaseModel):
    """
    RBAC configuration model.
    
    Allows runtime configuration of role permissions and endpoint restrictions.
    """
    
    # Role permission overrides
    role_permissions: Dict[str, Set[str]] = Field(default_factory=dict)
    
    # Endpoint role requirements (path pattern -> minimum role)
    endpoint_roles: Dict[str, str] = Field(default_factory=dict)
    
    # Admin-only path prefixes
    admin_paths: List[str] = Field(default_factory=lambda: ["/api/admin"])
    
    # Campaign manager path prefixes
    manager_paths: List[str] = Field(default_factory=lambda: ["/api/campaigns"])
    
    # Whether to log access denials
    log_denials: bool = True
    
    # Whether to include request details in denial logs
    log_request_details: bool = True
    
    @classmethod
    def from_env(cls) -> "RBACConfig":
        """
        Load RBAC configuration from environment variables.
        
        Environment variables:
        - RBAC_ADMIN_PATHS: Comma-separated admin path prefixes
        - RBAC_MANAGER_PATHS: Comma-separated manager path prefixes
        - RBAC_LOG_DENIALS: Whether to log denials (true/false)
        - RBAC_LOG_REQUEST_DETAILS: Whether to log request details (true/false)
        
        Returns:
            RBACConfig instance
        """
        admin_paths = os.getenv("RBAC_ADMIN_PATHS", "/api/admin")
        manager_paths = os.getenv("RBAC_MANAGER_PATHS", "/api/campaigns")
        log_denials = os.getenv("RBAC_LOG_DENIALS", "true").lower() == "true"
        log_request_details = os.getenv("RBAC_LOG_REQUEST_DETAILS", "true").lower() == "true"
        
        return cls(
            admin_paths=[p.strip() for p in admin_paths.split(",") if p.strip()],
            manager_paths=[p.strip() for p in manager_paths.split(",") if p.strip()],
            log_denials=log_denials,
            log_request_details=log_request_details,
        )
    
    def get_required_role_for_path(self, path: str) -> Optional[Role]:
        """
        Get the minimum required role for a path.
        
        Args:
            path: The URL path to check
            
        Returns:
            Required Role or None if no restriction
        """
        # Check explicit endpoint roles first
        for pattern, role_str in self.endpoint_roles.items():
            if path.startswith(pattern):
                try:
                    return Role.from_string(role_str)
                except ValueError:
                    continue
        
        # Check admin paths
        for admin_path in self.admin_paths:
            if path.startswith(admin_path):
                return Role.ADMIN
        
        # Check manager paths
        for manager_path in self.manager_paths:
            if path.startswith(manager_path):
                return Role.CAMPAIGN_MANAGER
        
        return None


# Global configuration instance
_config: Optional[RBACConfig] = None


def get_rbac_config() -> RBACConfig:
    """
    Get the current RBAC configuration.
    
    Returns:
        Current RBACConfig instance
    """
    global _config
    if _config is None:
        _config = RBACConfig.from_env()
    return _config


def set_rbac_config(config: RBACConfig) -> None:
    """
    Set the RBAC configuration.
    
    Args:
        config: New RBACConfig to use
    """
    global _config
    _config = config