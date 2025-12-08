"""
Campaign service for business logic.

Implements campaign management operations with state machine validation.
"""

from uuid import UUID

from app.auth.schemas import UserContext
from app.campaigns.models import Campaign, CampaignStatusEnum
from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import (
    CampaignCreate,
    CampaignStatus,
    CampaignUpdate,
)
from app.shared.exceptions import InvalidStateTransitionError, NotFoundError, ValidationError
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Valid state transitions for campaign status
VALID_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.DRAFT: {CampaignStatus.SCHEDULED, CampaignStatus.RUNNING, CampaignStatus.CANCELLED},
    CampaignStatus.SCHEDULED: {CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.CANCELLED},
    CampaignStatus.RUNNING: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
    CampaignStatus.PAUSED: {CampaignStatus.RUNNING, CampaignStatus.CANCELLED},
    CampaignStatus.COMPLETED: set(),  # Terminal state
    CampaignStatus.CANCELLED: set(),  # Terminal state
}

# Fields that can be updated in each status
UPDATABLE_FIELDS_BY_STATUS: dict[CampaignStatus, set[str]] = {
    CampaignStatus.DRAFT: {
        "name", "description", "language", "intro_script",
        "question_1", "question_2", "question_3",
        "max_attempts", "retry_interval_minutes",
        "allowed_call_start_local", "allowed_call_end_local",
        "email_completed_template_id", "email_refused_template_id",
        "email_not_reached_template_id",
    },
    CampaignStatus.SCHEDULED: {
        "name", "description",
        "email_completed_template_id", "email_refused_template_id",
        "email_not_reached_template_id",
    },
    CampaignStatus.RUNNING: {
        "name", "description",
        "email_completed_template_id", "email_refused_template_id",
        "email_not_reached_template_id",
    },
    CampaignStatus.PAUSED: {
        "name", "description",
        "email_completed_template_id", "email_refused_template_id",
        "email_not_reached_template_id",
    },
    CampaignStatus.COMPLETED: set(),
    CampaignStatus.CANCELLED: set(),
}

class CampaignService:
    """Service for campaign business logic."""

    def __init__(self, repository: CampaignRepository) -> None:
        """Initialize service with repository."""
        self._repository = repository

    async def create_campaign(
        self,
        data: CampaignCreate,
        user: UserContext,
    ) -> Campaign:
        """Create a new campaign in draft status."""
        campaign = Campaign(
            name=data.name,
            description=data.description,
            status=CampaignStatusEnum.DRAFT,
            language=data.language.value,
            intro_script=data.intro_script,
            question_1_text=data.question_1.text,
            question_1_type=data.question_1.type.value,
            question_2_text=data.question_2.text,
            question_2_type=data.question_2.type.value,
            question_3_text=data.question_3.text,
            question_3_type=data.question_3.type.value,
            max_attempts=data.max_attempts,
            retry_interval_minutes=data.retry_interval_minutes,
            allowed_call_start_local=data.allowed_call_start_local,
            allowed_call_end_local=data.allowed_call_end_local,
            email_completed_template_id=data.email_completed_template_id,
            email_refused_template_id=data.email_refused_template_id,
            email_not_reached_template_id=data.email_not_reached_template_id,
            created_by_user_id=user.id,
        )

        campaign = await self._repository.create(campaign)
        logger.info(
            "Campaign created",
            campaign_id=str(campaign.id),
            user_id=str(user.id),
        )
        return campaign

    async def get_campaign(self, campaign_id: UUID) -> Campaign:
        """Get campaign by ID."""
        campaign = await self._repository.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError(
                message=f"Campaign with ID {campaign_id} not found",
                details={"campaign_id": str(campaign_id)},
            )
        return campaign

    async def list_campaigns(
        self,
        status: CampaignStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Campaign], int]:
        """List campaigns with optional filtering and pagination."""
        return await self._repository.list_campaigns(
            status=status,
            page=page,
            page_size=page_size,
        )

    async def update_campaign(
        self,
        campaign_id: UUID,
        data: CampaignUpdate,
        user: UserContext,
    ) -> Campaign:
        """Update campaign with field validation based on current status."""
        campaign = await self.get_campaign(campaign_id)
        current_status = CampaignStatus(campaign.status)

        # Get allowed fields for current status
        allowed_fields = UPDATABLE_FIELDS_BY_STATUS.get(current_status, set())

        # Check which fields are being updated
        update_data = data.model_dump(exclude_unset=True)
        invalid_fields = set(update_data.keys()) - allowed_fields

        if invalid_fields:
            raise ValidationError(
                message=f"Cannot update fields {invalid_fields} when campaign is in {current_status.value} status",
                details={
                    "invalid_fields": list(invalid_fields),
                    "current_status": current_status.value,
                    "allowed_fields": list(allowed_fields),
                },
            )

        # Apply updates
        for field, value in update_data.items():
            if field.startswith("question_"):
                # Handle nested question updates
                q_num = field.split("_")[1]
                if value is not None:
                    setattr(campaign, f"question_{q_num}_text", value.text)
                    setattr(campaign, f"question_{q_num}_type", value.type.value)
            else:
                if hasattr(campaign, field):
                    if field == "language":
                        setattr(campaign, field, value.value if value else None)
                    else:
                        setattr(campaign, field, value)

        campaign = await self._repository.update(campaign)
        logger.info(
            "Campaign updated",
            campaign_id=str(campaign.id),
            user_id=str(user.id),
            updated_fields=list(update_data.keys()),
        )
        return campaign

    async def transition_status(
        self,
        campaign_id: UUID,
        target_status: CampaignStatus,
        user: UserContext,
    ) -> Campaign:
        """Transition campaign to a new status."""
        campaign = await self.get_campaign(campaign_id)
        current_status = CampaignStatus(campaign.status)

        # Validate transition
        valid_targets = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in valid_targets:
            raise InvalidStateTransitionError(
                message=f"Cannot transition from {current_status.value} to {target_status.value}",
                details={
                    "current_status": current_status.value,
                    "target_status": target_status.value,
                    "valid_transitions": [s.value for s in valid_targets],
                },
            )

        # Update status
        campaign.status = CampaignStatusEnum(target_status.value)
        campaign = await self._repository.update(campaign)

        logger.info(
            "Campaign status transitioned",
            campaign_id=str(campaign.id),
            user_id=str(user.id),
            from_status=current_status.value,
            to_status=target_status.value,
        )
        return campaign

    async def delete_campaign(
        self,
        campaign_id: UUID,
        user: UserContext,
    ) -> Campaign:
        """Soft delete campaign by setting status to cancelled."""
        campaign = await self.get_campaign(campaign_id)
        current_status = CampaignStatus(campaign.status)

        # Check if deletion is allowed
        if current_status in {CampaignStatus.COMPLETED, CampaignStatus.CANCELLED}:
            raise InvalidStateTransitionError(
                message=f"Cannot delete campaign in {current_status.value} status",
                details={"current_status": current_status.value},
            )

        campaign = await self._repository.soft_delete(campaign)
        logger.info(
            "Campaign soft deleted",
            campaign_id=str(campaign.id),
            user_id=str(user.id),
        )
        return campaign