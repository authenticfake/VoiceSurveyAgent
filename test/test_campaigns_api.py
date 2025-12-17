"""
API integration tests for campaign endpoints.

REQ-004: Campaign CRUD API
"""

from datetime import time
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
import pytest_asyncio

from app.auth.middleware import AuthenticatedUser
from app.campaigns.models import CampaignStatus, CampaignLanguage, QuestionType
from app.main import app


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_current_user() -> AuthenticatedUser:
    """Create a mock authenticated user."""
    return AuthenticatedUser(
        id=uuid4(),
        oidc_sub="oidc|test123",
        email="test@example.com",
        name="Test User",
        role="campaign_manager",
    )


@pytest.fixture
def mock_admin_user() -> AuthenticatedUser:
    """Create a mock admin user."""
    return AuthenticatedUser(
        id=uuid4(),
        oidc_sub="oidc|admin123",
        email="admin@example.com",
        name="Admin User",
        role="admin",
    )


@pytest.fixture
def mock_viewer_user() -> AuthenticatedUser:
    """Create a mock viewer user."""
    return AuthenticatedUser(
        id=uuid4(),
        oidc_sub="oidc|viewer123",
        email="viewer@example.com",
        name="Viewer User",
        role="viewer",
    )


@pytest.fixture
def sample_campaign_data() -> dict:
    """Create sample campaign data for API requests."""
    return {
        "name": "Test Campaign",
        "description": "Test description",
        "language": "en",
        "intro_script": "Hello, this is a test survey from Example Corp...",
        "question_1_text": "How satisfied are you with our service?",
        "question_1_type": "scale",
        "question_2_text": "What could we improve?",
        "question_2_type": "free_text",
        "question_3_text": "How likely are you to recommend us?",
        "question_3_type": "numeric",
        "max_attempts": 3,
        "retry_interval_minutes": 60,
        "allowed_call_start_local": "09:00:00",
        "allowed_call_end_local": "18:00:00",
    }


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ============================================================================
# Helper Functions
# ============================================================================


def patch_auth(user: AuthenticatedUser):
    """Create a patch for authentication middleware."""
    return patch(
        "app.auth.middleware.get_current_user",
        return_value=user,
    )


def patch_db_session():
    """Create a patch for database session."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = AsyncMock()
    return patch(
        "app.shared.database.get_db_session",
        return_value=mock_session,
    )


# ============================================================================
# Create Campaign Tests
# ============================================================================


class TestCreateCampaign:
    """Tests for POST /api/campaigns endpoint."""

    @pytest.mark.asyncio
    async def test_create_campaign_success(
        self,
        async_client: AsyncClient,
        mock_current_user: AuthenticatedUser,
        sample_campaign_data: dict,
    ) -> None:
        """Test successful campaign creation."""
        with patch_auth(mock_current_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            # Setup mock service
            mock_service = AsyncMock()
            mock_campaign = AsyncMock()
            mock_campaign.id = uuid4()
            mock_campaign.name = sample_campaign_data["name"]
            mock_campaign.description = sample_campaign_data["description"]
            mock_campaign.status = CampaignStatus.DRAFT
            mock_campaign.language = CampaignLanguage.EN
            mock_campaign.intro_script = sample_campaign_data["intro_script"]
            mock_campaign.question_1_text = sample_campaign_data["question_1_text"]
            mock_campaign.question_1_type = QuestionType.SCALE
            mock_campaign.question_2_text = sample_campaign_data["question_2_text"]
            mock_campaign.question_2_type = QuestionType.FREE_TEXT
            mock_campaign.question_3_text = sample_campaign_data["question_3_text"]
            mock_campaign.question_3_type = QuestionType.NUMERIC
            mock_campaign.max_attempts = sample_campaign_data["max_attempts"]
            mock_campaign.retry_interval_minutes = sample_campaign_data["retry_interval_minutes"]
            mock_campaign.allowed_call_start_local = time(9, 0)
            mock_campaign.allowed_call_end_local = time(18, 0)
            mock_campaign.email_completed_template_id = None
            mock_campaign.email_refused_template_id = None
            mock_campaign.email_not_reached_template_id = None
            mock_campaign.created_by_user_id = mock_current_user.id
            mock_campaign.created_at = "2024-01-01T00:00:00Z"
            mock_campaign.updated_at = "2024-01-01T00:00:00Z"
            
            mock_service.create_campaign.return_value = mock_campaign
            mock_service_dep.return_value = mock_service

            response = await async_client.post(
                "/api/campaigns",
                json=sample_campaign_data,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == sample_campaign_data["name"]
            assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_campaign_validation_error(
        self,
        async_client: AsyncClient,
        mock_current_user: AuthenticatedUser,
    ) -> None:
        """Test campaign creation with invalid data."""
        with patch_auth(mock_current_user):
            invalid_data = {
                "name": "",  # Empty name
                "intro_script": "Hello...",
                "question_1_text": "Q1?",
                "question_1_type": "scale",
                "question_2_text": "Q2?",
                "question_2_type": "free_text",
                "question_3_text": "Q3?",
                "question_3_type": "numeric",
                "allowed_call_start_local": "09:00:00",
                "allowed_call_end_local": "18:00:00",
            }

            response = await async_client.post(
                "/api/campaigns",
                json=invalid_data,
            )

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_time_window(
        self,
        async_client: AsyncClient,
        mock_current_user: AuthenticatedUser,
        sample_campaign_data: dict,
    ) -> None:
        """Test campaign creation with invalid time window."""
        with patch_auth(mock_current_user):
            sample_campaign_data["allowed_call_start_local"] = "18:00:00"
            sample_campaign_data["allowed_call_end_local"] = "09:00:00"

            response = await async_client.post(
                "/api/campaigns",
                json=sample_campaign_data,
            )

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_campaign_viewer_forbidden(
        self,
        async_client: AsyncClient,
        mock_viewer_user: AuthenticatedUser,
        sample_campaign_data: dict,
    ) -> None:
        """Test that viewers cannot create campaigns."""
        with patch_auth(mock_viewer_user):
            response = await async_client.post(
                "/api/campaigns",
                json=sample_campaign_data,
            )

            assert response.status_code == 403


# ============================================================================
# List Campaigns Tests
# ============================================================================


class TestListCampaigns:
    """Tests for GET /api/campaigns endpoint."""

    @pytest.mark.asyncio
    async def test_list_campaigns_success(
        self,
        async_client: AsyncClient,
        mock_viewer_user: AuthenticatedUser,
    ) -> None:
        """Test successful campaign list retrieval."""
        with patch_auth(mock_viewer_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            mock_service = AsyncMock()
            mock_campaign = AsyncMock()
            mock_campaign.id = uuid4()
            mock_campaign.name = "Test Campaign"
            mock_campaign.description = "Description"
            mock_campaign.status = CampaignStatus.DRAFT
            mock_campaign.language = CampaignLanguage.EN
            mock_campaign.created_at = "2024-01-01T00:00:00Z"
            mock_campaign.updated_at = "2024-01-01T00:00:00Z"
            
            mock_service.list_campaigns.return_value = ([mock_campaign], 1)
            mock_service_dep.return_value = mock_service

            response = await async_client.get("/api/campaigns")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "meta" in data
            assert data["meta"]["total"] == 1

    @pytest.mark.asyncio
    async def test_list_campaigns_with_status_filter(
        self,
        async_client: AsyncClient,
        mock_viewer_user: AuthenticatedUser,
    ) -> None:
        """Test campaign list with status filter."""
        with patch_auth(mock_viewer_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            mock_service = AsyncMock()
            mock_service.list_campaigns.return_value = ([], 0)
            mock_service_dep.return_value = mock_service

            response = await async_client.get(
                "/api/campaigns",
                params={"status": "running"},
            )

            assert response.status_code == 200
            mock_service.list_campaigns.assert_called_once()
            call_args = mock_service.list_campaigns.call_args
            assert call_args.kwargs["status"] == CampaignStatus.RUNNING

    @pytest.mark.asyncio
    async def test_list_campaigns_pagination(
        self,
        async_client: AsyncClient,
        mock_viewer_user: AuthenticatedUser,
    ) -> None:
        """Test campaign list pagination."""
        with patch_auth(mock_viewer_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            mock_service = AsyncMock()
            mock_service.list_campaigns.return_value = ([], 0)
            mock_service_dep.return_value = mock_service

            response = await async_client.get(
                "/api/campaigns",
                params={"page": 2, "page_size": 10},
            )

            assert response.status_code == 200
            mock_service.list_campaigns.assert_called_once()
            call_args = mock_service.list_campaigns.call_args
            assert call_args.kwargs["page"] == 2
            assert call_args.kwargs["page_size"] == 10


# ============================================================================
# Get Campaign Tests
# ============================================================================


class TestGetCampaign:
    """Tests for GET /api/campaigns/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_campaign_success(
        self,
        async_client: AsyncClient,
        mock_viewer_user: AuthenticatedUser,
    ) -> None:
        """Test successful campaign retrieval."""
        campaign_id = uuid4()
        
        with patch_auth(mock_viewer_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            mock_service = AsyncMock()
            mock_campaign = AsyncMock()
            mock_campaign.id = campaign_id
            mock_campaign.name = "Test Campaign"
            mock_campaign.description = "Description"
            mock_campaign.status = CampaignStatus.DRAFT
            mock_campaign.language = CampaignLanguage.EN
            mock_campaign.intro_script = "Hello..."
            mock_campaign.question_1_text = "Q1?"
            mock_campaign.question_1_type = QuestionType.SCALE
            mock_campaign.question_2_text = "Q2?"
            mock_campaign.question_2_type = QuestionType.FREE_TEXT
            mock_campaign.question_3_text = "Q3?"
            mock_campaign.question_3_type = QuestionType.NUMERIC
            mock_campaign.max_attempts = 3
            mock_campaign.retry_interval_minutes = 60
            mock_campaign.allowed_call_start_local = time(9, 0)
            mock_campaign.allowed_call_end_local = time(18, 0)
            mock_campaign.email_completed_template_id = None
            mock_campaign.email_refused_template_id = None
            mock_campaign.email_not_reached_template_id = None
            mock_campaign.created_by_user_id = uuid4()
            mock_campaign.created_at = "2024-01-01T00:00:00Z"
            mock_campaign.updated_at = "2024-01-01T00:00:00Z"
            
            mock_service.get_campaign.return_value = mock_campaign
            mock_service_dep.return_value = mock_service

            response = await async_client.get(f"/api/campaigns/{campaign_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(campaign_id)

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(
        self,
        async_client: AsyncClient,
        mock_viewer_user: AuthenticatedUser,
    ) -> None:
        """Test campaign not found error."""
        campaign_id = uuid4()
        
        with patch_auth(mock_viewer_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            from app.shared.exceptions import CampaignNotFoundError
            
            mock_service = AsyncMock()
            mock_service.get_campaign.side_effect = CampaignNotFoundError(campaign_id)
            mock_service_dep.return_value = mock_service

            response = await async_client.get(f"/api/campaigns/{campaign_id}")

            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["code"] == "CAMPAIGN_NOT_FOUND"


# ============================================================================
# Update Campaign Tests
# ============================================================================


class TestUpdateCampaign:
    """Tests for PUT /api/campaigns/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_campaign_success(
        self,
        async_client: AsyncClient,
        mock_current_user: AuthenticatedUser,
    ) -> None:
        """Test successful campaign update."""
        campaign_id = uuid4()
        
        with patch_auth(mock_current_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            mock_service = AsyncMock()
            mock_campaign = AsyncMock()
            mock_campaign.id = campaign_id
            mock_campaign.name = "Updated Name"
            mock_campaign.description = "Updated description"
            mock_campaign.status = CampaignStatus.DRAFT
            mock_campaign.language = CampaignLanguage.EN
            mock_campaign.intro_script = "Hello..."
            mock_campaign.question_1_text = "Q1?"
            mock_campaign.question_1_type = QuestionType.SCALE
            mock_campaign.question_2_text = "Q2?"
            mock_campaign.question_2_type = QuestionType.FREE_TEXT
            mock_campaign.question_3_text = "Q3?"
            mock_campaign.question_3_type = QuestionType.NUMERIC
            mock_campaign.max_attempts = 3
            mock_campaign.retry_interval_minutes = 60
            mock_campaign.allowed_call_start_local = time(9, 0)
            mock_campaign.allowed_call_end_local = time(18, 0)
            mock_campaign.email_completed_template_id = None
            mock_campaign.email_refused_template_id = None
            mock_campaign.email_not_reached_template_id = None
            mock_campaign.created_by_user_id = uuid4()
            mock_campaign.created_at = "2024-01-01T00:00:00Z"
            mock_campaign.updated_at = "2024-01-01T00:00:00Z"
            
            mock_service.update_campaign.return_value = mock_campaign
            mock_service_dep.return_value = mock_service

            response = await async_client.put(
                f"/api/campaigns/{campaign_id}",
                json={"name": "Updated Name", "description": "Updated description"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_campaign_viewer_forbidden(
        self,
        async_client: AsyncClient,
        mock_viewer_user: AuthenticatedUser,
    ) -> None:
        """Test that viewers cannot update campaigns."""
        campaign_id = uuid4()
        
        with patch_auth(mock_viewer_user):
            response = await async_client.put(
                f"/api/campaigns/{campaign_id}",
                json={"name": "Updated Name"},
            )

            assert response.status_code == 403


# ============================================================================
# Delete Campaign Tests
# ============================================================================


class TestDeleteCampaign:
    """Tests for DELETE /api/campaigns/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_campaign_success(
        self,
        async_client: AsyncClient,
        mock_current_user: AuthenticatedUser,
    ) -> None:
        """Test successful campaign deletion."""
        campaign_id = uuid4()
        
        with patch_auth(mock_current_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            mock_service = AsyncMock()
            mock_service.delete_campaign.return_value = None
            mock_service_dep.return_value = mock_service

            response = await async_client.delete(f"/api/campaigns/{campaign_id}")

            assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_campaign_not_found(
        self,
        async_client: AsyncClient,
        mock_current_user: AuthenticatedUser,
    ) -> None:
        """Test delete campaign not found error."""
        campaign_id = uuid4()
        
        with patch_auth(mock_current_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            from app.shared.exceptions import CampaignNotFoundError
            
            mock_service = AsyncMock()
            mock_service.delete_campaign.side_effect = CampaignNotFoundError(campaign_id)
            mock_service_dep.return_value = mock_service

            response = await async_client.delete(f"/api/campaigns/{campaign_id}")

            assert response.status_code == 404


# ============================================================================
# Status Transition Tests
# ============================================================================


class TestStatusTransition:
    """Tests for POST /api/campaigns/{id}/status endpoint."""

    @pytest.mark.asyncio
    async def test_transition_status_success(
        self,
        async_client: AsyncClient,
        mock_current_user: AuthenticatedUser,
    ) -> None:
        """Test successful status transition."""
        campaign_id = uuid4()
        
        with patch_auth(mock_current_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            mock_service = AsyncMock()
            mock_campaign = AsyncMock()
            mock_campaign.id = campaign_id
            mock_campaign.name = "Test Campaign"
            mock_campaign.description = "Description"
            mock_campaign.status = CampaignStatus.RUNNING
            mock_campaign.language = CampaignLanguage.EN
            mock_campaign.intro_script = "Hello..."
            mock_campaign.question_1_text = "Q1?"
            mock_campaign.question_1_type = QuestionType.SCALE
            mock_campaign.question_2_text = "Q2?"
            mock_campaign.question_2_type = QuestionType.FREE_TEXT
            mock_campaign.question_3_text = "Q3?"
            mock_campaign.question_3_type = QuestionType.NUMERIC
            mock_campaign.max_attempts = 3
            mock_campaign.retry_interval_minutes = 60
            mock_campaign.allowed_call_start_local = time(9, 0)
            mock_campaign.allowed_call_end_local = time(18, 0)
            mock_campaign.email_completed_template_id = None
            mock_campaign.email_refused_template_id = None
            mock_campaign.email_not_reached_template_id = None
            mock_campaign.created_by_user_id = uuid4()
            mock_campaign.created_at = "2024-01-01T00:00:00Z"
            mock_campaign.updated_at = "2024-01-01T00:00:00Z"
            
            mock_service.transition_status.return_value = mock_campaign
            mock_service_dep.return_value = mock_service

            response = await async_client.post(
                f"/api/campaigns/{campaign_id}/status",
                json={"status": "running"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_transition_status_invalid(
        self,
        async_client: AsyncClient,
        mock_current_user: AuthenticatedUser,
    ) -> None:
        """Test invalid status transition."""
        campaign_id = uuid4()
        
        with patch_auth(mock_current_user), \
             patch("app.campaigns.router.get_campaign_service") as mock_service_dep:
            
            from app.shared.exceptions import InvalidStatusTransitionError
            from app.campaigns.models import CampaignStatus
            
            mock_service = AsyncMock()
            mock_service.transition_status.side_effect = InvalidStatusTransitionError(
                current_status=CampaignStatus.DRAFT,
                target_status=CampaignStatus.COMPLETED,
                valid_transitions={CampaignStatus.SCHEDULED, CampaignStatus.RUNNING, CampaignStatus.CANCELLED},
            )
            mock_service_dep.return_value = mock_service

            response = await async_client.post(
                f"/api/campaigns/{campaign_id}/status",
                json={"status": "completed"},
            )

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["code"] == "INVALID_STATUS_TRANSITION"
            assert "valid_transitions" in data["detail"]