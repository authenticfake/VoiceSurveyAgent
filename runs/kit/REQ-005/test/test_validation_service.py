"""
Unit tests for campaign validation service.

REQ-005: Campaign validation service
"""

from datetime import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.campaigns.models import Campaign, CampaignLanguage, CampaignStatus, QuestionType
from app.campaigns.validation import CampaignValidationService, ValidationResult
from app.shared.exceptions import ValidationError


@pytest.fixture
def mock_campaign_repo() -> AsyncMock:
    """Create mock campaign repository."""
    return AsyncMock()


@pytest.fixture
def mock_contact_repo() -> AsyncMock:
    """Create mock contact repository."""
    return AsyncMock()


@pytest.fixture
def validation_service(
    mock_campaign_repo: AsyncMock,
    mock_contact_repo: AsyncMock,
) -> CampaignValidationService:
    """Create validation service with mocks."""
    return CampaignValidationService(
        campaign_repository=mock_campaign_repo,
        contact_repository=mock_contact_repo,
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


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_initial_state_is_valid(self) -> None:
        """Test that new result is valid."""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []

    def test_add_error_makes_invalid(self) -> None:
        """Test that adding error makes result invalid."""
        result = ValidationResult()
        result.add_error("field", "message")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == {"field": "field", "message": "message"}

    def test_multiple_errors(self) -> None:
        """Test adding multiple errors."""
        result = ValidationResult()
        result.add_error("field1", "message1")
        result.add_error("field2", "message2")
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_errors_returns_copy(self) -> None:
        """Test that errors property returns a copy."""
        result = ValidationResult()
        result.add_error("field", "message")
        errors = result.errors
        errors.append({"field": "new", "message": "new"})
        assert len(result.errors) == 1


class TestCampaignValidationService:
    """Tests for CampaignValidationService."""

    @pytest.mark.asyncio
    async def test_validate_campaign_not_found(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Test validation raises error when campaign not found."""
        mock_campaign_repo.get_by_id.return_value = None
        campaign_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_for_activation(campaign_id)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_zero_contacts(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails when campaign has zero contacts."""
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 0

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert any(e["field"] == "contacts" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_empty_question_1(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails when question 1 is empty."""
        valid_campaign.question_1_text = ""
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert any(e["field"] == "question_1_text" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_empty_question_2(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails when question 2 is empty."""
        valid_campaign.question_2_text = "   "  # Whitespace only
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert any(e["field"] == "question_2_text" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_empty_question_3(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails when question 3 is empty."""
        valid_campaign.question_3_text = None  # type: ignore
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert any(e["field"] == "question_3_text" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_max_attempts_too_low(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails when max_attempts < 1."""
        valid_campaign.max_attempts = 0
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert any(e["field"] == "max_attempts" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_max_attempts_too_high(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails when max_attempts > 5."""
        valid_campaign.max_attempts = 6
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert any(e["field"] == "max_attempts" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_time_window_start_equals_end(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails when start time equals end time."""
        valid_campaign.allowed_call_start_local = time(10, 0)
        valid_campaign.allowed_call_end_local = time(10, 0)
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert any(e["field"] == "time_window" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_time_window_start_after_end(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails when start time is after end time."""
        valid_campaign.allowed_call_start_local = time(20, 0)
        valid_campaign.allowed_call_end_local = time(9, 0)
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert any(e["field"] == "time_window" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_time_window_missing(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation fails when time window is not configured."""
        valid_campaign.allowed_call_start_local = None  # type: ignore
        valid_campaign.allowed_call_end_local = None  # type: ignore
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert any(e["field"] == "time_window" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_all_valid(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation passes when all criteria are met."""
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is True
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_validate_multiple_errors(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test validation collects multiple errors."""
        valid_campaign.question_1_text = ""
        valid_campaign.max_attempts = 10
        valid_campaign.allowed_call_start_local = time(20, 0)
        valid_campaign.allowed_call_end_local = time(9, 0)
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 0

        result = await validation_service.validate_for_activation(valid_campaign.id)

        assert result.is_valid is False
        assert len(result.errors) >= 4  # contacts, question_1, max_attempts, time_window


class TestActivateCampaign:
    """Tests for activate_campaign method."""

    @pytest.mark.asyncio
    async def test_activate_success(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test successful campaign activation."""
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10
        mock_campaign_repo.update.return_value = valid_campaign

        result = await validation_service.activate_campaign(valid_campaign.id)

        assert result.status == CampaignStatus.RUNNING
        mock_campaign_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_validation_fails(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test activation fails when validation fails."""
        valid_campaign.question_1_text = ""
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        with pytest.raises(ValidationError) as exc_info:
            await validation_service.activate_campaign(valid_campaign.id)

        assert exc_info.value.details is not None
        assert len(exc_info.value.details) > 0

    @pytest.mark.asyncio
    async def test_activate_wrong_status(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        valid_campaign: Campaign,
    ) -> None:
        """Test activation fails when campaign is not in draft status."""
        valid_campaign.status = CampaignStatus.RUNNING
        mock_campaign_repo.get_by_id.return_value = valid_campaign
        mock_contact_repo.count_by_campaign.return_value = 10

        with pytest.raises(ValidationError) as exc_info:
            await validation_service.activate_campaign(valid_campaign.id)

        assert "status" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_activate_campaign_not_found(
        self,
        validation_service: CampaignValidationService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Test activation fails when campaign not found."""
        mock_campaign_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            await validation_service.activate_campaign(uuid4())

        assert "not found" in str(exc_info.value).lower()