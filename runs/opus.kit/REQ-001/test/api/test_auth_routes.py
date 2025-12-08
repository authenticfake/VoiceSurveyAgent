"""Tests for auth API routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth.domain import User, UserCreate, UserRole
from app.auth.oidc import OIDCClient, TokenPayload, TokenResponse
from app.auth.repository import InMemoryUserRepository


class TestAuthRoutes:
    """Tests for authentication routes."""

    @pytest.mark.asyncio
    async def test_login_initiation(self, async_client: AsyncClient) -> None:
        """Test login initiation returns authorization URL."""
        response = await async_client.get("/api/auth/login")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert "authorize" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_callback_success(
        self,
        async_client: AsyncClient,
        user_repository: InMemoryUserRepository,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test successful OAuth callback."""
        mock_tokens = TokenResponse(
            access_token="access-token-123",
            token_type="Bearer",
            expires_in=3600,
            id_token="id-token-123",
        )
        mock_payload = TokenPayload(
            sub="callback-user-sub",
            email="callback@example.com",
            name="Callback User",
        )

        with patch.object(
            mock_oidc_client, "exchange_code", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.return_value = mock_tokens

            with patch.object(
                mock_oidc_client, "validate_id_token", new_callable=AsyncMock
            ) as mock_validate:
                mock_validate.return_value = mock_payload

                response = await async_client.post(
                    "/api/auth/callback",
                    json={"code": "auth-code", "state": "test-state"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["access_token"] == "access-token-123"
                assert data["user"]["email"] == "callback@example.com"

    @pytest.mark.asyncio
    async def test_callback_get_success(
        self,
        async_client: AsyncClient,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test OAuth callback via GET."""
        mock_tokens = TokenResponse(
            access_token="access-token-456",
            token_type="Bearer",
            id_token="id-token-456",
        )
        mock_payload = TokenPayload(
            sub="get-callback-sub",
            email="getcallback@example.com",
            name="Get Callback User",
        )

        with patch.object(
            mock_oidc_client, "exchange_code", new_callable=AsyncMock
        ) as mock_exchange:
            mock_exchange.return_value = mock_tokens

            with patch.object(
                mock_oidc_client, "validate_id_token", new_callable=AsyncMock
            ) as mock_validate:
                mock_validate.return_value = mock_payload

                response = await async_client.get(
                    "/api/auth/callback",
                    params={"code": "auth-code", "state": "test-state"},
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, async_client: AsyncClient) -> None:
        """Test /me endpoint without authentication."""
        response = await async_client.get("/api/auth/me")

        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "MISSING_TOKEN"

    @pytest.mark.asyncio
    async def test_me_authenticated(
        self,
        async_client: AsyncClient,
        user_repository: InMemoryUserRepository,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test /me endpoint with valid authentication."""
        # Create user in repository
        user = await user_repository.create(
            UserCreate(
                oidc_sub="me-test-sub",
                email="me@example.com",
                name="Me User",
                role=UserRole.CAMPAIGN_MANAGER,
            )
        )

        mock_payload = TokenPayload(
            sub="me-test-sub",
            email="me@example.com",
            name="Me User",
        )

        with patch.object(
            mock_oidc_client, "validate_access_token", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = mock_payload

            response = await async_client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer valid-token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "me@example.com"
            assert data["role"] == "campaign_manager"


class TestProtectedRoutes:
    """Tests for protected routes with RBAC."""

    @pytest.mark.asyncio
    async def test_viewer_resource_with_viewer(
        self,
        async_client: AsyncClient,
        user_repository: InMemoryUserRepository,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test viewer can access viewer resource."""
        await user_repository.create(
            UserCreate(
                oidc_sub="viewer-sub",
                email="viewer@example.com",
                name="Viewer",
                role=UserRole.VIEWER,
            )
        )

        mock_payload = TokenPayload(sub="viewer-sub")

        with patch.object(
            mock_oidc_client, "validate_access_token", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = mock_payload

            response = await async_client.get(
                "/api/protected/viewer-resource",
                headers={"Authorization": "Bearer token"},
            )

            assert response.status_code == 200
            assert response.json()["user_role"] == "viewer"

    @pytest.mark.asyncio
    async def test_writer_resource_with_viewer_forbidden(
        self,
        async_client: AsyncClient,
        user_repository: InMemoryUserRepository,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test viewer cannot access writer resource."""
        await user_repository.create(
            UserCreate(
                oidc_sub="viewer-sub-2",
                email="viewer2@example.com",
                name="Viewer 2",
                role=UserRole.VIEWER,
            )
        )

        mock_payload = TokenPayload(sub="viewer-sub-2")

        with patch.object(
            mock_oidc_client, "validate_access_token", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = mock_payload

            response = await async_client.get(
                "/api/protected/writer-resource",
                headers={"Authorization": "Bearer token"},
            )

            assert response.status_code == 403
            assert response.json()["code"] == "INSUFFICIENT_PERMISSIONS"

    @pytest.mark.asyncio
    async def test_writer_resource_with_campaign_manager(
        self,
        async_client: AsyncClient,
        user_repository: InMemoryUserRepository,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test campaign manager can access writer resource."""
        await user_repository.create(
            UserCreate(
                oidc_sub="manager-sub",
                email="manager@example.com",
                name="Manager",
                role=UserRole.CAMPAIGN_MANAGER,
            )
        )

        mock_payload = TokenPayload(sub="manager-sub")

        with patch.object(
            mock_oidc_client, "validate_access_token", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = mock_payload

            response = await async_client.get(
                "/api/protected/writer-resource",
                headers={"Authorization": "Bearer token"},
            )

            assert response.status_code == 200
            assert response.json()["user_role"] == "campaign_manager"

    @pytest.mark.asyncio
    async def test_admin_resource_with_admin(
        self,
        async_client: AsyncClient,
        user_repository: InMemoryUserRepository,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test admin can access admin resource."""
        await user_repository.create(
            UserCreate(
                oidc_sub="admin-sub",
                email="admin@example.com",
                name="Admin",
                role=UserRole.ADMIN,
            )
        )

        mock_payload = TokenPayload(sub="admin-sub")

        with patch.object(
            mock_oidc_client, "validate_access_token", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = mock_payload

            response = await async_client.get(
                "/api/protected/admin-resource",
                headers={"Authorization": "Bearer token"},
            )

            assert response.status_code == 200
            assert response.json()["user_role"] == "admin"

    @pytest.mark.asyncio
    async def test_admin_resource_with_campaign_manager_forbidden(
        self,
        async_client: AsyncClient,
        user_repository: InMemoryUserRepository,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test campaign manager cannot access admin resource."""
        await user_repository.create(
            UserCreate(
                oidc_sub="manager-sub-2",
                email="manager2@example.com",
                name="Manager 2",
                role=UserRole.CAMPAIGN_MANAGER,
            )
        )

        mock_payload = TokenPayload(sub="manager-sub-2")

        with patch.object(
            mock_oidc_client, "validate_access_token", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = mock_payload

            response = await async_client.get(
                "/api/protected/admin-resource",
                headers={"Authorization": "Bearer token"},
            )

            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_my_permissions_viewer(
        self,
        async_client: AsyncClient,
        user_repository: InMemoryUserRepository,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test permissions endpoint for viewer."""
        await user_repository.create(
            UserCreate(
                oidc_sub="perm-viewer-sub",
                email="permviewer@example.com",
                name="Perm Viewer",
                role=UserRole.VIEWER,
            )
        )

        mock_payload = TokenPayload(sub="perm-viewer-sub")

        with patch.object(
            mock_oidc_client, "validate_access_token", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = mock_payload

            response = await async_client.get(
                "/api/protected/my-permissions",
                headers={"Authorization": "Bearer token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["permissions"]["can_read"] is True
            assert data["permissions"]["can_write"] is False
            assert data["permissions"]["is_admin"] is False

    @pytest.mark.asyncio
    async def test_my_permissions_admin(
        self,
        async_client: AsyncClient,
        user_repository: InMemoryUserRepository,
        mock_oidc_client: OIDCClient,
    ) -> None:
        """Test permissions endpoint for admin."""
        await user_repository.create(
            UserCreate(
                oidc_sub="perm-admin-sub",
                email="permadmin@example.com",
                name="Perm Admin",
                role=UserRole.ADMIN,
            )
        )

        mock_payload = TokenPayload(sub="perm-admin-sub")

        with patch.object(
            mock_oidc_client, "validate_access_token", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = mock_payload

            response = await async_client.get(
                "/api/protected/my-permissions",
                headers={"Authorization": "Bearer token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["permissions"]["can_read"] is True
            assert data["permissions"]["can_write"] is True
            assert data["permissions"]["is_admin"] is True