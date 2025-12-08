"""Campaign repository for database operations."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus
from app.shared.logging import get_logger

logger = get_logger(__name__)


class CampaignRepository:
    """Repository for campaign database operations."""
    
    def __init__(self, db_session: AsyncSession):
        self._db = db_session
    
    async def create(self, campaign: Campaign) -> Campaign:
        """Create a new campaign."""
        self._db.add(campaign)
        await self._db.flush()
        await self._db.refresh(campaign)
        logger.info(
            "Campaign created",
            extra={"campaign_id": str(campaign.id), "name": campaign.name}
        )
        return campaign
    
    async def get_by_id(self, campaign_id: UUID) -> Optional[Campaign]:
        """Get campaign by ID."""
        result = await self._db.execute(
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
        total_result = await self._db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated results
        offset = (page - 1) * page_size
        query = query.order_by(Campaign.created_at.desc()).offset(offset).limit(page_size)
        result = await self._db.execute(query)
        campaigns = result.scalars().all()
        
        return campaigns, total
    
    async def update(self, campaign: Campaign) -> Campaign:
        """Update an existing campaign."""
        await self._db.flush()
        await self._db.refresh(campaign)
        logger.info(
            "Campaign updated",
            extra={"campaign_id": str(campaign.id), "status": campaign.status.value}
        )
        return campaign
    
    async def soft_delete(self, campaign: Campaign) -> Campaign:
        """Soft delete a campaign by setting status to cancelled."""
        campaign.status = CampaignStatus.CANCELLED
        await self._db.flush()
        await self._db.refresh(campaign)
        logger.info(
            "Campaign soft deleted",
            extra={"campaign_id": str(campaign.id)}
        )
        return campaign