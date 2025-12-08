"""
Tests for RBAC authorization middleware.

Tests role extraction, permission checks, and access control enforcement.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.auth.rbac import (
    Permission,
    ROLE_PERMISSIONS,
    AccessDeniedLog,
    get_role_permissions,
    has_minimum_role,
    has_permission,
    log_access_denied,
    require_permission,
    require_role,
    AdminUser,
    CampaignManagerUser,
    ViewerUser,
    RBACMiddleware,
)
from app.auth.schemas import UserRole
from app.auth.middleware import CurrentUser


# Test fixtures
@pytest.fixture
def admin_user() -> CurrentUser:
    """Create admin user context."""
    return CurrentUser(
        id=uuid4(),
        oidc_sub="admin-sub-123",
        email="admin@test.com",
        name="Admin User",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def campaign_manager_user() -> CurrentUser:
    """Create campaign manager user context."""
    return CurrentUser(
        id=uuid4(),
        oidc_sub="manager-sub-123",
        email="manager@test.com",
        name="Campaign Manager",
        role=UserRole.CAMPAIGN_MANAGER,
    )


@pytest.fixture
def viewer_user() -> CurrentUser:
    """Create viewer user context."""
    return CurrentUser(
        id=uuid4(),
        oidc_sub="viewer-sub-123",
        email="viewer@test.com",
        name="Viewer User",
        role=UserRole.VIEWER,
    )


class TestRolePermissions:
    """Tests for role permission mappings."""
    
    def test_admin_has_all_permissions(self):
        """Admin role should have all defined permissions."""
        admin_perms = get_role_permissions(UserRole.ADMIN)
        # Admin should have all permissions
        assert Permission.CAMPAIGN_READ in admin_perms
        assert Permission.CAMPAIGN_CREATE in admin_perms
        assert Permission.CAMPAIGN_UPDATE in admin_perms
        assert Permission.CAMPAIGN_DELETE in admin_perms
        assert Permission.ADMIN_CONFIG_READ in admin_perms
        assert Permission.ADMIN_CONFIG_UPDATE in admin_perms
        assert Permission.ADMIN_EXCLUSION_MANAGE in admin_perms
    
    def test_campaign_manager_permissions(self):
        """Campaign manager should have campaign and contact permissions."""
        manager_perms = get_role_permissions(UserRole.CAMPAIGN_MANAGER)
        # Should have campaign permissions
        assert Permission.CAMPAIGN_READ in manager_perms
        assert Permission.CAMPAIGN_CREATE in manager_perms
        assert Permission.CAMPAIGN_UPDATE in manager_perms
        assert Permission.CAMPAIGN_DELETE in manager_perms
        # Should NOT have admin permissions
        assert Permission.ADMIN_CONFIG_READ not in manager_perms
        assert Permission.ADMIN_CONFIG_UPDATE not in manager_perms
        assert Permission.ADMIN_EXCLUSION_MANAGE not in manager_perms
    
    def test_viewer_read_only_permissions(self):
        """Viewer should only have read permissions."""
        viewer_perms = get_role_permissions(UserRole.VIEWER)
        # Should have read permissions
        assert Permission.CAMPAIGN_READ in viewer_perms
        assert Permission.CONTACT_READ in viewer_perms
        assert Permission.STATS_READ in viewer_perms
        # Should NOT have write permissions
        assert Permission.CAMPAIGN_CREATE not in viewer_perms
        assert Permission.CAMPAIGN_UPDATE not in viewer_perms
        assert Permission.CONTACT_UPLOAD not in viewer_perms
        assert Permission.CONTACT_EXPORT not in viewer_perms


class TestHasPermission:
    """Tests for has_permission function."""
    
    def test_admin_has_admin_permission(self):
        """Admin should have admin config permission."""
        assert has_permission(UserRole.ADMIN, Permission.ADMIN_CONFIG_UPDATE) is True
    
    def test_manager_lacks_admin_permission(self):
        """Campaign manager should not have admin config permission."""
        assert has_permission(UserRole.CAMPAIGN_MANAGER, Permission.ADMIN_CONFIG_UPDATE) is False
    
    def test_viewer_has_read_permission(self):
        """Viewer should have read permission."""
        assert has_permission(UserRole.VIEWER, Permission.CAMPAIGN_READ) is True
    
    def test_viewer_lacks_write_permission(self):
        """Viewer should not have write permission."""
        assert has_permission(UserRole.VIEWER, Permission.CAMPAIGN_CREATE) is False


class TestHasMinimumRole:
    """Tests for has_minimum_role function."""
    
    def test_admin_meets_admin_requirement(self):
        """Admin should meet admin requirement."""
        assert has_minimum_role(UserRole.ADMIN, UserRole.ADMIN) is True
    
    def test_admin_meets_manager_requirement(self):
        """Admin should meet campaign manager requirement."""
        assert has_minimum_role(UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER) is True
    
    def test_admin_meets_viewer_requirement(self):
        """Admin should meet viewer requirement."""
        assert has_minimum_role(UserRole.ADMIN, UserRole.VIEWER) is True
    
    def test_manager_meets_manager_requirement(self):
        """Campaign manager should meet campaign manager requirement."""
        assert has_minimum_role(UserRole.CAMPAIGN_MANAGER, UserRole.CAMPAIGN_MANAGER) is True
    
    def test_manager_meets_viewer_requirement(self):
        """Campaign manager should meet viewer requirement."""
        assert has_minimum_role(UserRole.CAMPAIGN_MANAGER, UserRole.VIEWER) is True
    
    def test_manager_fails_admin_requirement(self):
        """Campaign manager should not meet admin requirement."""
        assert has_minimum_role(UserRole.CAMPAIGN_MANAGER, UserRole.ADMIN) is False
    
    def test_viewer_meets_viewer_requirement(self):
        """Viewer should meet viewer requirement."""
        assert has_minimum_role(UserRole.VIEWER, UserRole.VIEWER) is True
    
    def test_viewer_fails_manager_requirement(self):
        """Viewer should not meet campaign manager requirement."""
        assert has_minimum_role(UserRole.VIEWER, UserRole.CAMPAIGN_MANAGER) is False
    
    def test_viewer_fails_admin_requirement(self):
        """Viewer should not meet admin requirement."""
        assert has_minimum_role(UserRole.VIEWER, UserRole.ADMIN) is False


class TestAccessDeniedLog:
    """Tests for AccessDeniedLog structure."""
    
    def test_log_creation(self):
        """Test access denied log creation."""
        log = AccessDeniedLog(
            user_id="user-123",
            user_role="viewer",
            endpoint="/api/admin/config",
            method="PUT",
            required_role="admin",
        )
        assert log.user_id == "user-123"
        assert log.user_role == "viewer"
        assert log.endpoint == "/api/admin/config"
        assert log.method == "PUT"
        assert log.required_role == "admin"
        assert log.timestamp is not None
    
    def test_log_to_dict(self):
        """Test access denied log serialization."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        log = AccessDeniedLog(
            user_id="user-123",
            user_role="viewer",
            endpoint="/api/admin/config",
            method="PUT",
            required_role="admin",
            timestamp=timestamp,
        )
        log_dict = log.to_dict()
        assert log_dict["event"] == "access_denied"
        assert log_dict["user_id"] == "user-123"
        assert log_dict["user_role"] == "viewer"
        assert log_dict["endpoint"] == "/api/admin/config"
        assert log_dict["method"] == "PUT"
        assert log_dict["required_role"] == "admin"
        assert log_dict["timestamp"] == "2025-01-15T12:00:00"


class TestLogAccessDenied:
    """Tests for log_access_denied function."""
    
    def test_log_access_denied_with_role(self):
        """Test logging access denied with role requirement."""
        request = MagicMock()
        request.url.path = "/api/admin/config"
        request.method = "PUT"
        
        with patch("app.auth.rbac.logger") as mock_logger:
            log_access_denied(
                request=request,
                user_id="user-123",
                user_role="viewer",
                required_role="admin",
            )
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "Access denied"
            assert call_args[1]["extra"]["user_id"] == "user-123"
    
    def test_log_access_denied_with_permission(self):
        """Test logging access denied with permission requirement."""
        request = MagicMock()
        request.url.path = "/api/campaigns"
        request.method = "POST"
        
        with patch("app.auth.rbac.logger") as mock_logger:
            log_access_denied(
                request=request,
                user_id="user-456",
                user_role="viewer",
                required_permission="campaign:create",
            )
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[1]["extra"]["required_permission"] == "campaign:create"


class TestRequireRoleDecorator:
    """Tests for require_role dependency factory."""
    
    @pytest.mark.asyncio
    async def test_admin_passes_admin_check(self, admin_user):
        """Admin should pass admin role check."""
        request = MagicMock()
        request.url.path = "/api/admin/config"
        request.method = "GET"
        
        checker = require_role(UserRole.ADMIN)
        result = await checker(request, admin_user)
        assert result == admin_user
    
    @pytest.mark.asyncio
    async def test_manager_fails_admin_check(self, campaign_manager_user):
        """Campaign manager should fail admin role check."""
        request = MagicMock()
        request.url.path = "/api/admin/config"
        request.method = "GET"
        
        checker = require_role(UserRole.ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            await checker(request, campaign_manager_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "admin" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_viewer_fails_manager_check(self, viewer_user):
        """Viewer should fail campaign manager role check."""
        request = MagicMock()
        request.url.path = "/api/campaigns"
        request.method = "POST"
        
        checker = require_role(UserRole.CAMPAIGN_MANAGER)
        with pytest.raises(HTTPException) as exc_info:
            await checker(request, viewer_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_manager_passes_viewer_check(self, campaign_manager_user):
        """Campaign manager should pass viewer role check."""
        request = MagicMock()
        request.url.path = "/api/campaigns"
        request.method = "GET"
        
        checker = require_role(UserRole.VIEWER)
        result = await checker(request, campaign_manager_user)
        assert result == campaign_manager_user


class TestRequirePermissionDecorator:
    """Tests for require_permission dependency factory."""
    
    @pytest.mark.asyncio
    async def test_admin_has_admin_permission(self, admin_user):
        """Admin should have admin config permission."""
        request = MagicMock()
        request.url.path = "/api/admin/config"
        request.method = "PUT"
        
        checker = require_permission(Permission.ADMIN_CONFIG_UPDATE)
        result = await checker(request, admin_user)
        assert result == admin_user
    
    @pytest.mark.asyncio
    async def test_manager_lacks_admin_permission(self, campaign_manager_user):
        """Campaign manager should lack admin config permission."""
        request = MagicMock()
        request.url.path = "/api/admin/config"
        request.method = "PUT"
        
        checker = require_permission(Permission.ADMIN_CONFIG_UPDATE)
        with pytest.raises(HTTPException) as exc_info:
            await checker(request, campaign_manager_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "admin:config:update" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_viewer_has_read_permission(self, viewer_user):
        """Viewer should have campaign read permission."""
        request = MagicMock()
        request.url.path = "/api/campaigns"
        request.method = "GET"
        
        checker = require_permission(Permission.CAMPAIGN_READ)
        result = await checker(request, viewer_user)
        assert result == viewer_user
    
    @pytest.mark.asyncio
    async def test_viewer_lacks_create_permission(self, viewer_user):
        """Viewer should lack campaign create permission."""
        request = MagicMock()
        request.url.path = "/api/campaigns"
        request.method = "POST"
        
        checker = require_permission(Permission.CAMPAIGN_CREATE)
        with pytest.raises(HTTPException) as exc_info:
            await checker(request, viewer_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestRBACMiddleware:
    """Tests for RBACMiddleware class."""
    
    @pytest.mark.asyncio
    async def test_middleware_allows_sufficient_role(self, admin_user):
        """Middleware should allow user with sufficient role."""
        request = MagicMock()
        request.url.path = "/api/admin/config"
        request.method = "GET"
        
        middleware = RBACMiddleware(UserRole.ADMIN)
        result = await middleware(request, admin_user)
        assert result == admin_user
    
    @pytest.mark.asyncio
    async def test_middleware_denies_insufficient_role(self, viewer_user):
        """Middleware should deny user with insufficient role."""
        request = MagicMock()
        request.url.path = "/api/admin/config"
        request.method = "GET"
        
        middleware = RBACMiddleware(UserRole.ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            await middleware(request, viewer_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestIntegrationWithFastAPI:
    """Integration tests with FastAPI application."""
    
    @pytest.fixture
    def test_app(self, admin_user, campaign_manager_user, viewer_user):
        """Create test FastAPI application with RBAC-protected routes."""
        app = FastAPI()
        
        # Mock user injection based on header
        async def get_mock_user(request: MagicMock) -> CurrentUser:
            user_type = request.headers.get("X-Test-User", "viewer")
            if user_type == "admin":
                return admin_user
            elif user_type == "manager":
                return campaign_manager_user
            return viewer_user
        
        @app.get("/api/admin/config")
        async def admin_config(user: CurrentUser = Depends(get_mock_user)):
            checker = require_role(UserRole.ADMIN)
            mock_request = MagicMock()
            mock_request.url.path = "/api/admin/config"
            mock_request.method = "GET"
            await checker(mock_request, user)
            return {"config": "admin_data"}
        
        @app.get("/api/campaigns")
        async def list_campaigns(user: CurrentUser = Depends(get_mock_user)):
            checker = require_role(UserRole.VIEWER)
            mock_request = MagicMock()
            mock_request.url.path = "/api/campaigns"
            mock_request.method = "GET"
            await checker(mock_request, user)
            return {"campaigns": []}
        
        @app.post("/api/campaigns")
        async def create_campaign(user: CurrentUser = Depends(get_mock_user)):
            checker = require_role(UserRole.CAMPAIGN_MANAGER)
            mock_request = MagicMock()
            mock_request.url.path = "/api/campaigns"
            mock_request.method = "POST"
            await checker(mock_request, user)
            return {"id": "new-campaign"}
        
        return app
    
    @pytest.mark.asyncio
    async def test_admin_endpoint_with_admin(self, test_app):
        """Admin should access admin endpoint."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/admin/config",
                headers={"X-Test-User": "admin"}
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_admin_endpoint_with_manager(self, test_app):
        """Campaign manager should be denied admin endpoint."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/admin/config",
                headers={"X-Test-User": "manager"}
            )
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_campaign_list_with_viewer(self, test_app):
        """Viewer should access campaign list."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/campaigns",
                headers={"X-Test-User": "viewer"}
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_campaign_create_with_viewer(self, test_app):
        """Viewer should be denied campaign creation."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/campaigns",
                headers={"X-Test-User": "viewer"}
            )
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_campaign_create_with_manager(self, test_app):
        """Campaign manager should create campaigns."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/campaigns",
                headers={"X-Test-User": "manager"}
            )
            assert response.status_code == 200


class TestAccessDeniedLogging:
    """Tests for access denied logging functionality."""
    
    @pytest.mark.asyncio
    async def test_denied_access_is_logged(self, viewer_user):
        """Denied access should be logged with user details."""
        request = MagicMock()
        request.url.path = "/api/admin/config"
        request.method = "PUT"
        
        with patch("app.auth.rbac.logger") as mock_logger:
            checker = require_role(UserRole.ADMIN)
            with pytest.raises(HTTPException):
                await checker(request, viewer_user)
            
            # Verify logging was called
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            extra = call_args[1]["extra"]
            
            assert extra["event"] == "access_denied"
            assert extra["user_id"] == str(viewer_user.id)
            assert extra["user_role"] == "viewer"
            assert extra["endpoint"] == "/api/admin/config"
            assert extra["method"] == "PUT"
            assert extra["required_role"] == "admin"
            assert "timestamp" in extra