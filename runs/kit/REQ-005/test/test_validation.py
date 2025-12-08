"""Tests for campaign validation service."""

import pytest
from datetime import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.campaigns.validation import CampaignValidationService, ValidationResult
from app.campaigns.repository import CampaignRepository
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType

@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create mock repository."""
    return AsyncMock(spec=CampaignRepository)

@pytest.fixture
def validation_service(mock_repository: AsyncMock) -> CampaignValidationService:
    """Create validation service with mock repository."""
    return CampaignValidationService(mock_repository)

@pytest.fixture
def valid_campaign() -> Campaign:
    """Create a valid campaign for testing."""
    campaign = MagicMock(spec=Campaign)
    campaign.id = uuid4()
    campaign.status = CampaignStatus.DRAFT
    campaign.question_1_text = "What is your satisfaction level?"
    campaign.question_2_text = "Would you recommend us?"
    campaign.question_3_text = "Any additional feedback?"
    campaign.max_attempts = 3
    campaign.allowed_call_start_local = time(9, 0)
    campaign.allowed_call_end_local = time(20, 0)
    return campaign

class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_success_creates_valid_result(self) -> None:
        """Test success factory method."""
        result = ValidationResult.success()
        assert result.is_valid is True
        assert result.errors == []
    
    def test_failure_creates_invalid_result(self) -> None:
        """Test failure factory method."""
        errors = ["Error 1", "Error 2"]
        result = ValidationResult.failure(errors)
        assert result.is_valid is False
        assert result.errors == errors

class TestCampaignValidationService:
    """Tests for CampaignValidationService."""
    
    @pytest.mark.asyncio
    async def test_validate_campaign_not_found(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test validation raises NotFoundError for missing campaign."""
        campaign_id = uuid4()
        mock_repository.get_by_id.return_value = None
        
        with pytest.raises(NotFoundError):
            await validation_service.validate_for_activation(campaign_id)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_not_in_draft_status(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails if campaign is not in draft status."""
        valid_campaign.status = CampaignStatus.RUNNING
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert any("draft status" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_zero_contacts(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails if campaign has zero contacts."""
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 0
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert any("at least one contact" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_empty_question_1(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails if question 1 is empty."""
        valid_campaign.question_1_text = ""
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert any("Question 1" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_empty_question_2(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails if question 2 is empty."""
        valid_campaign.question_2_text = "   "  # Whitespace only
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert any("Question 2" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_empty_question_3(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails if question 3 is empty."""
        valid_campaign.question_3_text = None
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert any("Question 3" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_invalid_max_attempts_too_low(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails if max_attempts is less than 1."""
        valid_campaign.max_attempts = 0
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert any("between 1 and 5" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_invalid_max_attempts_too_high(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails if max_attempts is greater than 5."""
        valid_campaign.max_attempts = 6
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert any("between 1 and 5" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_invalid_time_window_equal(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails if start time equals end time."""
        valid_campaign.allowed_call_start_local = time(10, 0)
        valid_campaign.allowed_call_end_local = time(10, 0)
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert any("before end time" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_invalid_time_window_reversed(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails if start time is after end time."""
        valid_campaign.allowed_call_start_local = time(20, 0)
        valid_campaign.allowed_call_end_local = time(9, 0)
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert any("before end time" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_campaign_multiple_errors(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation collects all errors."""
        valid_campaign.question_1_text = ""
        valid_campaign.question_2_text = ""
        valid_campaign.max_attempts = 10
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 0
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is False
        assert len(result.errors) >= 4  # At least 4 errors
    
    @pytest.mark.asyncio
    async def test_validate_campaign_success(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation passes for valid campaign."""
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is True
        assert result.errors == []
    
    @pytest.mark.asyncio
    async def test_activate_campaign_validation_fails(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test activation raises ValidationError when validation fails."""
        valid_campaign.question_1_text = ""
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.activate_campaign(valid_campaign.id)
        
        assert "validation failed" in exc_info.value.message.lower()
        assert "errors" in exc_info.value.details
    
    @pytest.mark.asyncio
    async def test_activate_campaign_success(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test successful campaign activation."""
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        await validation_service.activate_campaign(valid_campaign.id)
        
        mock_repository.update_status.assert_called_once_with(
            valid_campaign.id,
            CampaignStatus.RUNNING,
        )

class TestValidationEdgeCases:
    """Edge case tests for validation."""
    
    @pytest.mark.asyncio
    async def test_validate_campaign_with_min_valid_attempts(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation passes with minimum valid attempts (1)."""
        valid_campaign.max_attempts = 1
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_campaign_with_max_valid_attempts(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation passes with maximum valid attempts (5)."""
        valid_campaign.max_attempts = 5
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_campaign_with_single_contact(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation passes with exactly one contact."""
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 1
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_campaign_time_window_one_minute_apart(
        self,
        validation_service: CampaignValidationService,
        mock_repository: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation passes with time window one minute apart."""
        valid_campaign.allowed_call_start_local = time(9, 0)
        valid_campaign.allowed_call_end_local = time(9, 1)
        mock_repository.get_by_id.return_value = valid_campaign
        mock_repository.get_contact_count.return_value = 10
        
        result = await validation_service.validate_for_activation(valid_campaign.id)
        
        assert result.is_valid is True