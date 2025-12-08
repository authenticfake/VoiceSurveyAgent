"""Campaign business logic service."""

from typing import Optional
from uuid import UUID

from app.campaigns.repository import CampaignRepository
from app.campaigns.schemas import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
)
from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus
from app.shared.exceptions import (
    NotFoundError,
    ValidationError,
    StateTransitionError,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


class CampaignService:
    """Service for campaign business logic."""
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        CampaignStatus.DRAFT: [
            CampaignStatus.SCHEDULED,
            CampaignStatus.RUNNING,
            CampaignStatus.CANCELLED,
        ],
        CampaignStatus.SCHEDULED: [
            CampaignStatus.RUNNING,
            CampaignStatus.PAUSED,
            CampaignStatus.CANCELLED,
        ],
        CampaignStatus.RUNNING: [
            CampaignStatus.PAUSED,
            CampaignStatus.COMPLETED,
            CampaignStatus.CANCELLED,
        ],
        CampaignStatus.PAUSED: [
            CampaignStatus.RUNNING,
            CampaignStatus.CANCELLED,
        ],
        CampaignStatus.COMPLETED: [],
        CampaignStatus.CANCELLED: [],
    }
    
    def __init__(self, repository: CampaignRepository):
        """Initialize service with repository."""
        self.repository = repository
    
    async def create_campaign(
        self, data: CampaignCreate, user_id: UUID
    ) -> CampaignResponse:
        """Create a new campaign."""
        campaign = Campaign(
            **data.model_dump(),
            status=CampaignStatus.DRAFT,
            created_by_user_id=user_id,
        )
        
        created = await self.repository.create(campaign)
        logger.info(f"User {user_id} created campaign {created.id}")
        return CampaignResponse.model_validate(created)
    
    async def get_campaign(self, campaign_id: UUID) -> CampaignResponse:
        """Get campaign by ID."""
        campaign = await self.repository.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        
        return CampaignResponse.model_validate(campaign)
    
    async def list_campaigns(
        self,
        status: Optional[CampaignStatus] = None,
        user_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CampaignListResponse:
        """Get paginated list of campaigns."""
        offset = (page - 1) * page_size
        campaigns, total = await self.repository.get_list(
            status=status,
            user_id=user_id,
            offset=offset,
            limit=page_size,
        )
        
        return CampaignListResponse(
            campaigns=[CampaignResponse.model_validate(c) for c in campaigns],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def update_campaign(
        self, campaign_id: UUID, data: CampaignUpdate
    ) -> CampaignResponse:
        """Update campaign fields."""
        campaign = await self.repository.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        
        # Only allow updates in certain states
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.PAUSED]:
            raise ValidationError(
                f"Cannot update campaign in {campaign.status} status"
            )
        
        updates = data.model_dump(exclude_unset=True)
        updated = await self.repository.update(campaign, updates)
        return CampaignResponse.model_validate(updated)
    
    async def transition_status(
        self, campaign_id: UUID, new_status: CampaignStatus
    ) -> CampaignResponse:
        """Transition campaign to new status."""
        campaign = await self.repository.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        
        # Check if transition is valid
        current_status = campaign.status
        valid_transitions = self.VALID_TRANSITIONS.get(current_status, [])
        
        if new_status not in valid_transitions:
            raise StateTransitionError(
                f"Invalid transition from {current_status} to {new_status}"
            )
        
        updated = await self.repository.update_status(campaign_id, new_status)
        logger.info(f"Campaign {campaign_id} transitioned from {current_status} to {new_status}")
        return CampaignResponse.model_validate(updated)
    
    async def delete_campaign(self, campaign_id: UUID) -> bool:
        """Soft delete campaign."""
        campaign = await self.repository.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        
        # Only allow deletion in certain states
        if campaign.status in [CampaignStatus.RUNNING]:
            raise ValidationError("Cannot delete a running campaign")
        
        return await self.repository.delete(campaign_id)