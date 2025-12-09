"""Campaign repository for database operations."""

from datetime import time
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.campaign import Campaign
from app.shared.models.contact import Contact
from app.shared.models.enums import CampaignStatus
from app.shared.logging import get_logger

logger = get_logger(__name__)

class CampaignRepository:
    """Repository for campaign database operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session
    
    async def create(self, campaign: Campaign) -> Campaign:
        """Create a new campaign."""
        self._session.add(campaign)
        await self._session.flush()
        await self._session.refresh(campaign)
        logger.info(
            "Campaign created",
            extra={"campaign_id": str(campaign.id), "name": campaign.name},
        )
        return campaign
    
    async def get_by_id(self, campaign_id: UUID) -> Optional[Campaign]:
        """Get a campaign by ID."""
        result = await self._session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()
    
    async def list_campaigns(
        self,
        status: Optional[CampaignStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Campaign], int]:
        """List campaigns with optional status filter and pagination."""
        query = select(Campaign)
        count_query = select(func.count()).select_from(Campaign)
        
        if status:
            query = query.where(Campaign.status == status)
            count_query = count_query.where(Campaign.status == status)
        
        # Get total count
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        offset = (page - 1) * page_size
        query = query.order_by(Campaign.created_at.desc()).offset(offset).limit(page_size)
        result = await self._session.execute(query)
        campaigns = result.scalars().all()
        
        return campaigns, total
    
    async def update(self, campaign: Campaign) -> Campaign:
        """Update a campaign."""
        await self._session.flush()
        await self._session.refresh(campaign)
        logger.info(
            "Campaign updated",
            extra={"campaign_id": str(campaign.id), "status": campaign.status.value},
        )
        return campaign
    
    async def soft_delete(self, campaign: Campaign) -> Campaign:
        """Soft delete a campaign by setting status to cancelled."""
        campaign.status = CampaignStatus.CANCELLED
        await self._session.flush()
        await self._session.refresh(campaign)
        logger.info(
            "Campaign soft deleted",
            extra={"campaign_id": str(campaign.id)},
        )
        return campaign
    
    # Methods for CampaignDataProvider protocol
    async def get_contact_count(self, campaign_id: UUID) -> int:
        """Get the number of contacts for a campaign."""
        result = await self._session.execute(
            select(func.count()).select_from(Contact).where(Contact.campaign_id == campaign_id)
        )
        return result.scalar() or 0
    
    async def get_campaign_questions(self, campaign_id: UUID) -> tuple[str, str, str]:
        """Get the three question texts for a campaign."""
        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            return ("", "", "")
        return (
            campaign.question_1_text or "",
            campaign.question_2_text or "",
            campaign.question_3_text or "",
        )
    
    async def get_retry_policy(self, campaign_id: UUID) -> tuple[int, int]:
        """Get max_attempts and retry_interval_minutes."""
        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            return (0, 0)
        return (campaign.max_attempts, campaign.retry_interval_minutes)
    
    async def get_time_window(self, campaign_id: UUID) -> tuple[time, time]:
        """Get allowed_call_start_local and allowed_call_end_local."""
        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            return (time(0, 0), time(0, 0))
        return (campaign.allowed_call_start_local, campaign.allowed_call_end_local)
    
    async def get_campaign_status(self, campaign_id: UUID) -> CampaignStatus:
        """Get current campaign status."""
        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            return CampaignStatus.CANCELLED  # Safe default for non-existent
        return campaign.status