"""Campaign service for business logic."""

from typing import Optional
from uuid import UUID

from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import CampaignCreate, CampaignUpdate
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus
from app.shared.exceptions import NotFoundError, ValidationError, StateTransitionError
from app.shared.logging import get_logger

logger = get_logger(__name__)


# Valid state transitions
VALID_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.DRAFT: {CampaignStatus.SCHEDULED, CampaignStatus.RUNNING, CampaignStatus.CANCELLED},
    CampaignStatus.SCHEDULED: {CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.CANCELLED},
    CampaignStatus.RUNNING: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
    CampaignStatus.PAUSED: {CampaignStatus.RUNNING, CampaignStatus.CANCELLED},
    CampaignStatus.COMPLETED: set(),  # Terminal state
    CampaignStatus.CANCELLED: set(),  # Terminal state
}

# Statuses that allow field updates
EDITABLE_STATUSES = {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}


class CampaignService:
    """Service for campaign business logic."""
    
    def __init__(self, repository: CampaignRepository):
        self._repository = repository
    
    async def create_campaign(
        self,
        data: CampaignCreate,
        user_id: UUID,
    ) -> Campaign:
        """Create a new campaign in draft status."""
        campaign = Campaign(
            name=data.name,
            description=data.description,
            status=CampaignStatus.DRAFT,
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
            created_by_user_id=user_id,
        )
        return await self._repository.create(campaign)
    
    async def get_campaign(self, campaign_id: UUID) -> Campaign:
        """Get campaign by ID."""
        campaign = await self._repository.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        return campaign
    
    async def list_campaigns(
        self,
        status: Optional[CampaignStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Campaign], int]:
        """List campaigns with optional filtering and pagination."""
        campaigns, total = await self._repository.list_campaigns(
            status=status,
            page=page,
            page_size=page_size,
        )
        return list(campaigns), total
    
    async def update_campaign(
        self,
        campaign_id: UUID,
        data: CampaignUpdate,
    ) -> Campaign:
        """Update campaign fields."""
        campaign = await self.get_campaign(campaign_id)
        
        # Check if campaign is in editable status
        if campaign.status not in EDITABLE_STATUSES:
            raise ValidationError(
                f"Cannot update campaign in {campaign.status.value} status. "
                f"Only campaigns in {', '.join(s.value for s in EDITABLE_STATUSES)} can be updated."
            )
        
        # Apply updates
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)
        
        return await self._repository.update(campaign)
    
    async def update_status(
        self,
        campaign_id: UUID,
        new_status: CampaignStatus,
    ) -> Campaign:
        """Update campaign status following state machine rules."""
        campaign = await self.get_campaign(campaign_id)
        
        # Check if transition is valid
        valid_next_states = VALID_TRANSITIONS.get(campaign.status, set())
        if new_status not in valid_next_states:
            raise StateTransitionError(
                f"Cannot transition from {campaign.status.value} to {new_status.value}. "
                f"Valid transitions: {', '.join(s.value for s in valid_next_states) or 'none'}"
            )
        
        campaign.status = new_status
        logger.info(
            "Campaign status updated",
            extra={
                "campaign_id": str(campaign_id),
                "old_status": campaign.status.value,
                "new_status": new_status.value,
            }
        )
        return await self._repository.update(campaign)
    
    async def delete_campaign(self, campaign_id: UUID) -> Campaign:
        """Soft delete a campaign by setting status to cancelled."""
        campaign = await self.get_campaign(campaign_id)
        
        # Check if campaign can be cancelled
        if campaign.status in {CampaignStatus.COMPLETED, CampaignStatus.CANCELLED}:
            raise StateTransitionError(
                f"Cannot delete campaign in {campaign.status.value} status"
            )
        
        return await self._repository.soft_delete(campaign)