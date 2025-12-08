"""
Tests for RBAC authorization middleware.

Tests role-based access control functionality.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.auth.rbac import (
    RequireRole,
    get_current_user,
    get_token_payload,
    require_admin,
    require_campaign_manager,
    require_viewer,
    ViewerUser,
    CampaignManagerUser,
    AdminUser,
)
from app.auth.schemas import TokenPayload, UserContext, UserRole
from app.shared.exceptions import AuthenticationError, AuthorizationError


@pytest.fixture
def mock_token_payload() -> TokenPayload:
    """Create a mock token payload."""
    return TokenPayload(
        sub="test-oidc-sub",
        exp=datetime.now(timezone.utc) + timedelta(hours=1),
        iat=datetime.now(timezone.utc),
        iss="https://idp.example.com",
        aud="test-client-id",
        email="test@example.com",
        name="Test User",
        role=UserRole.CAMPAIGN_MANAGER,
    )


@pytest.fixture
def mock_user_context() -> UserContext:
    """Create a mock user context."""
    return UserContext(
        id=uuid4(),
        oidc_sub="test-oidc-sub",
        email="test@example.com",
        name="Test User",
        role=UserRole.CAMPAIGN_MANAGER,
    )


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test FastAPI application with protected routes."""
    app = FastAPI()

    @app.get("/viewer-only")
    async def viewer_endpoint(user: ViewerUser) -> dict:
        return {"user_id": str(user.id), "role": user.role.value}

    @app.get("/manager-only")
    async def manager_endpoint(user: CampaignManagerUser) -> dict:
        return {"user_id": str(user.id), "role": user.role.value}

    @app.get("/admin-only")
    async def admin_endpoint(user: AdminUser) -> dict:
        return {"user_id": str(user.id), "role": user.role.value}

    return app


class TestGetTokenPayload:
    """Tests for get_token_payload dependency."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self) -> None:
        """Test that missing authorization header raises error."""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_token_payload(authorization=None)
        assert "Missing authorization header" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_invalid_authorization_format(self) -> None:
        """Test that invalid authorization format raises error."""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_token_payload(authorization="InvalidFormat token123")
        assert "Invalid authorization header format" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_valid_bearer_token(self, mock_token_payload: TokenPayload) -> None:
        """Test that valid bearer token is processed."""
        with patch("app.auth.rbac.AuthService") as mock_auth_service:
            mock_instance = mock_auth_service.return_value
            mock_instance.validate_token = AsyncMock(return_value=mock_token_payload)

            result = await get_token_payload(authorization="Bearer valid-token")

            assert result == mock_token_payload
            mock_instance.validate_token.assert_called_once_with("valid-token")


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_existing_user_returned(
        self, mock_token_payload: TokenPayload
    ) -> None:
        """Test that existing user is returned from database."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.oidc_sub = mock_token_payload.sub
        mock_user.email = mock_token_payload.email
        mock_user.name = mock_token_payload.name
        mock_user.role = UserRole.CAMPAIGN_MANAGER.value

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_current_user(mock_token_payload, mock_db)

        assert result.oidc_sub == mock_token_payload.sub
        assert result.email == mock_token_payload.email
        assert result.role == UserRole.CAMPAIGN_MANAGER

    @pytest.mark.asyncio
    async def test_new_user_created_on_first_login(
        self, mock_token_payload: TokenPayload
    ) -> None:
        """Test that new user is created on first login."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with patch("app.auth.rbac.User") as mock_user_class:
            mock_new_user = MagicMock()
            mock_new_user.id = uuid4()
            mock_new_user.oidc_sub = mock_token_payload.sub
            mock_new_user.email = mock_token_payload.email
            mock_new_user.name = mock_token_payload.name
            mock_new_user.role = UserRole.VIEWER.value
            mock_user_class.return_value = mock_new_user

            result = await get_current_user(mock_token_payload, mock_db)

            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
            assert result.oidc_sub == mock_token_payload.sub


class TestRequireRole:
    """Tests for RequireRole dependency class."""

    @pytest.mark.asyncio
    async def test_viewer_can_access_viewer_endpoint(
        self, mock_user_context: UserContext
    ) -> None:
        """Test that viewer role can access viewer-level endpoints."""
        mock_user_context.role = UserRole.VIEWER
        mock_request = MagicMock()
        mock_request.url.path = "/viewer-only"
        mock_request.method = "GET"

        require_role = RequireRole(UserRole.VIEWER)
        result = await require_role(mock_request, mock_user_context)

        assert result == mock_user_context

    @pytest.mark.asyncio
    async def test_viewer_cannot_access_manager_endpoint(
        self, mock_user_context: UserContext
    ) -> None:
        """Test that viewer role cannot access manager-level endpoints."""
        mock_user_context.role = UserRole.VIEWER
        mock_request = MagicMock()
        mock_request.url.path = "/manager-only"
        mock_request.method = "GET"

        require_role = RequireRole(UserRole.CAMPAIGN_MANAGER)

        with pytest.raises(AuthorizationError) as exc_info:
            await require_role(mock_request, mock_user_context)

        assert "campaign_manager" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_admin_can_access_all_endpoints(
        self, mock_user_context: UserContext
    ) -> None:
        """Test that admin role can access all endpoints."""
        mock_user_context.role = UserRole.ADMIN
        mock_request = MagicMock()
        mock_request.url.path = "/admin-only"
        mock_request.method = "GET"

        # Test admin endpoint
        require_admin_role = RequireRole(UserRole.ADMIN)
        result = await require_admin_role(mock_request, mock_user_context)
        assert result == mock_user_context

        # Test manager endpoint
        require_manager_role = RequireRole(UserRole.CAMPAIGN_MANAGER)
        result = await require_manager_role(mock_request, mock_user_context)
        assert result == mock_user_context

        # Test viewer endpoint
        require_viewer_role = RequireRole(UserRole.VIEWER)
        result = await require_viewer_role(mock_request, mock_user_context)
        assert result == mock_user_context

    @pytest.mark.asyncio
    async def test_campaign_manager_can_access_viewer_and_manager(
        self, mock_user_context: UserContext
    ) -> None:
        """Test that campaign_manager can access viewer and manager endpoints."""
        mock_user_context.role = UserRole.CAMPAIGN_MANAGER
        mock_request = MagicMock()
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        # Can access viewer endpoint
        require_viewer_role = RequireRole(UserRole.VIEWER)
        result = await require_viewer_role(mock_request, mock_user_context)
        assert result == mock_user_context

        # Can access manager endpoint
        require_manager_role = RequireRole(UserRole.CAMPAIGN_MANAGER)
        result = await require_manager_role(mock_request, mock_user_context)
        assert result == mock_user_context

    @pytest.mark.asyncio
    async def test_campaign_manager_cannot_access_admin(
        self, mock_user_context: UserContext
    ) -> None:
        """Test that campaign_manager cannot access admin endpoints."""
        mock_user_context.role = UserRole.CAMPAIGN_MANAGER
        mock_request = MagicMock()
        mock_request.url.path = "/admin-only"
        mock_request.method = "GET"

        require_admin_role = RequireRole(UserRole.ADMIN)

        with pytest.raises(AuthorizationError) as exc_info:
            await require_admin_role(mock_request, mock_user_context)

        assert "admin" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_access_denied_logged(
        self, mock_user_context: UserContext
    ) -> None:
        """Test that denied access attempts are logged."""
        mock_user_context.role = UserRole.VIEWER
        mock_request = MagicMock()
        mock_request.url.path = "/admin-only"
        mock_request.method = "POST"

        require_admin_role = RequireRole(UserRole.ADMIN)

        with patch("app.auth.rbac.logger") as mock_logger:
            with pytest.raises(AuthorizationError):
                await require_admin_role(mock_request, mock_user_context)

            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args[1]
            assert call_kwargs["user_id"] == str(mock_user_context.id)
            assert call_kwargs["endpoint"] == "/admin-only"
            assert call_kwargs["method"] == "POST"


class TestPreConfiguredDependencies:
    """Tests for pre-configured role dependencies."""

    def test_require_viewer_is_configured(self) -> None:
        """Test that require_viewer is properly configured."""
        assert isinstance(require_viewer, RequireRole)
        assert require_viewer.minimum_role == UserRole.VIEWER

    def test_require_campaign_manager_is_configured(self) -> None:
        """Test that require_campaign_manager is properly configured."""
        assert isinstance(require_campaign_manager, RequireRole)
        assert require_campaign_manager.minimum_role == UserRole.CAMPAIGN_MANAGER

    def test_require_admin_is_configured(self) -> None:
        """Test that require_admin is properly configured."""
        assert isinstance(require_admin, RequireRole)
        assert require_admin.minimum_role == UserRole.ADMIN


class TestIntegrationWithFastAPI:
    """Integration tests with FastAPI application."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_auth(self, test_app: FastAPI) -> None:
        """Test that protected endpoint returns 401 without auth."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test"
        ) as client:
            response = await client.get("/viewer-only")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_auth(
        self, test_app: FastAPI, mock_user_context: UserContext
    ) -> None:
        """Test that protected endpoint works with valid auth."""
        # Override dependencies for testing
        async def override_get_current_user() -> UserContext:
            return mock_user_context

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/viewer-only",
                headers={"Authorization": "Bearer test-token"}
            )
            # Should work since campaign_manager >= viewer
            assert response.status_code == 200
            data = response.json()
            assert data["role"] == "campaign_manager"

        # Clean up
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_insufficient_role_returns_403(
        self, test_app: FastAPI, mock_user_context: UserContext
    ) -> None:
        """Test that insufficient role returns 403."""
        mock_user_context.role = UserRole.VIEWER

        async def override_get_current_user() -> UserContext:
            return mock_user_context

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/admin-only",
                headers={"Authorization": "Bearer test-token"}
            )
            assert response.status_code == 403

        test_app.dependency_overrides.clear()