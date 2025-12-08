"""
Unit tests for RBAC permission decorators and utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends

from app.auth.rbac.roles import Role
from app.auth.rbac.permissions import (
    get_current_user_role,
    require_role,
    require_any_role,
    require_permission,
)


class MockUser:
    """Mock user for testing."""
    def __init__(self, user_id: str, role: str):
        self.id = user_id
        self.role = role


def create_mock_request(user=None, jwt_claims=None):
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    request.state.user = user
    request.state.jwt_claims = jwt_claims
    request.method = "GET"
    request.url = MagicMock()
    request.url.path = "/test/endpoint"
    request.headers = {}
    request.query_params = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    return request


class TestGetCurrentUserRole:
    """Tests for get_current_user_role dependency."""
    
    @pytest.mark.asyncio
    async def test_no_user_raises_401(self):
        """Test that missing user raises 401."""
        request = create_mock_request(user=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_role(request)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_role_from_jwt_claims(self):
        """Test role extraction from JWT claims."""
        user = MockUser("user-123", "viewer")
        jwt_claims = {"role": "admin"}
        request = create_mock_request(user=user, jwt_claims=jwt_claims)
        
        role = await get_current_user_role(request)
        
        assert role == Role.ADMIN
    
    @pytest.mark.asyncio
    async def test_role_from_user_record(self):
        """Test role extraction from user record."""
        user = MockUser("user-123", "campaign_manager")
        request = create_mock_request(user=user, jwt_claims=None)
        
        role = await get_current_user_role(request)
        
        assert role == Role.CAMPAIGN_MANAGER
    
    @pytest.mark.asyncio
    async def test_role_enum_from_user(self):
        """Test when user.role is already a Role enum."""
        user = MockUser("user-123", Role.VIEWER)
        request = create_mock_request(user=user, jwt_claims=None)
        
        role = await get_current_user_role(request)
        
        assert role == Role.VIEWER
    
    @pytest.mark.asyncio
    async def test_invalid_role_raises_403(self):
        """Test that invalid role raises 403."""
        user = MockUser("user-123", "invalid_role")
        request = create_mock_request(user=user, jwt_claims=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_role(request)
        
        assert exc_info.value.status_code == 403
        assert "Invalid role" in exc_info.value.detail


class TestRequireRole:
    """Tests for require_role dependency."""
    
    @pytest.mark.asyncio
    async def test_admin_access_admin_endpoint(self):
        """Test admin can access admin-only endpoint."""
        user = MockUser("user-123", "admin")
        request = create_mock_request(user=user)
        
        checker = require_role(Role.ADMIN, log_denial=False)
        role = await checker(request, Role.ADMIN)
        
        assert role == Role.ADMIN
    
    @pytest.mark.asyncio
    async def test_viewer_denied_admin_endpoint(self):
        """Test viewer is denied access to admin endpoint."""
        user = MockUser("user-123", "viewer")
        request = create_mock_request(user=user)
        
        checker = require_role(Role.ADMIN, log_denial=False)
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(request, Role.VIEWER)
        
        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_campaign_manager_access_viewer_endpoint(self):
        """Test campaign_manager can access viewer endpoint."""
        user = MockUser("user-123", "campaign_manager")
        request = create_mock_request(user=user)
        
        checker = require_role(Role.VIEWER, log_denial=False)
        role = await checker(request, Role.CAMPAIGN_MANAGER)
        
        assert role == Role.CAMPAIGN_MANAGER
    
    @pytest.mark.asyncio
    @patch("app.auth.rbac.permissions.log_access_denied")
    async def test_denial_is_logged(self, mock_log):
        """Test that access denial is logged."""
        mock_log.return_value = None
        user = MockUser("user-123", "viewer")
        request = create_mock_request(user=user)
        
        checker = require_role(Role.ADMIN, log_denial=True)
        
        with pytest.raises(HTTPException):
            await checker(request, Role.VIEWER)
        
        mock_log.assert_called_once()
        call_args = mock_log.call_args
        assert call_args.kwargs["user_id"] == "user-123"
        assert call_args.kwargs["required_role"] == "admin"
        assert call_args.kwargs["user_role"] == "viewer"


class TestRequireAnyRole:
    """Tests for require_any_role dependency."""
    
    @pytest.mark.asyncio
    async def test_admin_in_allowed_roles(self):
        """Test admin access when admin is in allowed roles."""
        user = MockUser("user-123", "admin")
        request = create_mock_request(user=user)
        
        checker = require_any_role([Role.ADMIN, Role.CAMPAIGN_MANAGER], log_denial=False)
        role = await checker(request, Role.ADMIN)
        
        assert role == Role.ADMIN
    
    @pytest.mark.asyncio
    async def test_viewer_not_in_allowed_roles(self):
        """Test viewer denied when not in allowed roles."""
        user = MockUser("user-123", "viewer")
        request = create_mock_request(user=user)
        
        checker = require_any_role([Role.ADMIN, Role.CAMPAIGN_MANAGER], log_denial=False)
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(request, Role.VIEWER)
        
        assert exc_info.value.status_code == 403


class TestRequirePermission:
    """Tests for require_permission dependency."""
    
    @pytest.mark.asyncio
    async def test_admin_has_config_permission(self):
        """Test admin has config:update permission."""
        user = MockUser("user-123", "admin")
        request = create_mock_request(user=user)
        
        checker = require_permission("config:update", log_denial=False)
        role = await checker(request, Role.ADMIN)
        
        assert role == Role.ADMIN
    
    @pytest.mark.asyncio
    async def test_viewer_lacks_create_permission(self):
        """Test viewer lacks campaigns:create permission."""
        user = MockUser("user-123", "viewer")
        request = create_mock_request(user=user)
        
        checker = require_permission("campaigns:create", log_denial=False)
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(request, Role.VIEWER)
        
        assert exc_info.value.status_code == 403
        assert "campaigns:create" in exc_info.value.detail