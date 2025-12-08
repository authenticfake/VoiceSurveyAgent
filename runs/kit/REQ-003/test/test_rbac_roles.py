"""
Unit tests for RBAC role definitions and hierarchy.
"""

import pytest

from app.auth.rbac.roles import Role, RoleHierarchy


class TestRole:
    """Tests for Role enum."""
    
    def test_role_values(self):
        """Test that all expected roles exist."""
        assert Role.ADMIN.value == "admin"
        assert Role.CAMPAIGN_MANAGER.value == "campaign_manager"
        assert Role.VIEWER.value == "viewer"
    
    def test_from_string_valid(self):
        """Test converting valid strings to Role."""
        assert Role.from_string("admin") == Role.ADMIN
        assert Role.from_string("ADMIN") == Role.ADMIN
        assert Role.from_string("campaign_manager") == Role.CAMPAIGN_MANAGER
        assert Role.from_string("viewer") == Role.VIEWER
    
    def test_from_string_invalid(self):
        """Test that invalid strings raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Role.from_string("invalid_role")
        assert "Invalid role" in str(exc_info.value)
        assert "admin" in str(exc_info.value)


class TestRoleHierarchy:
    """Tests for RoleHierarchy."""
    
    def test_privilege_levels(self):
        """Test that privilege levels are correctly ordered."""
        admin_level = RoleHierarchy.get_privilege_level(Role.ADMIN)
        manager_level = RoleHierarchy.get_privilege_level(Role.CAMPAIGN_MANAGER)
        viewer_level = RoleHierarchy.get_privilege_level(Role.VIEWER)
        
        assert admin_level > manager_level > viewer_level
    
    def test_has_minimum_role_admin(self):
        """Test admin has access to all role levels."""
        assert RoleHierarchy.has_minimum_role(Role.ADMIN, Role.ADMIN)
        assert RoleHierarchy.has_minimum_role(Role.ADMIN, Role.CAMPAIGN_MANAGER)
        assert RoleHierarchy.has_minimum_role(Role.ADMIN, Role.VIEWER)
    
    def test_has_minimum_role_campaign_manager(self):
        """Test campaign_manager has access to manager and viewer levels."""
        assert not RoleHierarchy.has_minimum_role(Role.CAMPAIGN_MANAGER, Role.ADMIN)
        assert RoleHierarchy.has_minimum_role(Role.CAMPAIGN_MANAGER, Role.CAMPAIGN_MANAGER)
        assert RoleHierarchy.has_minimum_role(Role.CAMPAIGN_MANAGER, Role.VIEWER)
    
    def test_has_minimum_role_viewer(self):
        """Test viewer only has access to viewer level."""
        assert not RoleHierarchy.has_minimum_role(Role.VIEWER, Role.ADMIN)
        assert not RoleHierarchy.has_minimum_role(Role.VIEWER, Role.CAMPAIGN_MANAGER)
        assert RoleHierarchy.has_minimum_role(Role.VIEWER, Role.VIEWER)
    
    def test_admin_permissions(self):
        """Test admin has all permissions."""
        admin_perms = RoleHierarchy.get_permissions(Role.ADMIN)
        
        assert "campaigns:read" in admin_perms
        assert "campaigns:create" in admin_perms
        assert "campaigns:update" in admin_perms
        assert "campaigns:delete" in admin_perms
        assert "config:read" in admin_perms
        assert "config:update" in admin_perms
        assert "exclusions:delete" in admin_perms
    
    def test_campaign_manager_permissions(self):
        """Test campaign_manager has appropriate permissions."""
        manager_perms = RoleHierarchy.get_permissions(Role.CAMPAIGN_MANAGER)
        
        assert "campaigns:read" in manager_perms
        assert "campaigns:create" in manager_perms
        assert "campaigns:update" in manager_perms
        assert "campaigns:delete" not in manager_perms
        assert "config:read" not in manager_perms
        assert "config:update" not in manager_perms
    
    def test_viewer_permissions(self):
        """Test viewer has read-only permissions."""
        viewer_perms = RoleHierarchy.get_permissions(Role.VIEWER)
        
        assert "campaigns:read" in viewer_perms
        assert "campaigns:create" not in viewer_perms
        assert "campaigns:update" not in viewer_perms
        assert "stats:read" in viewer_perms
        assert "stats:export" not in viewer_perms
    
    def test_has_permission(self):
        """Test has_permission method."""
        assert RoleHierarchy.has_permission(Role.ADMIN, "config:update")
        assert not RoleHierarchy.has_permission(Role.CAMPAIGN_MANAGER, "config:update")
        assert not RoleHierarchy.has_permission(Role.VIEWER, "campaigns:create")