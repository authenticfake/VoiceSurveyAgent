"""
Tests for RBAC authorization middleware.

Tests role extraction, permission checking, and route protection.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.auth.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    RBACChecker,
    get_role_permissions,
    has_all_permissions,
    has_any_permission,
    has_permission,
    rbac_required,
    require_admin,
    require_all_permissions,
    require_any_permission,
    require_campaign_manager,
    require_permission,
    require_viewer,
)
from app.auth.schemas import UserRole


class MockUser:
    """Mock user for testing."""

    def __init__(self, role: UserRole, user_id: uuid.UUID | None = None) -> None:
        self.id = user_id or uuid.uuid4()
        self.role = role
        self.email = f"{role.value}@test.com"
        self.name = f"Test {role.value}"


class TestRolePermissions:
    """Tests for role-permission mapping."""

    def test_admin_has_all_permissions(self) -> None:
        """Admin role should have all defined permissions."""
        admin_perms = get_role_permissions(UserRole.ADMIN)
        all_perms = set(Permission)
        assert admin_perms == all_perms

    def test_campaign_manager_permissions(self) -> None:
        """Campaign manager should have campaign and contact permissions."""
        perms = get_role_permissions(UserRole.CAMPAIGN_MANAGER)

        # Should have
        assert Permission.CAMPAIGN_CREATE in perms
        assert Permission.CAMPAIGN_READ in perms
        assert Permission.CAMPAIGN_UPDATE in perms
        assert Permission.CAMPAIGN_DELETE in perms
        assert Permission.CAMPAIGN_ACTIVATE in perms
        assert Permission.CONTACT_READ in perms
        assert Permission.CONTACT_UPLOAD in perms
        assert Permission.CONTACT_EXPORT in perms
        assert Permission.EXCLUSION_READ in perms
        assert Permission.STATS_READ in perms
        assert Permission.STATS_EXPORT in perms

        # Should NOT have
        assert Permission.ADMIN_CONFIG_READ not in perms
        assert Permission.ADMIN_CONFIG_WRITE not in perms
        assert Permission.EXCLUSION_MANAGE not in perms

    def test_viewer_permissions(self) -> None:
        """Viewer should have read-only permissions."""
        perms = get_role_permissions(UserRole.VIEWER)

        # Should have
        assert Permission.CAMPAIGN_READ in perms
        assert Permission.CONTACT_READ in perms
        assert Permission.STATS_READ in perms

        # Should NOT have
        assert Permission.CAMPAIGN_CREATE not in perms
        assert Permission.CAMPAIGN_UPDATE not in perms
        assert Permission.CAMPAIGN_DELETE not in perms
        assert Permission.CONTACT_UPLOAD not in perms
        assert Permission.ADMIN_CONFIG_READ not in perms


class TestPermissionChecks:
    """Tests for permission checking functions."""

    def test_has_permission_true(self) -> None:
        """has_permission returns True when role has permission."""
        assert has_permission(UserRole.ADMIN, Permission.ADMIN_CONFIG_WRITE)
        assert has_permission(UserRole.CAMPAIGN_MANAGER, Permission.CAMPAIGN_CREATE)
        assert has_permission(UserRole.VIEWER, Permission.CAMPAIGN_READ)

    def test_has_permission_false(self) -> None:
        """has_permission returns False when role lacks permission."""
        assert not has_permission(UserRole.VIEWER, Permission.CAMPAIGN_CREATE)
        assert not has_permission(UserRole.CAMPAIGN_MANAGER, Permission.ADMIN_CONFIG_WRITE)

    def test_has_any_permission_true(self) -> None:
        """has_any_permission returns True when role has at least one."""
        perms = {Permission.CAMPAIGN_CREATE, Permission.ADMIN_CONFIG_WRITE}
        assert has_any_permission(UserRole.ADMIN, perms)
        assert has_any_permission(UserRole.CAMPAIGN_MANAGER, perms)

    def test_has_any_permission_false(self) -> None:
        """has_any_permission returns False when role has none."""
        perms = {Permission.ADMIN_CONFIG_READ, Permission.ADMIN_CONFIG_WRITE}
        assert not has_any_permission(UserRole.VIEWER, perms)

    def test_has_all_permissions_true(self) -> None:
        """has_all_permissions returns True when role has all."""
        perms = {Permission.CAMPAIGN_READ, Permission.CONTACT_READ}
        assert has_all_permissions(UserRole.ADMIN, perms)
        assert has_all_permissions(UserRole.CAMPAIGN_MANAGER, perms)
        assert has_all_permissions(UserRole.VIEWER, perms)

    def test_has_all_permissions_false(self) -> None:
        """has_all_permissions returns False when role lacks any."""
        perms = {Permission.CAMPAIGN_READ, Permission.ADMIN_CONFIG_WRITE}
        assert not has_all_permissions(UserRole.VIEWER, perms)
        assert not has_all_permissions(UserRole.CAMPAIGN_MANAGER, perms)


class TestRBACChecker:
    """Tests for RBACChecker dependency."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test FastAPI app."""
        return FastAPI()

    @pytest.fixture
    def admin_user(self) -> MockUser:
        """Create admin user."""
        return MockUser(UserRole.ADMIN)

    @pytest.fixture
    def manager_user(self) -> MockUser:
        """Create campaign manager user."""
        return MockUser(UserRole.CAMPAIGN_MANAGER)

    @pytest.fixture
    def viewer_user(self) -> MockUser:
        """Create viewer user."""
        return MockUser(UserRole.VIEWER)

    @pytest.mark.asyncio
    async def test_no_user_returns_401(self, app: FastAPI) -> None:
        """Request without user should return 401."""
        checker = RBACChecker(minimum_role=UserRole.VIEWER)
        request = MagicMock()
        request.state = MagicMock(spec=[])  # No user attribute
        request.url.path = "/test"
        request.method = "GET"

        with pytest.raises(HTTPException) as exc_info:
            await checker(request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_minimum_role_admin_allows_admin(
        self, app: FastAPI, admin_user: MockUser
    ) -> None:
        """Admin should pass admin role check."""
        checker = RBACChecker(minimum_role=UserRole.ADMIN)
        request = MagicMock()
        request.state.user = admin_user
        request.url.path = "/admin/config"
        request.method = "GET"

        # Should not raise
        await checker(request)

    @pytest.mark.asyncio
    async def test_minimum_role_admin_denies_manager(
        self, app: FastAPI, manager_user: MockUser
    ) -> None:
        """Campaign manager should fail admin role check."""
        checker = RBACChecker(minimum_role=UserRole.ADMIN)
        request = MagicMock()
        request.state.user = manager_user
        request.url.path = "/admin/config"
        request.method = "GET"

        with pytest.raises(HTTPException) as exc_info:
            await checker(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_minimum_role_manager_allows_admin(
        self, app: FastAPI, admin_user: MockUser
    ) -> None:
        """Admin should pass campaign_manager role check (hierarchy)."""
        checker = RBACChecker(minimum_role=UserRole.CAMPAIGN_MANAGER)
        request = MagicMock()
        request.state.user = admin_user
        request.url.path = "/campaigns"
        request.method = "POST"

        # Should not raise
        await checker(request)

    @pytest.mark.asyncio
    async def test_minimum_role_manager_allows_manager(
        self, app: FastAPI, manager_user: MockUser
    ) -> None:
        """Campaign manager should pass campaign_manager role check."""
        checker = RBACChecker(minimum_role=UserRole.CAMPAIGN_MANAGER)
        request = MagicMock()
        request.state.user = manager_user
        request.url.path = "/campaigns"
        request.method = "POST"

        # Should not raise
        await checker(request)

    @pytest.mark.asyncio
    async def test_minimum_role_manager_denies_viewer(
        self, app: FastAPI, viewer_user: MockUser
    ) -> None:
        """Viewer should fail campaign_manager role check."""
        checker = RBACChecker(minimum_role=UserRole.CAMPAIGN_MANAGER)
        request = MagicMock()
        request.state.user = viewer_user
        request.url.path = "/campaigns"
        request.method = "POST"

        with pytest.raises(HTTPException) as exc_info:
            await checker(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_required_permission_allows(
        self, app: FastAPI, manager_user: MockUser
    ) -> None:
        """User with permission should pass."""
        checker = RBACChecker(required_permission=Permission.CAMPAIGN_CREATE)
        request = MagicMock()
        request.state.user = manager_user
        request.url.path = "/campaigns"
        request.method = "POST"

        # Should not raise
        await checker(request)

    @pytest.mark.asyncio
    async def test_required_permission_denies(
        self, app: FastAPI, viewer_user: MockUser
    ) -> None:
        """User without permission should fail."""
        checker = RBACChecker(required_permission=Permission.CAMPAIGN_CREATE)
        request = MagicMock()
        request.state.user = viewer_user
        request.url.path = "/campaigns"
        request.method = "POST"

        with pytest.raises(HTTPException) as exc_info:
            await checker(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "campaign:create" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_any_of_permissions_allows(
        self, app: FastAPI, manager_user: MockUser
    ) -> None:
        """User with any of the permissions should pass."""
        checker = RBACChecker(
            any_of_permissions={Permission.ADMIN_CONFIG_WRITE, Permission.CAMPAIGN_CREATE}
        )
        request = MagicMock()
        request.state.user = manager_user
        request.url.path = "/campaigns"
        request.method = "POST"

        # Should not raise (manager has CAMPAIGN_CREATE)
        await checker(request)

    @pytest.mark.asyncio
    async def test_any_of_permissions_denies(
        self, app: FastAPI, viewer_user: MockUser
    ) -> None:
        """User without any of the permissions should fail."""
        checker = RBACChecker(
            any_of_permissions={Permission.ADMIN_CONFIG_WRITE, Permission.CAMPAIGN_CREATE}
        )
        request = MagicMock()
        request.state.user = viewer_user
        request.url.path = "/campaigns"
        request.method = "POST"

        with pytest.raises(HTTPException) as exc_info:
            await checker(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_all_of_permissions_allows(
        self, app: FastAPI, admin_user: MockUser
    ) -> None:
        """User with all permissions should pass."""
        checker = RBACChecker(
            all_of_permissions={Permission.CAMPAIGN_CREATE, Permission.ADMIN_CONFIG_WRITE}
        )
        request = MagicMock()
        request.state.user = admin_user
        request.url.path = "/admin/campaigns"
        request.method = "POST"

        # Should not raise
        await checker(request)

    @pytest.mark.asyncio
    async def test_all_of_permissions_denies(
        self, app: FastAPI, manager_user: MockUser
    ) -> None:
        """User missing any permission should fail."""
        checker = RBACChecker(
            all_of_permissions={Permission.CAMPAIGN_CREATE, Permission.ADMIN_CONFIG_WRITE}
        )
        request = MagicMock()
        request.state.user = manager_user
        request.url.path = "/admin/campaigns"
        request.method = "POST"

        with pytest.raises(HTTPException) as exc_info:
            await checker(request)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestConvenienceFactories:
    """Tests for convenience dependency factories."""

    def test_require_admin_creates_checker(self) -> None:
        """require_admin should create checker with admin role."""
        checker = require_admin()
        assert checker.minimum_role == UserRole.ADMIN

    def test_require_campaign_manager_creates_checker(self) -> None:
        """require_campaign_manager should create checker with manager role."""
        checker = require_campaign_manager()
        assert checker.minimum_role == UserRole.CAMPAIGN_MANAGER

    def test_require_viewer_creates_checker(self) -> None:
        """require_viewer should create checker with viewer role."""
        checker = require_viewer()
        assert checker.minimum_role == UserRole.VIEWER

    def test_require_permission_creates_checker(self) -> None:
        """require_permission should create checker with permission."""
        checker = require_permission(Permission.CAMPAIGN_CREATE)
        assert checker.required_permission == Permission.CAMPAIGN_CREATE

    def test_require_any_permission_creates_checker(self) -> None:
        """require_any_permission should create checker with permissions set."""
        checker = require_any_permission(
            Permission.CAMPAIGN_CREATE, Permission.CAMPAIGN_UPDATE
        )
        assert checker.any_of_permissions == {
            Permission.CAMPAIGN_CREATE,
            Permission.CAMPAIGN_UPDATE,
        }

    def test_require_all_permissions_creates_checker(self) -> None:
        """require_all_permissions should create checker with permissions set."""
        checker = require_all_permissions(
            Permission.CAMPAIGN_CREATE, Permission.CAMPAIGN_UPDATE
        )
        assert checker.all_of_permissions == {
            Permission.CAMPAIGN_CREATE,
            Permission.CAMPAIGN_UPDATE,
        }


class TestRBACDecorator:
    """Tests for rbac_required decorator."""

    @pytest.mark.asyncio
    async def test_async_decorator_allows(self) -> None:
        """Async function with valid role should execute."""
        user = MockUser(UserRole.ADMIN)

        @rbac_required(minimum_role=UserRole.ADMIN)
        async def admin_action(user: MockUser) -> str:
            return "success"

        result = await admin_action(user=user)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_decorator_denies(self) -> None:
        """Async function with invalid role should raise."""
        user = MockUser(UserRole.VIEWER)

        @rbac_required(minimum_role=UserRole.ADMIN)
        async def admin_action(user: MockUser) -> str:
            return "success"

        with pytest.raises(PermissionError) as exc_info:
            await admin_action(user=user)

        assert "admin" in str(exc_info.value).lower()

    def test_sync_decorator_allows(self) -> None:
        """Sync function with valid role should execute."""
        user = MockUser(UserRole.CAMPAIGN_MANAGER)

        @rbac_required(permission=Permission.CAMPAIGN_CREATE)
        def create_campaign(user: MockUser) -> str:
            return "created"

        result = create_campaign(user=user)
        assert result == "created"

    def test_sync_decorator_denies(self) -> None:
        """Sync function with invalid permission should raise."""
        user = MockUser(UserRole.VIEWER)

        @rbac_required(permission=Permission.CAMPAIGN_CREATE)
        def create_campaign(user: MockUser) -> str:
            return "created"

        with pytest.raises(PermissionError) as exc_info:
            create_campaign(user=user)

        assert "campaign:create" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_decorator_no_user_raises(self) -> None:
        """Decorator without user context should raise ValueError."""

        @rbac_required(minimum_role=UserRole.VIEWER)
        async def some_action() -> str:
            return "success"

        with pytest.raises(ValueError) as exc_info:
            await some_action()

        assert "No user context" in str(exc_info.value)


class TestRBACIntegration:
    """Integration tests for RBAC with FastAPI routes."""

    @pytest.fixture
    def app_with_routes(self) -> FastAPI:
        """Create FastAPI app with protected routes."""
        from fastapi import Depends

        app = FastAPI()

        @app.get("/admin/config", dependencies=[Depends(require_admin())])
        async def admin_config() -> dict[str, str]:
            return {"status": "admin only"}

        @app.get("/campaigns", dependencies=[Depends(require_viewer())])
        async def list_campaigns() -> dict[str, str]:
            return {"status": "all users"}

        @app.post(
            "/campaigns",
            dependencies=[Depends(require_permission(Permission.CAMPAIGN_CREATE))],
        )
        async def create_campaign() -> dict[str, str]:
            return {"status": "created"}

        return app

    @pytest.mark.asyncio
    async def test_admin_route_with_admin(self, app_with_routes: FastAPI) -> None:
        """Admin route should allow admin user."""
        admin_user = MockUser(UserRole.ADMIN)

        # Middleware to inject user
        @app_with_routes.middleware("http")
        async def inject_user(request, call_next):
            request.state.user = admin_user
            return await call_next(request)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_routes),
            base_url="http://test",
        ) as client:
            response = await client.get("/admin/config")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_route_with_viewer(self, app_with_routes: FastAPI) -> None:
        """Admin route should deny viewer user."""
        viewer_user = MockUser(UserRole.VIEWER)

        @app_with_routes.middleware("http")
        async def inject_user(request, call_next):
            request.state.user = viewer_user
            return await call_next(request)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_routes),
            base_url="http://test",
        ) as client:
            response = await client.get("/admin/config")
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_route_with_viewer(self, app_with_routes: FastAPI) -> None:
        """Viewer route should allow viewer user."""
        viewer_user = MockUser(UserRole.VIEWER)

        @app_with_routes.middleware("http")
        async def inject_user(request, call_next):
            request.state.user = viewer_user
            return await call_next(request)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_routes),
            base_url="http://test",
        ) as client:
            response = await client.get("/campaigns")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_permission_route_with_manager(
        self, app_with_routes: FastAPI
    ) -> None:
        """Permission-protected route should allow user with permission."""
        manager_user = MockUser(UserRole.CAMPAIGN_MANAGER)

        @app_with_routes.middleware("http")
        async def inject_user(request, call_next):
            request.state.user = manager_user
            return await call_next(request)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_routes),
            base_url="http://test",
        ) as client:
            response = await client.post("/campaigns")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_permission_route_with_viewer(
        self, app_with_routes: FastAPI
    ) -> None:
        """Permission-protected route should deny user without permission."""
        viewer_user = MockUser(UserRole.VIEWER)

        @app_with_routes.middleware("http")
        async def inject_user(request, call_next):
            request.state.user = viewer_user
            return await call_next(request)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_routes),
            base_url="http://test",
        ) as client:
            response = await client.post("/campaigns")
            assert response.status_code == 403


class TestAccessLogging:
    """Tests for access denial logging."""

    @pytest.mark.asyncio
    async def test_denied_access_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Denied access should be logged with details."""
        import logging

        caplog.set_level(logging.WARNING)

        viewer_user = MockUser(UserRole.VIEWER)
        checker = RBACChecker(minimum_role=UserRole.ADMIN)

        request = MagicMock()
        request.state.user = viewer_user
        request.url.path = "/admin/config"
        request.method = "PUT"

        with pytest.raises(HTTPException):
            await checker(request)

        # Check log contains required information
        assert any("Access denied" in record.message for record in caplog.records)
        assert any(
            str(viewer_user.id) in str(record.__dict__)
            for record in caplog.records
            if "Access denied" in record.message
        )