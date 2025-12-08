"""
Unit tests for RBAC configuration.
"""

import os
import pytest
from unittest.mock import patch

from app.auth.rbac.roles import Role
from app.auth.rbac.config import (
    RBACConfig,
    get_rbac_config,
    set_rbac_config,
)


class TestRBACConfig:
    """Tests for RBACConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RBACConfig()
        
        assert "/api/admin" in config.admin_paths
        assert config.log_denials is True
        assert config.log_request_details is True
    
    def test_from_env_defaults(self):
        """Test loading config from environment with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = RBACConfig.from_env()
        
        assert "/api/admin" in config.admin_paths
        assert config.log_denials is True
    
    def test_from_env_custom_values(self):
        """Test loading config from environment with custom values."""
        env_vars = {
            "RBAC_ADMIN_PATHS": "/admin,/superuser",
            "RBAC_MANAGER_PATHS": "/campaigns,/contacts",
            "RBAC_LOG_DENIALS": "false",
            "RBAC_LOG_REQUEST_DETAILS": "false",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = RBACConfig.from_env()
        
        assert "/admin" in config.admin_paths
        assert "/superuser" in config.admin_paths
        assert "/campaigns" in config.manager_paths
        assert "/contacts" in config.manager_paths
        assert config.log_denials is False
        assert config.log_request_details is False
    
    def test_get_required_role_for_admin_path(self):
        """Test getting required role for admin path."""
        config = RBACConfig(admin_paths=["/api/admin"])
        
        role = config.get_required_role_for_path("/api/admin/config")
        
        assert role == Role.ADMIN
    
    def test_get_required_role_for_manager_path(self):
        """Test getting required role for manager path."""
        config = RBACConfig(manager_paths=["/api/campaigns"])
        
        role = config.get_required_role_for_path("/api/campaigns/123")
        
        assert role == Role.CAMPAIGN_MANAGER
    
    def test_get_required_role_for_unrestricted_path(self):
        """Test getting required role for unrestricted path."""
        config = RBACConfig()
        
        role = config.get_required_role_for_path("/api/health")
        
        assert role is None
    
    def test_explicit_endpoint_roles(self):
        """Test explicit endpoint role configuration."""
        config = RBACConfig(
            endpoint_roles={
                "/api/special": "admin",
            }
        )
        
        role = config.get_required_role_for_path("/api/special/action")
        
        assert role == Role.ADMIN


class TestConfigSingleton:
    """Tests for config singleton functions."""
    
    def test_get_and_set_config(self):
        """Test getting and setting config."""
        custom_config = RBACConfig(
            admin_paths=["/custom/admin"],
            log_denials=False,
        )
        
        set_rbac_config(custom_config)
        retrieved = get_rbac_config()
        
        assert "/custom/admin" in retrieved.admin_paths
        assert retrieved.log_denials is False