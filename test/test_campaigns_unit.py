"""
Unit tests for campaign service and repository.

REQ-004: Campaign CRUD API
"""

from datetime import time
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.campaigns.models import Campaign, CampaignStatus, CampaignLanguage, QuestionType, VALID_STATUS_TRANSITIONS
from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import CampaignCreate, CampaignUpdate
from app.campaigns.service import CampaignService
from app.shared.exceptions import (
    CampaignNotFoundError,
    InvalidStatusTransitionError,
    ValidationError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create a mock campaign repository."""
    return AsyncMock(spec=CampaignRepository)


@pytest.fixture
def campaign_service(mock_repository: AsyncMock) -> CampaignService:
    """Create campaign service with mock repository."""
    return CampaignService(repository=mock_repository)


@pytest.fixture
def sample_campaign() -> Campaign:
    """Create a sample campaign for testing."""
    return Campaign(
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
        question_3_text="How likely to recommend?",
        question_3_type=QuestionType.NUMERIC,
        max_attempts=3,
        retry_interval_minutes=60,
        allowed_call_start_local=time(9, 0),
        allowed_call_end_local=time(18, 0),
        created_by_user_id=uuid4(),
    )


@pytest.fixture
def sample_create_data() -> CampaignCreate:
    """Create sample campaign creation data."""
    return CampaignCreate(
        name="New Campaign",
        description="New campaign description",
        language=CampaignLanguage.EN,
        intro_script="Hello, this is a survey...",
        question_1_text="Question 1?",
        question_1_type=QuestionType.SCALE,
        question_2_text="Question 2?",
        question_2_type=QuestionType.FREE_TEXT,
        question_3_text="Question 3?",
        question_3_type=QuestionType.NUMERIC,
        max_attempts=3,
        retry_interval_minutes=60,
        allowed_call_start_local=time(9, 0),
        allowed_call_end_local=time(18, 0),
    )


# ============================================================================
# Model Tests
# ============================================================================


class TestCampaignModel:
    """Tests for Campaign model."""

    def test_can_transition_to_valid(self, sample_campaign: Campaign) -> None:
        """Test valid status transitions."""
        # Draft can transition to scheduled, running, or cancelled
        assert sample_campaign.can_transition_to(CampaignStatus.SCHEDULED)
        assert sample_campaign.can_transition_to(CampaignStatus.RUNNING)
        assert sample_campaign.can_transition_to(CampaignStatus.CANCELLED)

    def test_can_transition_to_invalid(self, sample_campaign: Campaign) -> None:
        """Test invalid status transitions."""
        # Draft cannot transition to paused or completed
        assert not sample_campaign.can_transition_to(CampaignStatus.PAUSED)
        assert not sample_campaign.can_transition_to(CampaignStatus.COMPLETED)

    def test_terminal_states_no_transitions(self) -> None:
        """Test that terminal states have no valid transitions."""
        assert VALID_STATUS_TRANSITIONS[CampaignStatus.COMPLETED] == set()
        assert VALID_STATUS_TRANSITIONS[CampaignStatus.CANCELLED] == set()

    def test_running_can_pause_complete_cancel(self) -> None:
        """Test running campaign transitions."""
        valid = VALID_STATUS_TRANSITIONS[CampaignStatus.RUNNING]
        assert CampaignStatus.PAUSED in valid
        assert CampaignStatus.COMPLETED in valid
        assert CampaignStatus.CANCELLED in valid


# ============================================================================
# Service Tests
# ============================================================================


class TestCampaignService:
    """Tests for CampaignService."""

    @pytest.mark.asyncio
    async def test_get_campaign_success(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
        sample_campaign: Campaign,
    ) -> None:
        """Test successful campaign retrieval."""
        mock_repository.get_by_id.return_value = sample_campaign

        result = await campaign_service.get_campaign(sample_campaign.id)

        assert result == sample_campaign
        mock_repository.get_by_id.assert_called_once_with(sample_campaign.id)

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test campaign not found error."""
        campaign_id = uuid4()
        mock_repository.get_by_id.return_value = None

        with pytest.raises(CampaignNotFoundError) as exc_info:
            await campaign_service.get_campaign(campaign_id)

        assert exc_info.value.campaign_id == campaign_id

    @pytest.mark.asyncio
    async def test_list_campaigns(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
        sample_campaign: Campaign,
    ) -> None:
        """Test campaign list retrieval."""
        mock_repository.get_list.return_value = ([sample_campaign], 1)

        campaigns, total = await campaign_service.list_campaigns(
            status=CampaignStatus.DRAFT,
            page=1,
            page_size=20,
        )

        assert len(campaigns) == 1
        assert total == 1
        mock_repository.get_list.assert_called_once_with(
            status=CampaignStatus.DRAFT,
            page=1,
            page_size=20,
        )

    @pytest.mark.asyncio
    async def test_create_campaign(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
        sample_create_data: CampaignCreate,
    ) -> None:
        """Test campaign creation."""
        user_id = uuid4()
        created_campaign = Campaign(
            id=uuid4(),
            name=sample_create_data.name,
            status=CampaignStatus.DRAFT,
            language=sample_create_data.language,
            intro_script=sample_create_data.intro_script,
            question_1_text=sample_create_data.question_1_text,
            question_1_type=sample_create_data.question_1_type,
            question_2_text=sample_create_data.question_2_text,
            question_2_type=sample_create_data.question_2_type,
            question_3_text=sample_create_data.question_3_text,
            question_3_type=sample_create_data.question_3_type,
            max_attempts=sample_create_data.max_attempts,
            retry_interval_minutes=sample_create_data.retry_interval_minutes,
            allowed_call_start_local=sample_create_data.allowed_call_start_local,
            allowed_call_end_local=sample_create_data.allowed_call_end_local,
            created_by_user_id=user_id,
        )
        mock_repository.create.return_value = created_campaign

        result = await campaign_service.create_campaign(
            data=sample_create_data,
            created_by_user_id=user_id,
        )

        assert result.status == CampaignStatus.DRAFT
        assert result.name == sample_create_data.name
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_campaign_draft_status(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
        sample_campaign: Campaign,
    ) -> None:
        """Test updating campaign in draft status."""
        mock_repository.get_by_id.return_value = sample_campaign
        mock_repository.update.return_value = sample_campaign

        update_data = CampaignUpdate(name="Updated Name")
        result = await campaign_service.update_campaign(
            campaign_id=sample_campaign.id,
            data=update_data,
        )

        assert result.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_campaign_non_draft_restricted_fields(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
        sample_campaign: Campaign,
    ) -> None:
        """Test that restricted fields cannot be updated when not in draft."""
        sample_campaign.status = CampaignStatus.RUNNING
        mock_repository.get_by_id.return_value = sample_campaign

        update_data = CampaignUpdate(name="New Name")

        with pytest.raises(ValidationError) as exc_info:
            await campaign_service.update_campaign(
                campaign_id=sample_campaign.id,
                data=update_data,
            )

        assert "draft status" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_campaign_description_always_allowed(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
        sample_campaign: Campaign,
    ) -> None:
        """Test that description can be updated in any status."""
        sample_campaign.status = CampaignStatus.RUNNING
        mock_repository.get_by_id.return_value = sample_campaign
        mock_repository.update.return_value = sample_campaign

        update_data = CampaignUpdate(description="New description")
        result = await campaign_service.update_campaign(
            campaign_id=sample_campaign.id,
            data=update_data,
        )

        assert result.description == "New description"

    @pytest.mark.asyncio
    async def test_delete_campaign(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
        sample_campaign: Campaign,
    ) -> None:
        """Test campaign deletion (soft delete)."""
        mock_repository.get_by_id.return_value = sample_campaign

        await campaign_service.delete_campaign(sample_campaign.id)

        mock_repository.delete.assert_called_once_with(sample_campaign)

    @pytest.mark.asyncio
    async def test_transition_status_valid(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
        sample_campaign: Campaign,
    ) -> None:
        """Test valid status transition."""
        mock_repository.get_by_id.return_value = sample_campaign
        mock_repository.update.return_value = sample_campaign

        result = await campaign_service.transition_status(
            campaign_id=sample_campaign.id,
            new_status=CampaignStatus.RUNNING,
        )

        assert result.status == CampaignStatus.RUNNING

    @pytest.mark.asyncio
    async def test_transition_status_invalid(
        self,
        campaign_service: CampaignService,
        mock_repository: AsyncMock,
        sample_campaign: Campaign,
    ) -> None:
        """Test invalid status transition."""
        mock_repository.get_by_id.return_value = sample_campaign

        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            await campaign_service.transition_status(
                campaign_id=sample_campaign.id,
                new_status=CampaignStatus.COMPLETED,
            )

        assert exc_info.value.current_status == CampaignStatus.DRAFT
        assert exc_info.value.target_status == CampaignStatus.COMPLETED


# ============================================================================
# Schema Validation Tests
# ============================================================================


class TestCampaignSchemas:
    """Tests for campaign schemas."""

    def test_create_schema_valid(self) -> None:
        """Test valid campaign creation schema."""
        data = CampaignCreate(
            name="Test Campaign",
            intro_script="Hello...",
            question_1_text="Q1?",
            question_1_type=QuestionType.SCALE,
            question_2_text="Q2?",
            question_2_type=QuestionType.FREE_TEXT,
            question_3_text="Q3?",
            question_3_type=QuestionType.NUMERIC,
            allowed_call_start_local=time(9, 0),
            allowed_call_end_local=time(18, 0),
        )
        assert data.name == "Test Campaign"
        assert data.max_attempts == 3  # Default

    def test_create_schema_invalid_time_window(self) -> None:
        """Test invalid time window validation."""
        with pytest.raises(ValueError) as exc_info:
            CampaignCreate(
                name="Test Campaign",
                intro_script="Hello...",
                question_1_text="Q1?",
                question_1_type=QuestionType.SCALE,
                question_2_text="Q2?",
                question_2_type=QuestionType.FREE_TEXT,
                question_3_text="Q3?",
                question_3_type=QuestionType.NUMERIC,
                allowed_call_start_local=time(18, 0),
                allowed_call_end_local=time(9, 0),  # End before start
            )
        assert "allowed_call_start_local must be before" in str(exc_info.value)

    def test_create_schema_invalid_max_attempts(self) -> None:
        """Test invalid max_attempts validation."""
        with pytest.raises(ValueError):
            CampaignCreate(
                name="Test Campaign",
                intro_script="Hello...",
                question_1_text="Q1?",
                question_1_type=QuestionType.SCALE,
                question_2_text="Q2?",
                question_2_type=QuestionType.FREE_TEXT,
                question_3_text="Q3?",
                question_3_type=QuestionType.NUMERIC,
                max_attempts=10,  # Max is 5
                allowed_call_start_local=time(9, 0),
                allowed_call_end_local=time(18, 0),
            )

    def test_update_schema_partial(self) -> None:
        """Test partial update schema."""
        data = CampaignUpdate(name="New Name")
        assert data.name == "New Name"
        assert data.description is None
        assert data.language is None