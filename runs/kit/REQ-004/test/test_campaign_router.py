"""Tests for campaign API router."""

import pytest
from datetime import time, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.campaigns.router import router, get_campaign_service
from app.campaigns.service import CampaignService
from app.campaigns.schemas import CampaignResponse
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType
from app.shared.exceptions import NotFoundError, ValidationError, StateTransitionError
from app.auth.middleware import CurrentUser
from app.auth.schemas import UserRole


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def mock_service():
    """Create mock campaign service."""
    return AsyncMock(spec=CampaignService)


@pytest.fixture
def mock_user():
    """Create mock current user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.role = UserRole.CAMPAIGN_MANAGER
    return user


@pytest.fixture
def sample_campaign_response():
    """Create sample campaign response data."""
    return {
        "id": str(uuid4()),
        "name": "Test Campaign",
        "description": None,
        "status": CampaignStatus.DRAFT.value,
        "language": LanguageCode.EN.value,
        "intro_script": "Test intro script",
        "question_1_text": "Question 1?",
        "question_1_type": QuestionType.FREE_TEXT.value,
        "question_2_text": "Question 2?",
        "question_2_type": QuestionType.FREE_TEXT.value,
        "question_3_text": "Question 3?",
        "question_3_type": QuestionType.FREE_TEXT.value,
        "max_attempts": 3,
        "retry_interval_minutes": 60,
        "allowed_call_start_local": "09:00:00",
        "allowed_call_end_local": "20:00:00",
        "email_completed_template_id": None,
        "email_refused_template_id": None,
        "email_not_reached_template_id": None,
        "created_by_user_id": str(uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_campaign(sample_campaign_response):
    """Create mock campaign object."""
    campaign = MagicMock(spec=Campaign)
    campaign.id = uuid4()
    campaign.name = sample_campaign_response["name"]
    campaign.description = sample_campaign_response["description"]
    campaign.status = CampaignStatus.DRAFT
    campaign.language = LanguageCode.EN
    campaign.intro_script = sample_campaign_response["intro_script"]
    campaign.question_1_text = sample_campaign_response["question_1_text"]
    campaign.question_1_type = QuestionType.FREE_TEXT
    campaign.question_2_text = sample_campaign_response["question_2_text"]
    campaign.question_2_type = QuestionType.FREE_TEXT
    campaign.question_3_text = sample_campaign_response["question_3_text"]
    campaign.question_3_type = QuestionType.FREE_TEXT
    campaign.max_attempts = 3
    campaign.retry_interval_minutes = 60
    campaign.allowed_call_start_local = time(9, 0)
    campaign.allowed_call_end_local = time(20, 0)
    campaign.email_completed_template_id = None
    campaign.email_refused_template_id = None
    campaign.email_not_reached_template_id = None
    campaign.created_by_user_id = uuid4()
    campaign.created_at = datetime.utcnow()
    campaign.updated_at = datetime.utcnow()
    return campaign


class TestCreateCampaign:
    """Tests for POST /api/campaigns."""
    
    @pytest.mark.asyncio
    async def test_create_campaign_success(self, app, mock_service, mock_user, mock_campaign):
        """Test successful campaign creation."""
        mock_service.create_campaign.return_value = mock_campaign
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        # Mock auth dependencies
        from app.auth.middleware import get_current_user, require_role
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/campaigns",
                json={
                    "name": "Test Campaign",
                    "intro_script": "Test intro script",
                    "question_1_text": "Question 1?",
                    "question_1_type": "free_text",
                    "question_2_text": "Question 2?",
                    "question_2_type": "free_text",
                    "question_3_text": "Question 3?",
                    "question_3_type": "free_text",
                },
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Campaign"
        assert data["status"] == "draft"


class TestListCampaigns:
    """Tests for GET /api/campaigns."""
    
    @pytest.mark.asyncio
    async def test_list_campaigns_success(self, app, mock_service, mock_user, mock_campaign):
        """Test successful campaign listing."""
        mock_service.list_campaigns.return_value = ([mock_campaign], 1)
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/campaigns")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
    
    @pytest.mark.asyncio
    async def test_list_campaigns_with_filter(self, app, mock_service, mock_user):
        """Test campaign listing with status filter."""
        mock_service.list_campaigns.return_value = ([], 0)
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/campaigns?status=running")
        
        assert response.status_code == 200
        mock_service.list_campaigns.assert_called_once()


class TestGetCampaign:
    """Tests for GET /api/campaigns/{id}."""
    
    @pytest.mark.asyncio
    async def test_get_campaign_success(self, app, mock_service, mock_user, mock_campaign):
        """Test successful campaign retrieval."""
        mock_service.get_campaign.return_value = mock_campaign
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(f"/api/campaigns/{mock_campaign.id}")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_campaign_not_found(self, app, mock_service, mock_user):
        """Test campaign not found."""
        mock_service.get_campaign.side_effect = NotFoundError("Campaign not found")
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(f"/api/campaigns/{uuid4()}")
        
        assert response.status_code == 404


class TestUpdateCampaign:
    """Tests for PUT /api/campaigns/{id}."""
    
    @pytest.mark.asyncio
    async def test_update_campaign_success(self, app, mock_service, mock_user, mock_campaign):
        """Test successful campaign update."""
        mock_campaign.name = "Updated Name"
        mock_service.update_campaign.return_value = mock_campaign
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.put(
                f"/api/campaigns/{mock_campaign.id}",
                json={"name": "Updated Name"},
            )
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
    
    @pytest.mark.asyncio
    async def test_update_campaign_validation_error(self, app, mock_service, mock_user):
        """Test update with validation error."""
        mock_service.update_campaign.side_effect = ValidationError("Cannot update")
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.put(
                f"/api/campaigns/{uuid4()}",
                json={"name": "Updated Name"},
            )
        
        assert response.status_code == 400


class TestUpdateCampaignStatus:
    """Tests for PATCH /api/campaigns/{id}/status."""
    
    @pytest.mark.asyncio
    async def test_update_status_success(self, app, mock_service, mock_user, mock_campaign):
        """Test successful status update."""
        mock_campaign.status = CampaignStatus.RUNNING
        mock_service.update_status.return_value = mock_campaign
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/api/campaigns/{mock_campaign.id}/status",
                json={"status": "running"},
            )
        
        assert response.status_code == 200
        assert response.json()["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_update_status_invalid_transition(self, app, mock_service, mock_user):
        """Test invalid status transition."""
        mock_service.update_status.side_effect = StateTransitionError("Invalid transition")
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/api/campaigns/{uuid4()}/status",
                json={"status": "running"},
            )
        
        assert response.status_code == 400


class TestDeleteCampaign:
    """Tests for DELETE /api/campaigns/{id}."""
    
    @pytest.mark.asyncio
    async def test_delete_campaign_success(self, app, mock_service, mock_user, mock_campaign):
        """Test successful campaign deletion."""
        mock_campaign.status = CampaignStatus.CANCELLED
        mock_service.delete_campaign.return_value = mock_campaign
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.delete(f"/api/campaigns/{mock_campaign.id}")
        
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_delete_campaign_state_error(self, app, mock_service, mock_user):
        """Test delete with state transition error."""
        mock_service.delete_campaign.side_effect = StateTransitionError("Cannot delete")
        
        app.dependency_overrides[get_campaign_service] = lambda: mock_service
        
        from app.auth.middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.delete(f"/api/campaigns/{uuid4()}")
        
        assert response.status_code == 400