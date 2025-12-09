"""
Tests for RBAC authorization middleware.

REQ-003: RBAC authorization middleware
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import jwt
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.auth.rbac import (
    Role,
    RBACChecker,
    RolePermissions,
    check_role_permission,
    log_access_denied,
    require_admin,
    require_campaign_manager,
    require_viewer,
    require_role,
)
from app.auth.middleware import CurrentUser, get_current_user
from app.config import Settings


# Test fixtures
@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        jwt_secret_key="test-secret-key-for-testing-purposes-only",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=30,
        jwt_refresh_token_expire_days=7,
        oidc_client_id="test-client",
        oidc_client_secret="test-secret",
        oidc_issuer_url="https://test-idp.example.com",
        oidc_redirect_uri="http://localhost:8000/api/auth/callback",
    )


@pytest.fixture
def admin_user() -> CurrentUser:
    """Create admin user fixture."""
    return CurrentUser(
        id=uuid4(),
        oidc_sub="oidc|admin001",
        email="admin@example.com",
        name="Admin User",
        role="admin",
    )


@pytest.fixture
def campaign_manager_user() -> CurrentUser:
    """Create campaign manager user fixture."""
    return CurrentUser(
        id=uuid4(),
        oidc_sub="oidc|manager001",
        email="manager@example.com",
        name="Campaign Manager",
        role="campaign_manager",
    )


@pytest.fixture
def viewer_user() -> CurrentUser:
    """Create viewer user fixture."""
    return CurrentUser(
        id=uuid4(),
        oidc_sub="oidc|viewer001",
        email="viewer@example.com",
        name="Viewer User",
        role="viewer",
    )


def create_test_token(
    user: CurrentUser,
    settings: Settings,
    expired: bool = False,
) -> str:
    """Create a test JWT token."""
    now = datetime.now(timezone.utc)
    if expired:
        exp = now - timedelta(hours=1)
    else:
        exp = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": user.oidc_sub,
        "user_id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "type": "access",
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


class TestRoleEnum:
    """Tests for Role enum."""

    def test_role_from_string_valid(self):
        """Test converting valid strings to Role enum."""
        assert Role.from_string("admin") == Role.ADMIN
        assert Role.from_string("campaign_manager") == Role.CAMPAIGN_MANAGER
        assert Role.from_string("viewer") == Role.VIEWER

    def test_role_from_string_invalid(self):
        """Test converting invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            Role.from_string("invalid_role")

    def test_role_hierarchy_admin(self):
        """Test admin has permission for all roles."""
        assert Role.ADMIN.has_permission(Role.ADMIN) is True
        assert Role.ADMIN.has_permission(Role.CAMPAIGN_MANAGER) is True
        assert Role.ADMIN.has_permission(Role.VIEWER) is True

    def test_role_hierarchy_campaign_manager(self):
        """Test campaign_manager has permission for manager and viewer."""
        assert Role.CAMPAIGN_MANAGER.has_permission(Role.ADMIN) is False
        assert Role.CAMPAIGN_MANAGER.has_permission(Role.CAMPAIGN_MANAGER) is True
        assert Role.CAMPAIGN_MANAGER.has_permission(Role.VIEWER) is True

    def test_role_hierarchy_viewer(self):
        """Test viewer only has permission for viewer."""
        assert Role.VIEWER.has_permission(Role.ADMIN) is False
        assert Role.VIEWER.has_permission(Role.CAMPAIGN_MANAGER) is False
        assert Role.VIEWER.has_permission(Role.VIEWER) is True


class TestCheckRolePermission:
    """Tests for check_role_permission function."""

    def test_admin_has_all_permissions(self):
        """Test admin role has all permissions."""
        assert check_role_permission("admin", Role.ADMIN) is True
        assert check_role_permission("admin", Role.CAMPAIGN_MANAGER) is True
        assert check_role_permission("admin", Role.VIEWER) is True

    def test_campaign_manager_permissions(self):
        """Test campaign_manager role permissions."""
        assert check_role_permission("campaign_manager", Role.ADMIN) is False
        assert check_role_permission("campaign_manager", Role.CAMPAIGN_MANAGER) is True
        assert check_role_permission("campaign_manager", Role.VIEWER) is True

    def test_viewer_permissions(self):
        """Test viewer role permissions."""
        assert check_role_permission("viewer", Role.ADMIN) is False
        assert check_role_permission("viewer", Role.CAMPAIGN_MANAGER) is False
        assert check_role_permission("viewer", Role.VIEWER) is True

    def test_invalid_role_returns_false(self):
        """Test invalid role returns False."""
        assert check_role_permission("invalid", Role.VIEWER) is False


class TestRolePermissions:
    """Tests for RolePermissions configuration."""

    def test_campaign_create_permissions(self):
        """Test campaign create permissions."""
        assert RolePermissions.can_perform("admin", RolePermissions.CAMPAIGN_CREATE)
        assert RolePermissions.can_perform("campaign_manager", RolePermissions.CAMPAIGN_CREATE)
        assert not RolePermissions.can_perform("viewer", RolePermissions.CAMPAIGN_CREATE)

    def test_campaign_read_permissions(self):
        """Test campaign read permissions."""
        assert RolePermissions.can_perform("admin", RolePermissions.CAMPAIGN_READ)
        assert RolePermissions.can_perform("campaign_manager", RolePermissions.CAMPAIGN_READ)
        assert RolePermissions.can_perform("viewer", RolePermissions.CAMPAIGN_READ)

    def test_admin_config_permissions(self):
        """Test admin config permissions."""
        assert RolePermissions.can_perform("admin", RolePermissions.ADMIN_CONFIG_READ)
        assert not RolePermissions.can_perform("campaign_manager", RolePermissions.ADMIN_CONFIG_READ)
        assert not RolePermissions.can_perform("viewer", RolePermissions.ADMIN_CONFIG_READ)

    def test_export_permissions(self):
        """Test export permissions."""
        assert RolePermissions.can_perform("admin", RolePermissions.EXPORT_DATA)
        assert RolePermissions.can_perform("campaign_manager", RolePermissions.EXPORT_DATA)
        assert not RolePermissions.can_perform("viewer", RolePermissions.EXPORT_DATA)


class TestLogAccessDenied:
    """Tests for log_access_denied function."""

    def test_log_access_denied_logs_warning(self):
        """Test that access denied events are logged."""
        with patch("app.auth.rbac.logger") as mock_logger:
            log_access_denied(
                user_id="test-user-id",
                user_email="test@example.com",
                user_role="viewer",
                endpoint="/api/admin/config",
                method="GET",
                required_role="admin",
                client_ip="192.168.1.1",
            )

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "Access denied"
            extra = call_args[1]["extra"]
            assert extra["user_id"] == "test-user-id"
            assert extra["user_email"] == "test@example.com"
            assert extra["user_role"] == "viewer"
            assert extra["required_role"] == "admin"
            assert extra["endpoint"] == "/api/admin/config"
            assert extra["method"] == "GET"
            assert extra["client_ip"] == "192.168.1.1"
            assert extra["event_type"] == "access_denied"


@pytest.fixture
def test_app(settings: Settings) -> FastAPI:
    """Create test FastAPI application with RBAC-protected endpoints."""
    app = FastAPI()

    @app.get("/admin-only")
    async def admin_endpoint(
        user: CurrentUser = Depends(require_admin),
    ):
        return {"message": "Admin access", "user": user.email}

    @app.get("/manager-only")
    async def manager_endpoint(
        user: CurrentUser = Depends(require_campaign_manager),
    ):
        return {"message": "Manager access", "user": user.email}

    @app.get("/viewer-only")
    async def viewer_endpoint(
        user: CurrentUser = Depends(require_viewer),
    ):
        return {"message": "Viewer access", "user": user.email}

    @app.get("/custom-role")
    async def custom_role_endpoint(
        user: CurrentUser = Depends(require_role(Role.CAMPAIGN_MANAGER)),
    ):
        return {"message": "Custom role access", "user": user.email}

    return app


@pytest.mark.asyncio
class TestRBACCheckerIntegration:
    """Integration tests for RBAC checker with FastAPI."""

    async def test_admin_can_access_admin_endpoint(
        self,
        test_app: FastAPI,
        admin_user: CurrentUser,
        settings: Settings,
    ):
        """Test admin can access admin-only endpoint."""
        token = create_test_token(admin_user, settings)

        # Override the get_current_user dependency
        async def override_get_current_user():
            return admin_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                "/admin-only",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Admin access"

        # Clean up
        test_app.dependency_overrides.clear()

    async def test_campaign_manager_cannot_access_admin_endpoint(
        self,
        test_app: FastAPI,
        campaign_manager_user: CurrentUser,
        settings: Settings,
    ):
        """Test campaign manager cannot access admin-only endpoint."""
        token = create_test_token(campaign_manager_user, settings)

        async def override_get_current_user():
            return campaign_manager_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                "/admin-only",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        detail = response.json()["detail"]
        assert detail["code"] == "INSUFFICIENT_PERMISSIONS"
        assert detail["required_role"] == "admin"
        assert detail["current_role"] == "campaign_manager"

        test_app.dependency_overrides.clear()

    async def test_viewer_cannot_access_admin_endpoint(
        self,
        test_app: FastAPI,
        viewer_user: CurrentUser,
        settings: Settings,
    ):
        """Test viewer cannot access admin-only endpoint."""
        token = create_test_token(viewer_user, settings)

        async def override_get_current_user():
            return viewer_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                "/admin-only",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

        test_app.dependency_overrides.clear()

    async def test_campaign_manager_can_access_manager_endpoint(
        self,
        test_app: FastAPI,
        campaign_manager_user: CurrentUser,
        settings: Settings,
    ):
        """Test campaign manager can access manager endpoint."""
        token = create_test_token(campaign_manager_user, settings)

        async def override_get_current_user():
            return campaign_manager_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                "/manager-only",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Manager access"

        test_app.dependency_overrides.clear()

    async def test_admin_can_access_manager_endpoint(
        self,
        test_app: FastAPI,
        admin_user: CurrentUser,
        settings: Settings,
    ):
        """Test admin can access manager endpoint (hierarchy)."""
        token = create_test_token(admin_user, settings)

        async def override_get_current_user():
            return admin_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                "/manager-only",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_200_OK

        test_app.dependency_overrides.clear()

    async def test_viewer_cannot_access_manager_endpoint(
        self,
        test_app: FastAPI,
        viewer_user: CurrentUser,
        settings: Settings,
    ):
        """Test viewer cannot access manager endpoint."""
        token = create_test_token(viewer_user, settings)

        async def override_get_current_user():
            return viewer_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                "/manager-only",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

        test_app.dependency_overrides.clear()

    async def test_all_roles_can_access_viewer_endpoint(
        self,
        test_app: FastAPI,
        admin_user: CurrentUser,
        campaign_manager_user: CurrentUser,
        viewer_user: CurrentUser,
        settings: Settings,
    ):
        """Test all roles can access viewer endpoint."""
        for user in [admin_user, campaign_manager_user, viewer_user]:
            token = create_test_token(user, settings)

            async def override_get_current_user(u=user):
                return u

            test_app.dependency_overrides[get_current_user] = override_get_current_user

            async with AsyncClient(
                transport=ASGITransport(app=test_app),
                base_url="http://localhost:8080",
            ) as client:
                response = await client.get(
                    "/viewer-only",
                    headers={"Authorization": f"Bearer {token}"},
                )

            assert response.status_code == status.HTTP_200_OK, f"Failed for role: {user.role}"

            test_app.dependency_overrides.clear()

    async def test_custom_role_requirement(
        self,
        test_app: FastAPI,
        campaign_manager_user: CurrentUser,
        viewer_user: CurrentUser,
        settings: Settings,
    ):
        """Test custom role requirement with require_role function."""
        # Campaign manager should have access
        async def override_manager():
            return campaign_manager_user

        test_app.dependency_overrides[get_current_user] = override_manager

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                "/custom-role",
                headers={"Authorization": f"Bearer {create_test_token(campaign_manager_user, settings)}"},
            )

        assert response.status_code == status.HTTP_200_OK

        # Viewer should not have access
        async def override_viewer():
            return viewer_user

        test_app.dependency_overrides[get_current_user] = override_viewer

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://localhost:8080",
        ) as client:
            response = await client.get(
                "/custom-role",
                headers={"Authorization": f"Bearer {create_test_token(viewer_user, settings)}"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

        test_app.dependency_overrides.clear()


class TestRBACCheckerUnit:
    """Unit tests for RBACChecker class."""

    def test_rbac_checker_initialization(self):
        """Test RBACChecker initializes with correct role."""
        checker = RBACChecker(Role.ADMIN)
        assert checker.minimum_role == Role.ADMIN

    @pytest.mark.asyncio
    async def test_rbac_checker_grants_access_for_sufficient_role(
        self,
        admin_user: CurrentUser,
    ):
        """Test RBACChecker grants access for sufficient role."""
        checker = RBACChecker(Role.CAMPAIGN_MANAGER)
        request = MagicMock()
        request.url.path = "/test"
        request.method = "GET"
        request.client.host = "127.0.0.1"

        result = await checker(request, admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_rbac_checker_denies_access_for_insufficient_role(
        self,
        viewer_user: CurrentUser,
    ):
        """Test RBACChecker denies access for insufficient role."""
        checker = RBACChecker(Role.ADMIN)
        request = MagicMock()
        request.url.path = "/admin"
        request.method = "GET"
        request.client.host = "127.0.0.1"

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await checker(request, viewer_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail["code"] == "INSUFFICIENT_PERMISSIONS"


class TestRequireRoleFactory:
    """Tests for require_role factory function."""

    def test_require_role_returns_rbac_checker(self):
        """Test require_role returns RBACChecker instance."""
        checker = require_role(Role.ADMIN)
        assert isinstance(checker, RBACChecker)
        assert checker.minimum_role == Role.ADMIN

    def test_pre_configured_checkers(self):
        """Test pre-configured checker instances."""
        assert require_admin.minimum_role == Role.ADMIN
        assert require_campaign_manager.minimum_role == Role.CAMPAIGN_MANAGER
        assert require_viewer.minimum_role == Role.VIEWER