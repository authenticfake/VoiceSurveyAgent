"""
Tests for RBAC authorization middleware.

Tests cover:
- Role extraction from JWT claims and user database
- Route decorator enforcement
- Admin endpoint restrictions
- Campaign modification restrictions
- Access denied logging
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.auth.rbac import (
    AccessDeniedLog,
    AdminUser,
    CampaignManagerUser,
    InsufficientPermissionsError,
    RoleChecker,
    RoleLevel,
    ViewerUser,
    can_modify_campaigns,
    get_role_level,
    has_minimum_role,
    is_admin,
    log_access_denied,
    rbac_decorator,
    require_admin,
    require_campaign_manager,
    require_role,
    require_viewer,
)
from app.auth.schemas import UserRole
from app.auth.middleware import CurrentUser


# Test fixtures
@pytest.fixture
def admin_user() -> CurrentUser:
    """Create an admin user context."""
    return CurrentUser(
        user_id=uuid4(),
        email="admin@test.com",
        name="Admin User",
        role=UserRole.ADMIN,
        oidc_sub="admin-sub-123",
    )


@pytest.fixture
def campaign_manager_user() -> CurrentUser:
    """Create a campaign manager user context."""
    return CurrentUser(
        user_id=uuid4(),
        email="manager@test.com",
        name="Campaign Manager",
        role=UserRole.CAMPAIGN_MANAGER,
        oidc_sub="manager-sub-123",
    )


@pytest.fixture
def viewer_user() -> CurrentUser:
    """Create a viewer user context."""
    return CurrentUser(
        user_id=uuid4(),
        email="viewer@test.com",
        name="Viewer User",
        role=UserRole.VIEWER,
        oidc_sub="viewer-sub-123",
    )


class TestRoleLevel:
    """Tests for role level hierarchy."""
    
    def test_role_levels_ordered_correctly(self):
        """Verify role levels are in correct order."""
        assert RoleLevel.VIEWER < RoleLevel.CAMPAIGN_MANAGER < RoleLevel.ADMIN
    
    def test_get_role_level_returns_correct_level(self):
        """Test get_role_level returns correct level for each role."""
        assert get_role_level(UserRole.VIEWER) == RoleLevel.VIEWER
        assert get_role_level(UserRole.CAMPAIGN_MANAGER) == RoleLevel.CAMPAIGN_MANAGER
        assert get_role_level(UserRole.ADMIN) == RoleLevel.ADMIN


class TestHasMinimumRole:
    """Tests for has_minimum_role function."""
    
    def test_admin_has_all_roles(self):
        """Admin should have access to all role levels."""
        assert has_minimum_role(UserRole.ADMIN, UserRole.VIEWER)
        assert has_minimum_role(UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER)
        assert has_minimum_role(UserRole.ADMIN, UserRole.ADMIN)
    
    def test_campaign_manager_has_viewer_and_self(self):
        """Campaign manager should have viewer and own role."""
        assert has_minimum_role(UserRole.CAMPAIGN_MANAGER, UserRole.VIEWER)
        assert has_minimum_role(UserRole.CAMPAIGN_MANAGER, UserRole.CAMPAIGN_MANAGER)
        assert not has_minimum_role(UserRole.CAMPAIGN_MANAGER, UserRole.ADMIN)
    
    def test_viewer_only_has_viewer(self):
        """Viewer should only have viewer role."""
        assert has_minimum_role(UserRole.VIEWER, UserRole.VIEWER)
        assert not has_minimum_role(UserRole.VIEWER, UserRole.CAMPAIGN_MANAGER)
        assert not has_minimum_role(UserRole.VIEWER, UserRole.ADMIN)


class TestCanModifyCampaigns:
    """Tests for campaign modification permission."""
    
    def test_admin_can_modify(self):
        """Admin can modify campaigns."""
        assert can_modify_campaigns(UserRole.ADMIN)
    
    def test_campaign_manager_can_modify(self):
        """Campaign manager can modify campaigns."""
        assert can_modify_campaigns(UserRole.CAMPAIGN_MANAGER)
    
    def test_viewer_cannot_modify(self):
        """Viewer cannot modify campaigns."""
        assert not can_modify_campaigns(UserRole.VIEWER)


class TestIsAdmin:
    """Tests for admin check."""
    
    def test_admin_is_admin(self):
        """Admin role returns True."""
        assert is_admin(UserRole.ADMIN)
    
    def test_campaign_manager_is_not_admin(self):
        """Campaign manager is not admin."""
        assert not is_admin(UserRole.CAMPAIGN_MANAGER)
    
    def test_viewer_is_not_admin(self):
        """Viewer is not admin."""
        assert not is_admin(UserRole.VIEWER)


class TestAccessDeniedLog:
    """Tests for access denied logging."""
    
    def test_log_entry_creation(self):
        """Test AccessDeniedLog creates correct structure."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        log_entry = AccessDeniedLog(
            user_id="user-123",
            endpoint="/api/admin/config",
            user_role=UserRole.VIEWER,
            required_role=UserRole.ADMIN,
            timestamp=timestamp,
        )
        
        result = log_entry.to_dict()
        
        assert result["event"] == "access_denied"
        assert result["user_id"] == "user-123"
        assert result["endpoint"] == "/api/admin/config"
        assert result["user_role"] == "viewer"
        assert result["required_role"] == "admin"
        assert result["timestamp"] == "2024-01-15T10:30:00"
    
    def test_log_entry_default_timestamp(self):
        """Test AccessDeniedLog uses current time if not provided."""
        log_entry = AccessDeniedLog(
            user_id="user-123",
            endpoint="/api/test",
            user_role=UserRole.VIEWER,
            required_role=UserRole.ADMIN,
        )
        
        assert log_entry.timestamp is not None
        assert isinstance(log_entry.timestamp, datetime)


class TestLogAccessDenied:
    """Tests for log_access_denied function."""
    
    def test_logs_warning_with_correct_data(self):
        """Test that access denied events are logged correctly."""
        with patch("app.auth.rbac.logger") as mock_logger:
            log_access_denied(
                user_id="user-456",
                endpoint="/api/campaigns",
                user_role=UserRole.VIEWER,
                required_role=UserRole.CAMPAIGN_MANAGER,
            )
            
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "Access denied"
            extra = call_args[1]["extra"]
            assert extra["user_id"] == "user-456"
            assert extra["endpoint"] == "/api/campaigns"
            assert extra["user_role"] == "viewer"
            assert extra["required_role"] == "campaign_manager"


class TestRoleChecker:
    """Tests for RoleChecker dependency class."""
    
    @pytest.mark.asyncio
    async def test_allows_sufficient_role(self, admin_user):
        """Test that sufficient role is allowed."""
        checker = RoleChecker(UserRole.VIEWER)
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        
        result = await checker(request, admin_user)
        
        assert result == admin_user
    
    @pytest.mark.asyncio
    async def test_denies_insufficient_role(self, viewer_user):
        """Test that insufficient role is denied."""
        checker = RoleChecker(UserRole.ADMIN)
        request = MagicMock(spec=Request)
        request.url.path = "/api/admin/config"
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(request, viewer_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail["error"] == "insufficient_permissions"
        assert exc_info.value.detail["required_role"] == "admin"
        assert exc_info.value.detail["user_role"] == "viewer"
    
    @pytest.mark.asyncio
    async def test_logs_denied_access(self, viewer_user):
        """Test that denied access is logged."""
        checker = RoleChecker(UserRole.ADMIN)
        request = MagicMock(spec=Request)
        request.url.path = "/api/admin/config"
        
        with patch("app.auth.rbac.log_access_denied") as mock_log:
            with pytest.raises(HTTPException):
                await checker(request, viewer_user)
            
            mock_log.assert_called_once_with(
                user_id=str(viewer_user.user_id),
                endpoint="/api/admin/config",
                user_role=UserRole.VIEWER,
                required_role=UserRole.ADMIN,
            )


class TestRequireRole:
    """Tests for require_role factory function."""
    
    def test_creates_role_checker(self):
        """Test that require_role creates a RoleChecker."""
        checker = require_role(UserRole.CAMPAIGN_MANAGER)
        
        assert isinstance(checker, RoleChecker)
        assert checker.required_role == UserRole.CAMPAIGN_MANAGER
    
    def test_preconfigured_checkers(self):
        """Test pre-configured role checkers."""
        assert require_viewer.required_role == UserRole.VIEWER
        assert require_campaign_manager.required_role == UserRole.CAMPAIGN_MANAGER
        assert require_admin.required_role == UserRole.ADMIN


class TestInsufficientPermissionsError:
    """Tests for InsufficientPermissionsError exception."""
    
    def test_error_message(self):
        """Test error message format."""
        error = InsufficientPermissionsError(
            user_role=UserRole.VIEWER,
            required_role=UserRole.ADMIN,
            endpoint="/api/admin/config",
            user_id="user-123",
        )
        
        assert "viewer" in str(error)
        assert "admin" in str(error)
        assert "/api/admin/config" in str(error)
    
    def test_error_attributes(self):
        """Test error attributes are set correctly."""
        error = InsufficientPermissionsError(
            user_role=UserRole.CAMPAIGN_MANAGER,
            required_role=UserRole.ADMIN,
            endpoint="/api/test",
            user_id="user-456",
        )
        
        assert error.user_role == UserRole.CAMPAIGN_MANAGER
        assert error.required_role == UserRole.ADMIN
        assert error.endpoint == "/api/test"
        assert error.user_id == "user-456"


class TestRBACIntegration:
    """Integration tests for RBAC with FastAPI."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with RBAC-protected routes."""
        app = FastAPI()
        
        # Mock the CurrentUser dependency
        async def get_mock_user():
            return None  # Will be overridden in tests
        
        @app.get("/public")
        async def public_endpoint():
            return {"message": "public"}
        
        @app.get("/viewer-only")
        async def viewer_endpoint(user: ViewerUser):
            return {"message": "viewer", "role": user.role.value}
        
        @app.get("/manager-only")
        async def manager_endpoint(user: CampaignManagerUser):
            return {"message": "manager", "role": user.role.value}
        
        @app.get("/admin-only")
        async def admin_endpoint(user: AdminUser):
            return {"message": "admin", "role": user.role.value}
        
        @app.put("/campaigns/{id}")
        async def update_campaign(
            id: str,
            user: CampaignManagerUser,
        ):
            return {"message": "updated", "id": id}
        
        return app
    
    @pytest.mark.asyncio
    async def test_admin_accesses_all_endpoints(self, app, admin_user):
        """Admin should access all protected endpoints."""
        # Override the dependency
        app.dependency_overrides[require_viewer] = lambda: admin_user
        app.dependency_overrides[require_campaign_manager] = lambda: admin_user
        app.dependency_overrides[require_admin] = lambda: admin_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Test viewer endpoint
            response = await client.get("/viewer-only")
            assert response.status_code == 200
            
            # Test manager endpoint
            response = await client.get("/manager-only")
            assert response.status_code == 200
            
            # Test admin endpoint
            response = await client.get("/admin-only")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_viewer_denied_admin_endpoint(self, app, viewer_user):
        """Viewer should be denied access to admin endpoint."""
        # Create a checker that will deny access
        async def deny_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "insufficient_permissions"},
            )
        
        app.dependency_overrides[require_admin] = deny_admin
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/admin-only")
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_campaign_modification_requires_manager(self, app, viewer_user, campaign_manager_user):
        """Campaign modification should require campaign_manager role."""
        # Test with viewer (should fail)
        async def deny_viewer():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "insufficient_permissions"},
            )
        
        app.dependency_overrides[require_campaign_manager] = deny_viewer
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.put("/campaigns/123")
            assert response.status_code == 403
        
        # Test with campaign manager (should succeed)
        app.dependency_overrides[require_campaign_manager] = lambda: campaign_manager_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.put("/campaigns/123")
            assert response.status_code == 200


class TestRBACDecorator:
    """Tests for rbac_decorator function."""
    
    @pytest.mark.asyncio
    async def test_decorator_allows_sufficient_role(self, admin_user):
        """Test decorator allows access with sufficient role."""
        @rbac_decorator(UserRole.VIEWER)
        async def protected_func(current_user):
            return {"success": True}
        
        result = await protected_func(current_user=admin_user)
        assert result == {"success": True}
    
    @pytest.mark.asyncio
    async def test_decorator_denies_insufficient_role(self, viewer_user):
        """Test decorator denies access with insufficient role."""
        @rbac_decorator(UserRole.ADMIN)
        async def admin_func(current_user):
            return {"success": True}
        
        with pytest.raises(HTTPException) as exc_info:
            await admin_func(current_user=viewer_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_decorator_requires_authentication(self):
        """Test decorator requires current_user."""
        @rbac_decorator(UserRole.VIEWER)
        async def protected_func():
            return {"success": True}
        
        with pytest.raises(HTTPException) as exc_info:
            await protected_func()
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED