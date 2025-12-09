"""Tests for campaign router validation and activation endpoints."""

from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.campaigns.router import router
from app.campaigns.service import CampaignService
from app.campaigns.validation import ValidationResult
from app.shared.exceptions import NotFoundError, ValidationError, StateTransitionError
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType

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
    """Create mock authenticated user."""
    user = MagicMock()
    user.id = uuid4()
    user.role = "campaign_manager"
    return user

@pytest.fixture
def sample_campaign():
    """Create sample campaign for testing."""
    campaign = MagicMock(spec=Campaign)
    campaign.id = uuid4()
    campaign.name = "Test Campaign"
    campaign.description = "Test description"
    campaign.status = CampaignStatus.DRAFT
    campaign.language = LanguageCode.EN
    campaign.intro_script = "Hello, this is a test survey."
    campaign.question_1_text = "Question 1?"
    campaign.question_1_type = QuestionType.FREE_TEXT
    campaign.question_2_text = "Question 2?"
    campaign.question_2_type = QuestionType.NUMERIC
    campaign.question_3_text = "Question 3?"
    campaign.question_3_type = QuestionType.SCALE
    campaign.max_attempts = 3
    campaign.retry_interval_minutes = 60
    campaign.allowed_call_start_local = time(9, 0)
    campaign.allowed_call_end_local = time(20, 0)
    campaign.email_completed_template_id = None
    campaign.email_refused_template_id = None
    campaign.email_not_reached_template_id = None
    campaign.created_by_user_id = uuid4()
    campaign.created_at = "2024-01-01T00:00:00Z"
    campaign.updated_at = "2024-01-01T00:00:00Z"
    return campaign

@pytest.mark.asyncio
async def test_validate_campaign_success(app, mock_service, mock_user, sample_campaign):
    """Test successful campaign validation endpoint."""
    validation_result = ValidationResult(is_valid=True)
    mock_service.validate_for_activation.return_value = validation_result
    
    with patch("app.campaigns.router.get_campaign_service", return_value=mock_service):
        with patch("app.auth.middleware.get_current_user", return_value=mock_user):
            with patch("app.auth.middleware.require_role", return_value=lambda: None):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test"
                ) as client:
                    response = await client.get(f"/api/campaigns/{sample_campaign.id}/validate")
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["errors"] == []

@pytest.mark.asyncio
async def test_validate_campaign_with_errors(app, mock_service, mock_user, sample_campaign):
    """Test campaign validation endpoint with validation errors."""
    validation_result = ValidationResult(is_valid=False)
    validation_result.add_error("contacts", "No contacts", "NO_CONTACTS")
    validation_result.add_error("question_1_text", "Question 1 is empty", "EMPTY_QUESTION")
    mock_service.validate_for_activation.return_value = validation_result
    
    with patch("app.campaigns.router.get_campaign_service", return_value=mock_service):
        with patch("app.auth.middleware.get_current_user", return_value=mock_user):
            with patch("app.auth.middleware.require_role", return_value=lambda: None):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test"
                ) as client:
                    response = await client.get(f"/api/campaigns/{sample_campaign.id}/validate")
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert len(data["errors"]) == 2

@pytest.mark.asyncio
async def test_validate_campaign_not_found(app, mock_service, mock_user):
    """Test campaign validation endpoint when campaign not found."""
    mock_service.validate_for_activation.side_effect = NotFoundError("Campaign not found")
    
    campaign_id = uuid4()
    
    with patch("app.campaigns.router.get_campaign_service", return_value=mock_service):
        with patch("app.auth.middleware.get_current_user", return_value=mock_user):
            with patch("app.auth.middleware.require_role", return_value=lambda: None):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test"
                ) as client:
                    response = await client.get(f"/api/campaigns/{campaign_id}/validate")
    
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_activate_campaign_success(app, mock_service, mock_user, sample_campaign):
    """Test successful campaign activation endpoint."""
    sample_campaign.status = CampaignStatus.RUNNING
    mock_service.activate_campaign.return_value = sample_campaign
    
    with patch("app.campaigns.router.get_campaign_service", return_value=mock_service):
        with patch("app.auth.middleware.get_current_user", return_value=mock_user):
            with patch("app.auth.middleware.require_role", return_value=lambda: None):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test"
                ) as client:
                    response = await client.post(f"/api/campaigns/{sample_campaign.id}/activate")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["message"] == "Campaign activated successfully"

@pytest.mark.asyncio
async def test_activate_campaign_validation_failure(app, mock_service, mock_user, sample_campaign):
    """Test campaign activation endpoint when validation fails."""
    mock_service.activate_campaign.side_effect = ValidationError("contacts: No contacts")
    
    with patch("app.campaigns.router.get_campaign_service", return_value=mock_service):
        with patch("app.auth.middleware.get_current_user", return_value=mock_user):
            with patch("app.auth.middleware.require_role", return_value=lambda: None):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test"
                ) as client:
                    response = await client.post(f"/api/campaigns/{sample_campaign.id}/activate")
    
    assert response.status_code == 400
    assert "contacts: No contacts" in response.json()["detail"]

@pytest.mark.asyncio
async def test_activate_campaign_not_found(app, mock_service, mock_user):
    """Test campaign activation endpoint when campaign not found."""
    mock_service.activate_campaign.side_effect = NotFoundError("Campaign not found")
    
    campaign_id = uuid4()
    
    with patch("app.campaigns.router.get_campaign_service", return_value=mock_service):
        with patch("app.auth.middleware.get_current_user", return_value=mock_user):
            with patch("app.auth.middleware.require_role", return_value=lambda: None):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test"
                ) as client:
                    response = await client.post(f"/api/campaigns/{campaign_id}/activate")
    
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_activate_campaign_state_transition_error(app, mock_service, mock_user, sample_campaign):
    """Test campaign activation endpoint when state transition is invalid."""
    mock_service.activate_campaign.side_effect = StateTransitionError(
        "Cannot transition from running to running"
    )
    
    with patch("app.campaigns.router.get_campaign_service", return_value=mock_service):
        with patch("app.auth.middleware.get_current_user", return_value=mock_user):
            with patch("app.auth.middleware.require_role", return_value=lambda: None):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test"
                ) as client:
                    response = await client.post(f"/api/campaigns/{sample_campaign.id}/activate")
    
    assert response.status_code == 400