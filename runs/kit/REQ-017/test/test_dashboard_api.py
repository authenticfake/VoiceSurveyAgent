"""
Integration tests for dashboard API.

REQ-017: Campaign dashboard stats API
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.dashboard.models import Campaign, Contact, User
from app.dashboard.router import router
from app.shared.auth import UserRole
from app.shared.config import get_settings
from app.shared.database import get_db

settings = get_settings()


@pytest.fixture
def app(db_session):
    """Create test FastAPI app."""
    test_app = FastAPI()
    test_app.include_router(router)

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


@pytest.fixture
def auth_token(test_user: User) -> str:
    """Create valid JWT token for test user."""
    payload = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "name": test_user.name,
        "role": test_user.role.value,
        "oidc_sub": test_user.oidc_sub,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture
def admin_token(test_user: User) -> str:
    """Create valid JWT token for admin user."""
    payload = {
        "sub": str(test_user.id),
        "email": "admin@example.com",
        "name": "Admin User",
        "role": "admin",
        "oidc_sub": "oidc|admin001",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture
def viewer_token(test_user: User) -> str:
    """Create valid JWT token for viewer user."""
    payload = {
        "sub": str(test_user.id),
        "email": "viewer@example.com",
        "name": "Viewer User",
        "role": "viewer",
        "oidc_sub": "oidc|viewer001",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


class TestDashboardAPI:
    """Integration tests for dashboard API endpoints."""

    @pytest.mark.asyncio
    async def test_get_campaign_stats_success(
        self,
        app: FastAPI,
        auth_token: str,
        test_campaign: Campaign,
        test_contacts: list[Contact],
        test_call_attempts,
    ):
        """Test successful stats retrieval."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/campaigns/{test_campaign.id}/stats",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["campaign_id"] == str(test_campaign.id)
        assert data["campaign_name"] == test_campaign.name
        assert "contacts" in data
        assert "call_outcomes" in data
        assert "rates" in data
        assert "duration_stats" in data

    @pytest.mark.asyncio
    async def test_get_campaign_stats_not_found(
        self,
        app: FastAPI,
        auth_token: str,
    ):
        """Test stats for non-existent campaign."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/campaigns/{uuid4()}/stats",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_campaign_stats_unauthorized(
        self,
        app: FastAPI,
        test_campaign: Campaign,
    ):
        """Test stats without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/campaigns/{test_campaign.id}/stats",
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_campaign_stats_viewer_allowed(
        self,
        app: FastAPI,
        viewer_token: str,
        test_campaign: Campaign,
        test_contacts: list[Contact],
    ):
        """Test that viewer role can access stats."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/campaigns/{test_campaign.id}/stats",
                headers={"Authorization": f"Bearer {viewer_token}"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_campaign_stats_without_time_series(
        self,
        app: FastAPI,
        auth_token: str,
        test_campaign: Campaign,
        test_contacts: list[Contact],
    ):
        """Test stats without time series data."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/campaigns/{test_campaign.id}/stats",
                params={"include_time_series": False},
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["time_series_hourly"] == []
        assert data["time_series_daily"] == []

    @pytest.mark.asyncio
    async def test_invalidate_cache_admin_only(
        self,
        app: FastAPI,
        auth_token: str,
        admin_token: str,
        test_campaign: Campaign,
    ):
        """Test that cache invalidation requires admin role."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Campaign manager should be denied
            response = await client.post(
                f"/api/campaigns/{test_campaign.id}/stats/invalidate",
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            assert response.status_code == 403

            # Admin should be allowed
            response = await client.post(
                f"/api/campaigns/{test_campaign.id}/stats/invalidate",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert response.status_code == 204