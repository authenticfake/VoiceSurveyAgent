"""Tests for campaign service activation functionality."""

from datetime import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.campaigns.service import CampaignService
from app.campaigns.validation import CampaignValidationService, ValidationResult, ValidationError as ValError
from app.shared.exceptions import ValidationError, StateTransitionError, NotFoundError
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType

@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_validation_service():
    """Create a mock validation service."""
    service = AsyncMock(spec=CampaignValidationService)
    return service

@pytest.fixture
def sample_campaign():
    """Create a sample campaign for testing."""
    campaign = MagicMock(spec=Campaign)
    campaign.id = uuid4()
    campaign.name = "Test Campaign"
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
    return campaign

@pytest.mark.asyncio
async def test_activate_campaign_success(mock_repository, mock_validation_service, sample_campaign):
    """Test successful campaign activation."""
    mock_repository.get_by_id.return_value = sample_campaign
    mock_validation_service.validate_for_activation.return_value = ValidationResult(is_valid=True)
    mock_repository.update.return_value = sample_campaign
    
    service = CampaignService(mock_repository, mock_validation_service)
    
    result = await service.activate_campaign(sample_campaign.id)
    
    assert result == sample_campaign
    mock_validation_service.validate_for_activation.assert_called_once_with(sample_campaign.id)
    mock_repository.update.assert_called_once()

@pytest.mark.asyncio
async def test_activate_campaign_validation_failure(mock_repository, mock_validation_service, sample_campaign):
    """Test campaign activation fails when validation fails."""
    mock_repository.get_by_id.return_value = sample_campaign
    
    validation_result = ValidationResult(is_valid=False)
    validation_result.add_error("contacts", "No contacts", "NO_CONTACTS")
    mock_validation_service.validate_for_activation.return_value = validation_result
    
    service = CampaignService(mock_repository, mock_validation_service)
    
    with pytest.raises(ValidationError) as exc_info:
        await service.activate_campaign(sample_campaign.id)
    
    assert "contacts: No contacts" in str(exc_info.value)
    mock_repository.update.assert_not_called()

@pytest.mark.asyncio
async def test_activate_campaign_not_found(mock_repository, mock_validation_service):
    """Test campaign activation fails when campaign not found."""
    mock_repository.get_by_id.return_value = None
    
    service = CampaignService(mock_repository, mock_validation_service)
    
    with pytest.raises(NotFoundError):
        await service.activate_campaign(uuid4())

@pytest.mark.asyncio
async def test_validate_for_activation_delegates_to_validation_service(
    mock_repository, mock_validation_service, sample_campaign
):
    """Test that validate_for_activation delegates to validation service."""
    mock_repository.get_by_id.return_value = sample_campaign
    expected_result = ValidationResult(is_valid=True)
    mock_validation_service.validate_for_activation.return_value = expected_result
    
    service = CampaignService(mock_repository, mock_validation_service)
    
    result = await service.validate_for_activation(sample_campaign.id)
    
    assert result == expected_result
    mock_validation_service.validate_for_activation.assert_called_once_with(sample_campaign.id)

@pytest.mark.asyncio
async def test_activate_campaign_transitions_to_running(mock_repository, mock_validation_service, sample_campaign):
    """Test that activation transitions campaign to running status."""
    mock_repository.get_by_id.return_value = sample_campaign
    mock_validation_service.validate_for_activation.return_value = ValidationResult(is_valid=True)
    
    async def update_side_effect(campaign):
        campaign.status = CampaignStatus.RUNNING
        return campaign
    
    mock_repository.update.side_effect = update_side_effect
    
    service = CampaignService(mock_repository, mock_validation_service)
    
    result = await service.activate_campaign(sample_campaign.id)
    
    assert sample_campaign.status == CampaignStatus.RUNNING