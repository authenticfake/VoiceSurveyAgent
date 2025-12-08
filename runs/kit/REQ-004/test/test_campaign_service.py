"""Tests for campaign service."""

import pytest
from datetime import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.campaigns.service import CampaignService, VALID_TRANSITIONS, EDITABLE_STATUSES
from app.campaigns.schemas import CampaignCreate, CampaignUpdate
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType
from app.shared.exceptions import NotFoundError, ValidationError, StateTransitionError


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return AsyncMock()


@pytest.fixture
def campaign_service(mock_repository):
    """Create a campaign service with mock repository."""
    return CampaignService(mock_repository)


@pytest.fixture
def sample_campaign():
    """Create a sample campaign."""
    campaign = MagicMock(spec=Campaign)
    campaign.id = uuid4()
    campaign.name = "Test Campaign"
    campaign.status = CampaignStatus.DRAFT
    campaign.language = LanguageCode.EN
    campaign.intro_script = "Test intro script"
    campaign.question_1_text = "Question 1?"
    campaign.question_1_type = QuestionType.FREE_TEXT
    campaign.question_2_text = "Question 2?"
    campaign.question_2_type = QuestionType.FREE_TEXT
    campaign.question_3_text = "Question 3?"
    campaign.question_3_type = QuestionType.FREE_TEXT
    campaign.max_attempts = 3
    campaign.retry_interval_minutes = 60
    campaign.allowed_call_start_local = time(9, 0)
    campaign.allowed_call_end_local = time(20, 0)
    return campaign


class TestCampaignServiceCreate:
    """Tests for campaign creation."""
    
    @pytest.mark.asyncio
    async def test_create_campaign_success(self, campaign_service, mock_repository, sample_campaign):
        """Test successful campaign creation."""
        mock_repository.create.return_value = sample_campaign
        
        data = CampaignCreate(
            name="Test Campaign",
            intro_script="Test intro script",
            question_1_text="Question 1?",
            question_1_type=QuestionType.FREE_TEXT,
            question_2_text="Question 2?",
            question_2_type=QuestionType.FREE_TEXT,
            question_3_text="Question 3?",
            question_3_type=QuestionType.FREE_TEXT,
        )
        user_id = uuid4()
        
        result = await campaign_service.create_campaign(data, user_id)
        
        assert result == sample_campaign
        mock_repository.create.assert_called_once()
        created_campaign = mock_repository.create.call_args[0][0]
        assert created_campaign.status == CampaignStatus.DRAFT
        assert created_campaign.created_by_user_id == user_id


class TestCampaignServiceGet:
    """Tests for getting campaigns."""
    
    @pytest.mark.asyncio
    async def test_get_campaign_success(self, campaign_service, mock_repository, sample_campaign):
        """Test successful campaign retrieval."""
        mock_repository.get_by_id.return_value = sample_campaign
        
        result = await campaign_service.get_campaign(sample_campaign.id)
        
        assert result == sample_campaign
        mock_repository.get_by_id.assert_called_once_with(sample_campaign.id)
    
    @pytest.mark.asyncio
    async def test_get_campaign_not_found(self, campaign_service, mock_repository):
        """Test campaign not found."""
        mock_repository.get_by_id.return_value = None
        campaign_id = uuid4()
        
        with pytest.raises(NotFoundError) as exc_info:
            await campaign_service.get_campaign(campaign_id)
        
        assert str(campaign_id) in str(exc_info.value)


class TestCampaignServiceList:
    """Tests for listing campaigns."""
    
    @pytest.mark.asyncio
    async def test_list_campaigns_success(self, campaign_service, mock_repository, sample_campaign):
        """Test successful campaign listing."""
        mock_repository.list_campaigns.return_value = ([sample_campaign], 1)
        
        campaigns, total = await campaign_service.list_campaigns()
        
        assert len(campaigns) == 1
        assert total == 1
        mock_repository.list_campaigns.assert_called_once_with(
            status=None, page=1, page_size=20
        )
    
    @pytest.mark.asyncio
    async def test_list_campaigns_with_filter(self, campaign_service, mock_repository):
        """Test campaign listing with status filter."""
        mock_repository.list_campaigns.return_value = ([], 0)
        
        await campaign_service.list_campaigns(
            status=CampaignStatus.RUNNING,
            page=2,
            page_size=10,
        )
        
        mock_repository.list_campaigns.assert_called_once_with(
            status=CampaignStatus.RUNNING, page=2, page_size=10
        )


class TestCampaignServiceUpdate:
    """Tests for updating campaigns."""
    
    @pytest.mark.asyncio
    async def test_update_campaign_success(self, campaign_service, mock_repository, sample_campaign):
        """Test successful campaign update."""
        mock_repository.get_by_id.return_value = sample_campaign
        mock_repository.update.return_value = sample_campaign
        
        data = CampaignUpdate(name="Updated Name")
        result = await campaign_service.update_campaign(sample_campaign.id, data)
        
        assert result == sample_campaign
        assert sample_campaign.name == "Updated Name"
    
    @pytest.mark.asyncio
    async def test_update_campaign_not_editable(self, campaign_service, mock_repository, sample_campaign):
        """Test update fails for non-editable status."""
        sample_campaign.status = CampaignStatus.RUNNING
        mock_repository.get_by_id.return_value = sample_campaign
        
        data = CampaignUpdate(name="Updated Name")
        
        with pytest.raises(ValidationError) as exc_info:
            await campaign_service.update_campaign(sample_campaign.id, data)
        
        assert "Cannot update campaign" in str(exc_info.value)


class TestCampaignServiceStatusUpdate:
    """Tests for status updates."""
    
    @pytest.mark.asyncio
    async def test_valid_status_transition(self, campaign_service, mock_repository, sample_campaign):
        """Test valid status transition."""
        mock_repository.get_by_id.return_value = sample_campaign
        mock_repository.update.return_value = sample_campaign
        
        result = await campaign_service.update_status(
            sample_campaign.id, CampaignStatus.RUNNING
        )
        
        assert result.status == CampaignStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_invalid_status_transition(self, campaign_service, mock_repository, sample_campaign):
        """Test invalid status transition."""
        sample_campaign.status = CampaignStatus.COMPLETED
        mock_repository.get_by_id.return_value = sample_campaign
        
        with pytest.raises(StateTransitionError) as exc_info:
            await campaign_service.update_status(
                sample_campaign.id, CampaignStatus.RUNNING
            )
        
        assert "Cannot transition" in str(exc_info.value)
    
    def test_valid_transitions_coverage(self):
        """Test that all statuses have defined transitions."""
        for status in CampaignStatus:
            assert status in VALID_TRANSITIONS


class TestCampaignServiceDelete:
    """Tests for campaign deletion."""
    
    @pytest.mark.asyncio
    async def test_delete_campaign_success(self, campaign_service, mock_repository, sample_campaign):
        """Test successful campaign deletion."""
        mock_repository.get_by_id.return_value = sample_campaign
        sample_campaign.status = CampaignStatus.CANCELLED
        mock_repository.soft_delete.return_value = sample_campaign
        
        result = await campaign_service.delete_campaign(sample_campaign.id)
        
        assert result.status == CampaignStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_delete_completed_campaign_fails(self, campaign_service, mock_repository, sample_campaign):
        """Test that completed campaigns cannot be deleted."""
        sample_campaign.status = CampaignStatus.COMPLETED
        mock_repository.get_by_id.return_value = sample_campaign
        
        with pytest.raises(StateTransitionError) as exc_info:
            await campaign_service.delete_campaign(sample_campaign.id)
        
        assert "Cannot delete campaign" in str(exc_info.value)