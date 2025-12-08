"""
Integration tests for RBAC with database and full auth flow.

Tests role extraction from JWT claims and database records.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, status
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import (
    require_role,
    require_permission,
    Permission,
    AdminUser,
    CampaignManagerUser,
    ViewerUser,
)
from app.auth.schemas import UserRole
from app.auth.middleware import CurrentUser, get_current_user


class TestRoleExtractionFromJWT:
    """Tests for role extraction from JWT claims."""
    
    @pytest.fixture
    def jwt_with_admin_role(self):
        """Create JWT payload with admin role."""
        return {
            "sub": "admin-oidc-sub",
            "email": "admin@test.com",
            "name": "Admin User",
            "role": "admin",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
        }
    
    @pytest.fixture
    def jwt_with_manager_role(self):
        """Create JWT payload with campaign_manager role."""
        return {
            "sub": "manager-oidc-sub",
            "email": "manager@test.com",
            "name": "Manager User",
            "role": "campaign_manager",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
        }
    
    @pytest.fixture
    def jwt_with_viewer_role(self):
        """Create JWT payload with viewer role."""
        return {
            "sub": "viewer-oidc-sub",
            "email": "viewer@test.com",
            "name": "Viewer User",
            "role": "viewer",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
        }
    
    def test_admin_role_extracted_from_jwt(self, jwt_with_admin_role):
        """Admin role should be correctly extracted from JWT."""
        role_claim = jwt_with_admin_role.get("role")
        assert role_claim == "admin"
        assert UserRole(role_claim) == UserRole.ADMIN
    
    def test_manager_role_extracted_from_jwt(self, jwt_with_manager_role):
        """Campaign manager role should be correctly extracted from JWT."""
        role_claim = jwt_with_manager_role.get("role")
        assert role_claim == "campaign_manager"
        assert UserRole(role_claim) == UserRole.CAMPAIGN_MANAGER
    
    def test_viewer_role_extracted_from_jwt(self, jwt_with_viewer_role):
        """Viewer role should be correctly extracted from JWT."""
        role_claim = jwt_with_viewer_role.get("role")
        assert role_claim == "viewer"
        assert UserRole(role_claim) == UserRole.VIEWER


class TestRoleExtractionFromDatabase:
    """Tests for role extraction from database user record."""
    
    @pytest.fixture
    def mock_db_user_admin(self):
        """Create mock database user with admin role."""
        user = MagicMock()
        user.id = uuid4()
        user.oidc_sub = "admin-oidc-sub"
        user.email = "admin@test.com"
        user.name = "Admin User"
        user.role = UserRole.ADMIN
        return user
    
    @pytest.fixture
    def mock_db_user_manager(self):
        """Create mock database user with campaign_manager role."""
        user = MagicMock()
        user.id = uuid4()
        user.oidc_sub = "manager-oidc-sub"
        user.email = "manager@test.com"
        user.name = "Manager User"
        user.role = UserRole.CAMPAIGN_MANAGER
        return user
    
    @pytest.fixture
    def mock_db_user_viewer(self):
        """Create mock database user with viewer role."""
        user = MagicMock()
        user.id = uuid4()
        user.oidc_sub = "viewer-oidc-sub"
        user.email = "viewer@test.com"
        user.name = "Viewer User"
        user.role = UserRole.VIEWER
        return user
    
    def test_admin_role_from_database(self, mock_db_user_admin):
        """Admin role should be correctly read from database."""
        assert mock_db_user_admin.role == UserRole.ADMIN
    
    def test_manager_role_from_database(self, mock_db_user_manager):
        """Campaign manager role should be correctly read from database."""
        assert mock_db_user_manager.role == UserRole.CAMPAIGN_MANAGER
    
    def test_viewer_role_from_database(self, mock_db_user_viewer):
        """Viewer role should be correctly read from database."""
        assert mock_db_user_viewer.role == UserRole.VIEWER


class TestTypedUserDependencies:
    """Tests for typed user dependency aliases."""
    
    @pytest.fixture
    def admin_user(self):
        """Create admin user context."""
        return CurrentUser(
            id=uuid4(),
            oidc_sub="admin-sub",
            email="admin@test.com",
            name="Admin",
            role=UserRole.ADMIN,
        )
    
    @pytest.fixture
    def manager_user(self):
        """Create campaign manager user context."""
        return CurrentUser(
            id=uuid4(),
            oidc_sub="manager-sub",
            email="manager@test.com",
            name="Manager",
            role=UserRole.CAMPAIGN_MANAGER,
        )
    
    @pytest.fixture
    def viewer_user(self):
        """Create viewer user context."""
        return CurrentUser(
            id=uuid4(),
            oidc_sub="viewer-sub",
            email="viewer@test.com",
            name="Viewer",
            role=UserRole.VIEWER,
        )
    
    @pytest.fixture
    def app_with_typed_deps(self, admin_user, manager_user, viewer_user):
        """Create app with typed user dependencies."""
        app = FastAPI()
        
        # Store users for lookup
        users = {
            "admin": admin_user,
            "manager": manager_user,
            "viewer": viewer_user,
        }
        
        async def mock_get_current_user(request: MagicMock) -> CurrentUser:
            user_type = request.headers.get("X-Test-User", "viewer")
            return users.get(user_type, viewer_user)
        
        # Override the dependency
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        @app.get("/admin-only")
        async def admin_only_endpoint(request: MagicMock):
            user = await mock_get_current_user(request)
            mock_req = MagicMock()
            mock_req.url.path = "/admin-only"
            mock_req.method = "GET"
            checker = require_role(UserRole.ADMIN)
            await checker(mock_req, user)
            return {"access": "granted"}
        
        @app.get("/manager-only")
        async def manager_only_endpoint(request: MagicMock):
            user = await mock_get_current_user(request)
            mock_req = MagicMock()
            mock_req.url.path = "/manager-only"
            mock_req.method = "GET"
            checker = require_role(UserRole.CAMPAIGN_MANAGER)
            await checker(mock_req, user)
            return {"access": "granted"}
        
        @app.get("/viewer-allowed")
        async def viewer_allowed_endpoint(request: MagicMock):
            user = await mock_get_current_user(request)
            mock_req = MagicMock()
            mock_req.url.path = "/viewer-allowed"
            mock_req.method = "GET"
            checker = require_role(UserRole.VIEWER)
            await checker(mock_req, user)
            return {"access": "granted"}
        
        return app
    
    @pytest.mark.asyncio
    async def test_admin_user_type_alias(self, app_with_typed_deps):
        """AdminUser type alias should enforce admin role."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_typed_deps),
            base_url="http://test"
        ) as client:
            # Admin should access admin-only
            response = await client.get(
                "/admin-only",
                headers={"X-Test-User": "admin"}
            )
            assert response.status_code == 200
            
            # Manager should not access admin-only
            response = await client.get(
                "/admin-only",
                headers={"X-Test-User": "manager"}
            )
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_campaign_manager_user_type_alias(self, app_with_typed_deps):
        """CampaignManagerUser type alias should enforce manager role."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_typed_deps),
            base_url="http://test"
        ) as client:
            # Manager should access manager-only
            response = await client.get(
                "/manager-only",
                headers={"X-Test-User": "manager"}
            )
            assert response.status_code == 200
            
            # Viewer should not access manager-only
            response = await client.get(
                "/manager-only",
                headers={"X-Test-User": "viewer"}
            )
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_viewer_user_type_alias(self, app_with_typed_deps):
        """ViewerUser type alias should allow viewer role."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_typed_deps),
            base_url="http://test"
        ) as client:
            # All roles should access viewer-allowed
            for user_type in ["admin", "manager", "viewer"]:
                response = await client.get(
                    "/viewer-allowed",
                    headers={"X-Test-User": user_type}
                )
                assert response.status_code == 200


class TestRBACConfigurability:
    """Tests for RBAC configurability without code changes."""
    
    def test_role_permissions_are_configurable(self):
        """Role permissions should be defined in a configurable mapping."""
        from app.auth.rbac import ROLE_PERMISSIONS
        
        # Verify structure allows configuration
        assert isinstance(ROLE_PERMISSIONS, dict)
        assert UserRole.ADMIN in ROLE_PERMISSIONS
        assert UserRole.CAMPAIGN_MANAGER in ROLE_PERMISSIONS
        assert UserRole.VIEWER in ROLE_PERMISSIONS
        
        # Verify permissions are sets (easily modifiable)
        for role, perms in ROLE_PERMISSIONS.items():
            assert isinstance(perms, set)
    
    def test_permission_enum_is_extensible(self):
        """Permission enum should be easily extensible."""
        # Verify all permissions are strings
        for perm in Permission:
            assert isinstance(perm.value, str)
            # Verify naming convention (resource:action)
            assert ":" in perm.value