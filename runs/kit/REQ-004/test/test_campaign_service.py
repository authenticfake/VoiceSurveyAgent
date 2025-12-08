"""Tests for Campaign service business logic."""

import pytest
from datetime import time
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.campaigns.service import CampaignService
from app.campaigns.schemas import CampaignCreate, CampaignUpdate
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType
from app.shared.exceptions import (
    NotFoundError,
    ValidationError,
    StateTransitionError,
)


@pytest.fixture
def mock_repository():
    """Create mock campaign repository."""
    return AsyncMock()


@pytest.fixture
def campaign_service(mock_repository):
    """Create campaign service with mock repository."""
    return CampaignService(repository=mock_repository)


@pytest.fixture
def sample_campaign():
    """Create sample campaign object."""
    campaign = MagicMock(spec=Campaign)
    campaign.id = uuid4()
    campaign.name = "Test Campaign"
    campaign.status = CampaignStatus.DRAFT
    campaign.created_by_user_id = uuid4()
    campaign.language = LanguageCode.EN
    campaign.intro_script = "Test intro script"
    campaign.question_1_text = "Question 1"
    campaign.question_1_type = QuestionType.FREE_TEXT
    campaign.question_2_text = "Question 2"
    campaign.question_2_type = QuestionType.NUMERIC
    campaign.question_3_text = "Question 3"
    campaign.question_3_type = QuestionType.SCALE
    campaign.max_attempts = 3
    campaign.retry_interval_minutes = 60
    campaign.allowed_call_start_local = time(9, 0)
    campaign.allowed_call_end_local = time(20, 0)
    return campaign


@pytest.mark.asyncio
async def test_create_campaign_success(campaign_service, mock_repository):
    """Test successful campaign creation."""
    user_id = uuid4()
    campaign_data = CampaignCreate(
        name="New Campaign",
        language=LanguageCode.EN,
        intro_script="Hello, this is a survey",
        question_1_text="Question 1",
        question_1_type=QuestionType.FREE_TEXT,
        question_2_text="Question 2",
        question_2_type=QuestionType.NUMERIC,
        question_3_text="Question 3",
        question_3_type=QuestionType.SCALE,
    )
    
    mock_campaign = MagicMock()
    mock_campaign.id = uuid4()
    mock_repository.create.return_value = mock_campaign
    
    result = await campaign_service.create_campaign(campaign_data, user_id)
    
    assert mock_repository.create.called
    assert result.id == mock_campaign.id


@pytest.mark.asyncio
async def test_get_campaign_not_found(campaign_service, mock_repository):
    """Test getting non-existent campaign raises NotFoundError."""
    campaign_id = uuid4()
    mock_repository.get_by_id.return_value = None
    
    with pytest.raises(NotFoundError):
        await campaign_service.get_campaign(campaign_id)


@pytest.mark.asyncio
async def test_update_campaign_invalid_status(campaign_service, mock_repository, sample_campaign):
    """Test updating campaign in invalid status raises ValidationError."""
    sample_campaign.status = CampaignStatus.RUNNING
    mock_repository.get_by_id.return_value = sample_campaign
    
    update_data = CampaignUpdate(name="Updated Name")
    
    with pytest.raises(ValidationError):
        await campaign_service.update_campaign(sample_campaign.id, update_data)


@pytest.mark.asyncio
async def test_valid_status_transition(campaign_service, mock_repository, sample_campaign):
    """Test valid status transition from draft to running."""
    sample_campaign.status = CampaignStatus.DRAFT
    mock_repository.get_by_id.return_value = sample_campaign
    mock_repository.update_status.return_value = sample_campaign
    
    result = await campaign_service.transition_status(
        sample_campaign.id,
        CampaignStatus.RUNNING
    )
    
    assert mock_repository.update_status.called
    assert result.id == sample_campaign.id


@pytest.mark.asyncio
async def test_invalid_status_transition(campaign_service, mock_repository, sample_campaign):
    """Test invalid status transition raises StateTransitionError."""
    sample_campaign.status = CampaignStatus.COMPLETED
    mock_repository.get_by_id.return_value = sample_campaign
    
    with pytest.raises(StateTransitionError):
        await campaign_service.transition_status(
            sample_campaign.id,
            CampaignStatus.DRAFT
        )


@pytest.mark.asyncio
async def test_delete_running_campaign_fails(campaign_service, mock_repository, sample_campaign):
    """Test deleting running campaign raises ValidationError."""
    sample_campaign.status = CampaignStatus.RUNNING
    mock_repository.get_by_id.return_value = sample_campaign
    
    with pytest.raises(ValidationError):
        await campaign_service.delete_campaign(sample_campaign.id)


@pytest.mark.asyncio
async def test_list_campaigns_with_filters(campaign_service, mock_repository):
    """Test listing campaigns with status filter."""
    mock_campaigns = [MagicMock() for _ in range(3)]
    mock_repository.get_list.return_value = (mock_campaigns, 3)
    
    result = await campaign_service.list_campaigns(
        status=CampaignStatus.DRAFT,
        page=1,
        page_size=10
    )
    
    assert len(result.campaigns) == 3
    assert result.total == 3
    assert result.page == 1
    assert result.page_size == 10
    mock_repository.get_list.assert_called_once_with(
        status=CampaignStatus.DRAFT,
        user_id=None,
        offset=0,
        limit=10
    )