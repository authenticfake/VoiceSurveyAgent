"""Tests for auth dependencies."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import (
    get_current_user,
    get_token_payload,
    require_role,
)
from app.auth.domain import User, UserRole
from app.auth.errors import TokenExpiredError, TokenValidationError
from app.auth.oidc import OIDCClient, TokenPayload
from app.auth.repository import InMemoryUserRepository


class TestRequireRole:
    """Tests for require_role dependency."""

    @pytest.mark.asyncio
    async def test_require_admin_with_admin(self, admin_user: User) -> None:
        """Test admin role requirement with admin user."""
        checker = require_role(UserRole.ADMIN)

        # Mock the get_current_user dependency
        async def mock_get_current_user() -> User:
            return admin_user

        # The checker should return the user
        result = await checker(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_admin_with_viewer(self, sample_user: User) -> None:
        """Test admin role requirement with viewer user."""
        checker = require_role(UserRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            await checker(sample_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "INSUFFICIENT_PERMISSIONS"

    @pytest.mark.asyncio
    async def test_require_multiple_roles(
        self, campaign_manager_user: User, sample_user: User
    ) -> None:
        """Test requiring one of multiple roles."""
        checker = require_role(UserRole.ADMIN, UserRole.CAMPAIGN_MANAGER)

        # Campaign manager should pass
        result = await checker(campaign_manager_user)
        assert result == campaign_manager_user

        # Viewer should fail
        with pytest.raises(HTTPException) as exc_info:
            await checker(sample_user)
        assert exc_info.value.status_code == 403