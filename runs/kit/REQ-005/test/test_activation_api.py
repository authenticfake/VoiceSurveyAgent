"""
Integration tests for campaign activation API.

REQ-005: Campaign validation service
"""

from datetime import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.middleware import CurrentUser
from app.campaigns.models import Campaign, CampaignLanguage, CampaignStatus, QuestionType
from app.main import app


@pytest.fixture
def mock_current_user() -> CurrentUser:
    """Create mock authenticated user."""
    return CurrentUser(
        id=uuid4(),
        email="manager@example.com",
        name="Campaign Manager",
        role="campaign_manager",
    )


@pytest.fixture
def valid_campaign() -> Campaign:
    """Create a valid campaign for testing."""
    campaign = Campaign(
        id=uuid4(),
        name="Test Campaign",
        description="Test description",
        status=CampaignStatus.DRAFT,
        language=CampaignLanguage.EN,
        intro_script="Hello, this is a test survey...",
        question_1_text="How satisfied are you?",
        question_1_type=QuestionType.SCALE,
        question_2_text="What could we improve?",
        question_2_type=QuestionType.FREE_TEXT,
        question_3_text="Would you recommend us?",
        question_3_type=QuestionType.NUMERIC,
        max_attempts=3,
        retry_interval_minutes=60,
        allowed_call_start_local=time(9, 0),
        allowed_call_end_local=time(20, 0),
        created_by_user_id=uuid4(),
    )
    return campaign


@pytest.fixture
async def client() -> AsyncClient:
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestActivateCampaignAPI:
    """Tests for POST /api/campaigns/{id}/activate endpoint."""

    @pytest.mark.asyncio
    async def test_activate_success(
        self,
        client: AsyncClient,
        mock_current_user: CurrentUser,
        valid_campaign: Campaign,
    ) -> None:
        """Test successful campaign activation."""
        with (
            patch("app.campaigns.activation_router.require_campaign_manager") as mock_rbac,
            patch("app.campaigns.activation_router.get_validation_service") as mock_service_dep,
        ):
            # Setup mocks
            mock_rbac.return_value = mock_current_user
            mock_service = AsyncMock()
            valid_campaign.status = CampaignStatus.RUNNING
            mock_service.activate_campaign.return_value = valid_campaign
            mock_service_dep.return_value = mock_service

            response = await client.post(
                f"/api/campaigns/{valid_campaign.id}/activate",
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_activate_validation_fails(
        self,
        client: AsyncClient,
        mock_current_user: CurrentUser,
        valid_campaign: Campaign,
    ) -> None:
        """Test activation returns 400 when validation fails."""
        from app.shared.exceptions import ValidationError

        with (
            patch("app.campaigns.activation_router.require_campaign_manager") as mock_rbac,
            patch("app.campaigns.activation_router.get_validation_service") as mock_service_dep,
        ):
            mock_rbac.return_value = mock_current_user
            mock_service = AsyncMock()
            mock_service.activate_campaign.side_effect = ValidationError(
                message="Campaign validation failed",
                details=[{"field": "contacts", "message": "Campaign must have at least one contact"}],
            )
            mock_service_dep.return_value = mock_service

            response = await client.post(
                f"/api/campaigns/{valid_campaign.id}/activate",
            )

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["code"] == "VALIDATION_FAILED"
            assert len(data["detail"]["errors"]) > 0

    @pytest.mark.asyncio
    async def test_activate_not_found(
        self,
        client: AsyncClient,
        mock_current_user: CurrentUser,
    ) -> None:
        """Test activation returns 404 when campaign not found."""
        from app.shared.exceptions import ValidationError

        with (
            patch("app.campaigns.activation_router.require_campaign_manager") as mock_rbac,
            patch("app.campaigns.activation_router.get_validation_service") as mock_service_dep,
        ):
            mock_rbac.return_value = mock_current_user
            mock_service = AsyncMock()
            mock_service.activate_campaign.side_effect = ValidationError(
                message="Campaign not found",
                field="campaign_id",
            )
            mock_service_dep.return_value = mock_service

            response = await client.post(
                f"/api/campaigns/{uuid4()}/activate",
            )

            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["code"] == "CAMPAIGN_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_activate_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test activation requires authentication."""
        # Without mocking auth, should get 401/403
        response = await client.post(
            f"/api/campaigns/{uuid4()}/activate",
        )

        # Expect auth error (401 or 403 depending on middleware)
        assert response.status_code in [401, 403]