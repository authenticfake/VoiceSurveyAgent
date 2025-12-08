"""
Integration tests for RBAC with FastAPI application.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import httpx

from app.auth.rbac.roles import Role
from app.auth.rbac.permissions import (
    require_role,
    require_any_role,
    require_permission,
    get_current_user_role,
)


class MockUser:
    """Mock user for testing."""
    def __init__(self, user_id: str, role: str):
        self.id = user_id
        self.role = role


def create_test_app():
    """Create a test FastAPI application with RBAC-protected routes."""
    app = FastAPI()
    
    @app.get("/public")
    async def public_endpoint():
        return {"message": "public"}
    
    @app.get("/admin-only")
    async def admin_only(role: Role = Depends(require_role(Role.ADMIN, log_denial=False))):
        return {"message": "admin", "role": role.value}
    
    @app.get("/manager-or-admin")
    async def manager_or_admin(
        role: Role = Depends(require_any_role([Role.ADMIN, Role.CAMPAIGN_MANAGER], log_denial=False))
    ):
        return {"message": "manager_or_admin", "role": role.value}
    
    @app.get("/viewer-minimum")
    async def viewer_minimum(role: Role = Depends(require_role(Role.VIEWER, log_denial=False))):
        return {"message": "viewer_minimum", "role": role.value}
    
    @app.post("/campaigns")
    async def create_campaign(
        role: Role = Depends(require_permission("campaigns:create", log_denial=False))
    ):
        return {"message": "campaign_created", "role": role.value}
    
    @app.middleware("http")
    async def mock_auth_middleware(request, call_next):
        # Simulate auth middleware setting user based on header
        role_header = request.headers.get("x-test-role")
        if role_header:
            request.state.user = MockUser("test-user", role_header)
            request.state.jwt_claims = {"role": role_header}
        else:
            request.state.user = None
            request.state.jwt_claims = None
        return await call_next(request)
    
    return app


@pytest.fixture
def test_app():
    """Fixture for test application."""
    return create_test_app()


@pytest.fixture
def client(test_app):
    """Fixture for test client."""
    return TestClient(test_app)


class TestRBACIntegration:
    """Integration tests for RBAC with FastAPI."""
    
    def test_public_endpoint_no_auth(self, client):
        """Test public endpoint accessible without auth."""
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json()["message"] == "public"
    
    def test_admin_endpoint_with_admin_role(self, client):
        """Test admin endpoint accessible with admin role."""
        response = client.get("/admin-only", headers={"x-test-role": "admin"})
        assert response.status_code == 200
        assert response.json()["role"] == "admin"
    
    def test_admin_endpoint_with_viewer_role(self, client):
        """Test admin endpoint denied with viewer role."""
        response = client.get("/admin-only", headers={"x-test-role": "viewer"})
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()
    
    def test_admin_endpoint_no_auth(self, client):
        """Test admin endpoint denied without auth."""
        response = client.get("/admin-only")
        assert response.status_code == 401
    
    def test_manager_or_admin_with_admin(self, client):
        """Test manager_or_admin endpoint with admin role."""
        response = client.get("/manager-or-admin", headers={"x-test-role": "admin"})
        assert response.status_code == 200
        assert response.json()["role"] == "admin"
    
    def test_manager_or_admin_with_manager(self, client):
        """Test manager_or_admin endpoint with campaign_manager role."""
        response = client.get("/manager-or-admin", headers={"x-test-role": "campaign_manager"})
        assert response.status_code == 200
        assert response.json()["role"] == "campaign_manager"
    
    def test_manager_or_admin_with_viewer(self, client):
        """Test manager_or_admin endpoint denied with viewer role."""
        response = client.get("/manager-or-admin", headers={"x-test-role": "viewer"})
        assert response.status_code == 403
    
    def test_viewer_minimum_with_admin(self, client):
        """Test viewer_minimum endpoint with admin role (hierarchy)."""
        response = client.get("/viewer-minimum", headers={"x-test-role": "admin"})
        assert response.status_code == 200
        assert response.json()["role"] == "admin"
    
    def test_viewer_minimum_with_viewer(self, client):
        """Test viewer_minimum endpoint with viewer role."""
        response = client.get("/viewer-minimum", headers={"x-test-role": "viewer"})
        assert response.status_code == 200
        assert response.json()["role"] == "viewer"
    
    def test_permission_based_access_admin(self, client):
        """Test permission-based access with admin role."""
        response = client.post("/campaigns", headers={"x-test-role": "admin"})
        assert response.status_code == 200
        assert response.json()["message"] == "campaign_created"
    
    def test_permission_based_access_manager(self, client):
        """Test permission-based access with campaign_manager role."""
        response = client.post("/campaigns", headers={"x-test-role": "campaign_manager"})
        assert response.status_code == 200
        assert response.json()["message"] == "campaign_created"
    
    def test_permission_based_access_viewer_denied(self, client):
        """Test permission-based access denied for viewer."""
        response = client.post("/campaigns", headers={"x-test-role": "viewer"})
        assert response.status_code == 403
        assert "campaigns:create" in response.json()["detail"]