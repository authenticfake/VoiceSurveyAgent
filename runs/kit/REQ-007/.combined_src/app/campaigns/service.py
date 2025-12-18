"""
Campaign service for business logic.

REQ-004: Campaign CRUD API
"""

from typing import Protocol
from uuid import UUID

from app.campaigns.models import Campaign, CampaignStatus, VALID_STATUS_TRANSITIONS
from app.campaigns.repository import CampaignRepository, CampaignRepositoryProtocol
from app.campaigns.schemas import CampaignCreate, CampaignUpdate
from app.shared.exceptions import (
    CampaignNotFoundError,
    InvalidStatusTransitionError,
    ValidationError,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


class CampaignServiceProtocol(Protocol):
    """Protocol for campaign service operations."""

    async def get_campaign(self, campaign_id: UUID) -> Campaign: ...
    async def list_campaigns(
        self,
        status: CampaignStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Campaign], int]: ...
    async def create_campaign(
        self,
        data: CampaignCreate,
        created_by_user_id: UUID,
    ) -> Campaign: ...
    async def update_campaign(
        self,
        campaign_id: UUID,
        data: CampaignUpdate,
    ) -> Campaign: ...
    async def delete_campaign(self, campaign_id: UUID) -> None: ...
    async def transition_status(
        self,
        campaign_id: UUID,
        new_status: CampaignStatus,
    ) -> Campaign: ...


class CampaignService:
    """Service for campaign business logic."""

    def __init__(self, repository: CampaignRepositoryProtocol) -> None:
        """Initialize service with repository.

        Args:
            repository: Campaign repository for database operations.
        """
        self._repository = repository

    async def get_campaign(self, campaign_id: UUID) -> Campaign:
        """Get a campaign by ID.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            Campaign entity.

        Raises:
            CampaignNotFoundError: If campaign not found.
        """
        campaign = await self._repository.get_by_id(campaign_id)
        if campaign is None:
            logger.warning(
                "Campaign not found",
                extra={"campaign_id": str(campaign_id)},
            )
            raise CampaignNotFoundError(campaign_id)

        return campaign

    async def list_campaigns(
        self,
        status: CampaignStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Campaign], int]:
        """Get paginated list of campaigns.

        Args:
            status: Optional status filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Tuple of (campaigns list, total count).
        """
        return await self._repository.get_list(
            status=status,
            page=page,
            page_size=page_size,
        )

    async def create_campaign(
        self,
        data: CampaignCreate,
        created_by_user_id: UUID,
    ) -> Campaign:
        """Create a new campaign.

        Args:
            data: Campaign creation data.
            created_by_user_id: ID of the user creating the campaign.

        Returns:
            Created campaign entity.
        """
        campaign = Campaign(
            name=data.name,
            description=data.description,
            status=CampaignStatus.DRAFT,  # Always start in draft
            language=data.language,
            intro_script=data.intro_script,
            question_1_text=data.question_1_text,
            question_1_type=data.question_1_type,
            question_2_text=data.question_2_text,
            question_2_type=data.question_2_type,
            question_3_text=data.question_3_text,
            question_3_type=data.question_3_type,
            max_attempts=data.max_attempts,
            retry_interval_minutes=data.retry_interval_minutes,
            allowed_call_start_local=data.allowed_call_start_local,
            allowed_call_end_local=data.allowed_call_end_local,
            email_completed_template_id=data.email_completed_template_id,
            email_refused_template_id=data.email_refused_template_id,
            email_not_reached_template_id=data.email_not_reached_template_id,
            created_by_user_id=created_by_user_id,
        )

        created = await self._repository.create(campaign)

        logger.info(
            "Campaign created",
            extra={
                "campaign_id": str(created.id),
                "name": created.name,
                "created_by": str(created_by_user_id),
            },
        )

        return created

    async def update_campaign(
        self,
        campaign_id: UUID,
        data: CampaignUpdate,
    ) -> Campaign:
        """Update an existing campaign.

        Args:
            campaign_id: Campaign UUID.
            data: Campaign update data.

        Returns:
            Updated campaign entity.

        Raises:
            CampaignNotFoundError: If campaign not found.
            ValidationError: If update is not allowed for current status.
        """
        campaign = await self.get_campaign(campaign_id)

        # Validate update is allowed based on status
        self._validate_update_allowed(campaign, data)

        # Apply updates
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)

        updated = await self._repository.update(campaign)

        logger.info(
            "Campaign updated",
            extra={
                "campaign_id": str(updated.id),
                "updated_fields": list(update_data.keys()),
            },
        )

        return updated

    def _validate_update_allowed(
        self,
        campaign: Campaign,
        data: CampaignUpdate,
    ) -> None:
        """Validate that update is allowed for current campaign status.

        Args:
            campaign: Current campaign entity.
            data: Proposed update data.

        Raises:
            ValidationError: If update is not allowed.
        """
        # Define fields that can be updated in each status
        always_updatable = {"description", "email_completed_template_id", "email_refused_template_id", "email_not_reached_template_id"}
        draft_only = {"name", "language", "intro_script", "question_1_text", "question_1_type", "question_2_text", "question_2_type", "question_3_text", "question_3_type", "max_attempts", "retry_interval_minutes", "allowed_call_start_local", "allowed_call_end_local"}

        update_data = data.model_dump(exclude_unset=True)
        requested_fields = set(update_data.keys())

        # Check if any draft-only fields are being updated
        draft_only_requested = requested_fields & draft_only

        if draft_only_requested and campaign.status != CampaignStatus.DRAFT:
            raise ValidationError(
                f"Fields {draft_only_requested} can only be updated when campaign is in draft status. "
                f"Current status: {campaign.status.value}"
            )

        # Validate time window if both times are being updated
        new_start = update_data.get("allowed_call_start_local")
        new_end = update_data.get("allowed_call_end_local")
        
        # If only one is provided, use existing value for comparison
        if new_start is not None and new_end is None:
            new_end = campaign.allowed_call_end_local
        elif new_end is not None and new_start is None:
            new_start = campaign.allowed_call_start_local

        if new_start is not None and new_end is not None:
            if new_start >= new_end:
                raise ValidationError(
                    "allowed_call_start_local must be before allowed_call_end_local"
                )

    async def delete_campaign(self, campaign_id: UUID) -> None:
        """Delete a campaign (soft delete).

        Args:
            campaign_id: Campaign UUID.

        Raises:
            CampaignNotFoundError: If campaign not found.
        """
        campaign = await self.get_campaign(campaign_id)
        await self._repository.delete(campaign)

        logger.info(
            "Campaign deleted",
            extra={"campaign_id": str(campaign_id)},
        )

    async def transition_status(
        self,
        campaign_id: UUID,
        new_status: CampaignStatus,
    ) -> Campaign:
        """Transition campaign to a new status.

        Args:
            campaign_id: Campaign UUID.
            new_status: Target status.

        Returns:
            Updated campaign entity.

        Raises:
            CampaignNotFoundError: If campaign not found.
            InvalidStatusTransitionError: If transition is not valid.
        """
        campaign = await self.get_campaign(campaign_id)

        if not campaign.can_transition_to(new_status):
            valid_transitions = VALID_STATUS_TRANSITIONS.get(campaign.status, set())
            raise InvalidStatusTransitionError(
                current_status=campaign.status,
                target_status=new_status,
                valid_transitions=valid_transitions,
            )

        old_status = campaign.status
        campaign.status = new_status
        updated = await self._repository.update(campaign)

        logger.info(
            "Campaign status transitioned",
            extra={
                "campaign_id": str(campaign_id),
                "old_status": old_status.value,
                "new_status": new_status.value,
            },
        )

        return updated