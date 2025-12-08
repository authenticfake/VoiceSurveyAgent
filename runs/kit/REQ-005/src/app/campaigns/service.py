"""Campaign service for business logic."""

from typing import Optional, Sequence
from uuid import UUID

from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import CampaignCreate, CampaignUpdate
from app.shared.exceptions import NotFoundError, StateTransitionError
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus
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

class CampaignService:
    """Service for campaign business logic."""
    
    def __init__(self, repository: CampaignRepository) -> None:
        """
        Initialize service.
        
        Args:
            repository: Campaign repository for data access
        """
        self._repository = repository
    
    async def create_campaign(
        self,
        data: CampaignCreate,
        created_by_user_id: UUID,
    ) -> Campaign:
        """
        Create a new campaign in draft status.
        
        Args:
            data: Campaign creation data
            created_by_user_id: UUID of the creating user
            
        Returns:
            Created campaign
        """
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
            created_by_user_id=created_by_user_id,
        )
        
        return await self._repository.create(campaign)
    
    async def get_campaign(self, campaign_id: UUID) -> Campaign:
        """
        Get campaign by ID.
        
        Args:
            campaign_id: UUID of the campaign
            
        Returns:
            Campaign entity
            
        Raises:
            NotFoundError: If campaign not found
        """
        campaign = await self._repository.get_by_id(campaign_id)
        if campaign is None:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        return campaign
    
    async def list_campaigns(
        self,
        status_filter: Optional[CampaignStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Campaign], int]:
        """
        List campaigns with pagination.
        
        Args:
            status_filter: Optional status to filter by
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            Tuple of (campaigns list, total count)
        """
        offset = (page - 1) * page_size
        return await self._repository.list_campaigns(
            status_filter=status_filter,
            offset=offset,
            limit=page_size,
        )
    
    async def update_campaign(
        self,
        campaign_id: UUID,
        data: CampaignUpdate,
    ) -> Campaign:
        """
        Update campaign fields.
        
        Args:
            campaign_id: UUID of the campaign
            data: Update data
            
        Returns:
            Updated campaign
            
        Raises:
            NotFoundError: If campaign not found
            StateTransitionError: If campaign is not in editable state
        """
        campaign = await self.get_campaign(campaign_id)
        
        # Only allow updates in draft or scheduled status
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
            raise StateTransitionError(
                f"Cannot update campaign in {campaign.status.value} status"
            )
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)
        
        return await self._repository.update(campaign)
    
    async def update_status(
        self,
        campaign_id: UUID,
        new_status: CampaignStatus,
    ) -> Campaign:
        """
        Update campaign status following state machine rules.
        
        Args:
            campaign_id: UUID of the campaign
            new_status: New status to set
            
        Returns:
            Updated campaign
            
        Raises:
            NotFoundError: If campaign not found
            StateTransitionError: If transition is not valid
        """
        campaign = await self.get_campaign(campaign_id)
        
        valid_next_states = VALID_TRANSITIONS.get(campaign.status, set())
        if new_status not in valid_next_states:
            raise StateTransitionError(
                f"Cannot transition from {campaign.status.value} to {new_status.value}"
            )
        
        campaign.status = new_status
        return await self._repository.update(campaign)
    
    async def delete_campaign(self, campaign_id: UUID) -> None:
        """
        Soft delete campaign by setting status to cancelled.
        
        Args:
            campaign_id: UUID of the campaign
            
        Raises:
            NotFoundError: If campaign not found
        """
        campaign = await self.get_campaign(campaign_id)
        
        # Allow cancellation from any non-terminal state
        if campaign.status in {CampaignStatus.COMPLETED, CampaignStatus.CANCELLED}:
            return  # Already in terminal state
        
        campaign.status = CampaignStatus.CANCELLED
        await self._repository.update(campaign)