"""
Unit tests for Campaign Service.

Tests business logic and state machine validation.
"""

from datetime import time
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import UserContext, UserRole
from app.campaigns.models import Campaign, CampaignStatusEnum, User
from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import (
    CampaignCreate,
    CampaignLanguage,
    CampaignStatus,
    CampaignUpdate,
    QuestionConfig,
    QuestionType,
)
from app.campaigns.service import CampaignService, VALID_TRANSITIONS
from app.shared.exceptions import InvalidStateTransitionError, NotFoundError, ValidationError

@pytest_asyncio.fixture
async def user_context() -> UserContext:
    """Create a test user context."""
    return UserContext(
        id=uuid4(),
        oidc_sub="test-sub",
        email="test@example.com",
        name="Test User",
        role=UserRole.CAMPAIGN_MANAGER,
    )

@pytest_asyncio.fixture
async def campaign_service(db_session: AsyncSession) -> CampaignService:
    """Create campaign service with repository."""
    repository = CampaignRepository(db_session)
    return CampaignService(repository)

@pytest_asyncio.fixture
async def test_user_in_db(db_session: AsyncSession, user_context: UserContext) -> User:
    """Create test user in database."""
    user = User(
        id=user_context.id,
        oidc_sub=user_context.oidc_sub,
        email=user_context.email,
        name=user_context.name,
        role=user_context.role.value,
    )
    db_session.add(user)
    await db_session.flush()
    return user

class TestCampaignServiceCreate:
    """Tests for campaign creation."""

    @pytest.mark.asyncio
    async def test_create_campaign_success(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
        test_user_in_db: User,
    ):
        """Test successful campaign creation."""
        data = CampaignCreate(
            name="Test Campaign",
            description="Test description",
            language=CampaignLanguage.EN,
            intro_script="Hello, this is a test survey...",
            question_1=QuestionConfig(text="Question 1?", type=QuestionType.FREE_TEXT),
            question_2=QuestionConfig(text="Question 2?", type=QuestionType.SCALE),
            question_3=QuestionConfig(text="Question 3?", type=QuestionType.NUMERIC),
            max_attempts=3,
            retry_interval_minutes=60,
            allowed_call_start_local=time(9, 0),
            allowed_call_end_local=time(20, 0),
        )

        campaign = await campaign_service.create_campaign(data, user_context)

        assert campaign.name == data.name
        assert campaign.status == CampaignStatusEnum.DRAFT
        assert campaign.created_by_user_id == user_context.id

    @pytest.mark.asyncio
    async def test_create_campaign_with_all_fields(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
        test_user_in_db: User,
    ):
        """Test campaign creation with all optional fields."""
        data = CampaignCreate(
            name="Full Campaign",
            description="Full description",
            language=CampaignLanguage.IT,
            intro_script="Ciao, questo è un sondaggio...",
            question_1=QuestionConfig(text="Domanda 1?", type=QuestionType.FREE_TEXT),
            question_2=QuestionConfig(text="Domanda 2?", type=QuestionType.SCALE),
            question_3=QuestionConfig(text="Domanda 3?", type=QuestionType.NUMERIC),
            max_attempts=5,
            retry_interval_minutes=120,
            allowed_call_start_local=time(10, 0),
            allowed_call_end_local=time(18, 0),
        )

        campaign = await campaign_service.create_campaign(data, user_context)

        assert campaign.language == "it"
        assert campaign.max_attempts == 5

class TestCampaignServiceUpdate:
    """Tests for campaign updates."""

    @pytest.mark.asyncio
    async def test_update_draft_campaign_all_fields(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
        test_campaign: Campaign,
    ):
        """Test updating all fields in draft status."""
        update_data = CampaignUpdate(
            name="Updated Name",
            description="Updated description",
            max_attempts=5,
        )

        campaign = await campaign_service.update_campaign(
            test_campaign.id, update_data, user_context
        )

        assert campaign.name == "Updated Name"
        assert campaign.max_attempts == 5

    @pytest.mark.asyncio
    async def test_update_running_campaign_restricted_fields(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
        test_campaign: Campaign,
        db_session: AsyncSession,
    ):
        """Test that running campaigns have restricted field updates."""
        # First transition to running
        test_campaign.status = CampaignStatusEnum.RUNNING
        await db_session.flush()

        # Try to update restricted field
        update_data = CampaignUpdate(max_attempts=5)

        with pytest.raises(ValidationError) as exc_info:
            await campaign_service.update_campaign(
                test_campaign.id, update_data, user_context
            )

        assert "max_attempts" in str(exc_info.value.details)

class TestCampaignServiceStatusTransitions:
    """Tests for status transitions."""

    @pytest.mark.asyncio
    async def test_valid_transitions(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
        test_campaign: Campaign,
    ):
        """Test valid status transitions."""
        # Draft -> Running
        campaign = await campaign_service.transition_status(
            test_campaign.id, CampaignStatus.RUNNING, user_context
        )
        assert campaign.status == CampaignStatusEnum.RUNNING

    @pytest.mark.asyncio
    async def test_invalid_transition_raises_error(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
        test_campaign: Campaign,
    ):
        """Test invalid transition raises error."""
        with pytest.raises(InvalidStateTransitionError):
            await campaign_service.transition_status(
                test_campaign.id, CampaignStatus.COMPLETED, user_context
            )

    @pytest.mark.asyncio
    async def test_transition_from_completed_not_allowed(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
        test_campaign: Campaign,
        db_session: AsyncSession,
    ):
        """Test that completed campaigns cannot transition."""
        test_campaign.status = CampaignStatusEnum.COMPLETED
        await db_session.flush()

        with pytest.raises(InvalidStateTransitionError):
            await campaign_service.transition_status(
                test_campaign.id, CampaignStatus.RUNNING, user_context
            )

    def test_valid_transitions_coverage(self):
        """Test that all status transitions are properly defined."""
        # Verify all statuses have transition rules
        for status in CampaignStatus:
            assert status in VALID_TRANSITIONS

        # Verify terminal states have no transitions
        assert len(VALID_TRANSITIONS[CampaignStatus.COMPLETED]) == 0
        assert len(VALID_TRANSITIONS[CampaignStatus.CANCELLED]) == 0

class TestCampaignServiceDelete:
    """Tests for campaign deletion."""

    @pytest.mark.asyncio
    async def test_delete_draft_campaign(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
        test_campaign: Campaign,
    ):
        """Test deleting a draft campaign."""
        campaign = await campaign_service.delete_campaign(
            test_campaign.id, user_context
        )

        assert campaign.status == CampaignStatusEnum.CANCELLED

    @pytest.mark.asyncio
    async def test_delete_completed_campaign_fails(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
        test_campaign: Campaign,
        db_session: AsyncSession,
    ):
        """Test that completed campaigns cannot be deleted."""
        test_campaign.status = CampaignStatusEnum.COMPLETED
        await db_session.flush()

        with pytest.raises(InvalidStateTransitionError):
            await campaign_service.delete_campaign(test_campaign.id, user_context)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_campaign(
        self,
        campaign_service: CampaignService,
        user_context: UserContext,
    ):
        """Test deleting non-existent campaign raises error."""
        with pytest.raises(NotFoundError):
            await campaign_service.delete_campaign(uuid4(), user_context)