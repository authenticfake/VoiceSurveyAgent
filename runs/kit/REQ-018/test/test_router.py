"""
Integration tests for export API endpoints.

REQ-018: Campaign CSV export
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.dashboard.router import export_router, router as dashboard_router
from app.dashboard.storage import InMemoryStorageProvider
from app.shared.auth import CurrentUser, create_access_token
from app.shared.models import (
    Campaign,
    Contact,
    ExportJobStatus,
    User,
    UserRole,
)


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI application."""
    app = FastAPI()
    app.include_router(dashboard_router)
    app.include_router(export_router)
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_storage() -> InMemoryStorageProvider:
    """Create mock storage provider."""
    return InMemoryStorageProvider()


@pytest.fixture
def campaign_manager_token(test_user: User) -> str:
    """Create JWT token for campaign manager."""
    return create_access_token(test_user)


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create JWT token for admin."""
    return create_access_token(admin_user)


@pytest.fixture
def viewer_token(viewer_user: User) -> str:
    """Create JWT token for viewer."""
    return create_access_token(viewer_user)


class TestExportEndpoints:
    """Tests for export API endpoints."""

    @pytest.mark.asyncio
    async def test_initiate_export_success(
        self,
        client: AsyncClient,
        test_campaign: Campaign,
        test_user: User,
        campaign_manager_token: str,
        db_session,
        mock_storage: InMemoryStorageProvider,
    ):
        """Test initiating export successfully."""
        with patch(
            "app.dashboard.router.get_storage_provider",
            return_value=mock_storage,
        ), patch(
            "app.dashboard.router.get_db_session",
            return_value=db_session,
        ), patch(
            "app.shared.auth.get_db_session",
            return_value=db_session,
        ):
            response = await client.get(
                f"/api/campaigns/{test_campaign.id}/export",
                headers={"Authorization": f"Bearer {campaign_manager_token}"},
            )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_initiate_export_campaign_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        campaign_manager_token: str,
        db_session,
        mock_storage: InMemoryStorageProvider,
    ):
        """Test initiating export for non-existent campaign."""
        with patch(
            "app.dashboard.router.get_storage_provider",
            return_value=mock_storage,
        ), patch(
            "app.dashboard.router.get_db_session",
            return_value=db_session,
        ), patch(
            "app.shared.auth.get_db_session",
            return_value=db_session,
        ):
            response = await client.get(
                f"/api/campaigns/{uuid4()}/export",
                headers={"Authorization": f"Bearer {campaign_manager_token}"},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_initiate_export_unauthorized(
        self,
        client: AsyncClient,
        test_campaign: Campaign,
    ):
        """Test initiating export without authentication."""
        response = await client.get(
            f"/api/campaigns/{test_campaign.id}/export",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_initiate_export_forbidden_for_viewer(
        self,
        client: AsyncClient,
        test_campaign: Campaign,
        viewer_user: User,
        viewer_token: str,
        db_session,
        mock_storage: InMemoryStorageProvider,
    ):
        """Test viewer cannot initiate export."""
        with patch(
            "app.dashboard.router.get_storage_provider",
            return_value=mock_storage,
        ), patch(
            "app.dashboard.router.get_db_session",
            return_value=db_session,
        ), patch(
            "app.shared.auth.get_db_session",
            return_value=db_session,
        ):
            response = await client.get(
                f"/api/campaigns/{test_campaign.id}/export",
                headers={"Authorization": f"Bearer {viewer_token}"},
            )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_export_job_success(
        self,
        client: AsyncClient,
        test_campaign: Campaign,
        test_user: User,
        campaign_manager_token: str,
        db_session,
        mock_storage: InMemoryStorageProvider,
    ):
        """Test getting export job status."""
        # First create a job
        from app.dashboard.export_service import ExportService

        service = ExportService(db=db_session, storage=mock_storage)
        job = await service.create_export_job(
            campaign_id=test_campaign.id,
            user_id=test_user.id,
        )
        await db_session.flush()

        with patch(
            "app.dashboard.router.get_storage_provider",
            return_value=mock_storage,
        ), patch(
            "app.dashboard.router.get_db_session",
            return_value=db_session,
        ), patch(
            "app.shared.auth.get_db_session",
            return_value=db_session,
        ):
            response = await client.get(
                f"/api/exports/{job.id}",
                headers={"Authorization": f"Bearer {campaign_manager_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job.id)
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_export_job_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        campaign_manager_token: str,
        db_session,
        mock_storage: InMemoryStorageProvider,
    ):
        """Test getting non-existent export job."""
        with patch(
            "app.dashboard.router.get_storage_provider",
            return_value=mock_storage,
        ), patch(
            "app.dashboard.router.get_db_session",
            return_value=db_session,
        ), patch(
            "app.shared.auth.get_db_session",
            return_value=db_session,
        ):
            response = await client.get(
                f"/api/exports/{uuid4()}",
                headers={"Authorization": f"Bearer {campaign_manager_token}"},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_campaign_exports(
        self,
        client: AsyncClient,
        test_campaign: Campaign,
        test_user: User,
        campaign_manager_token: str,
        db_session,
        mock_storage: InMemoryStorageProvider,
    ):
        """Test listing export jobs for a campaign."""
        # Create some jobs
        from app.dashboard.export_service import ExportService

        service = ExportService(db=db_session, storage=mock_storage)
        for _ in range(3):
            await service.create_export_job(
                campaign_id=test_campaign.id,
                user_id=test_user.id,
            )
        await db_session.flush()

        with patch(
            "app.dashboard.router.get_storage_provider",
            return_value=mock_storage,
        ), patch(
            "app.dashboard.router.get_db_session",
            return_value=db_session,
        ), patch(
            "app.shared.auth.get_db_session",
            return_value=db_session,
        ):
            response = await client.get(
                f"/api/campaigns/{test_campaign.id}/exports",
                headers={"Authorization": f"Bearer {campaign_manager_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_admin_can_export(
        self,
        client: AsyncClient,
        test_campaign: Campaign,
        admin_user: User,
        admin_token: str,
        db_session,
        mock_storage: InMemoryStorageProvider,
    ):
        """Test admin can initiate export."""
        with patch(
            "app.dashboard.router.get_storage_provider",
            return_value=mock_storage,
        ), patch(
            "app.dashboard.router.get_db_session",
            return_value=db_session,
        ), patch(
            "app.shared.auth.get_db_session",
            return_value=db_session,
        ):
            response = await client.get(
                f"/api/campaigns/{test_campaign.id}/export",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert response.status_code == 202