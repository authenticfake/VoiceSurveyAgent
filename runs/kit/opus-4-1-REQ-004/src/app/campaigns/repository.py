"""Campaign repository for database operations."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.shared.models.campaign import Campaign
from app.shared.models.enums import CampaignStatus
from app.shared.logging import get_logger

logger = get_logger(__name__)


class CampaignRepository:
    """Repository for campaign database operations."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize repository with database session."""
        self.db = db_session
    
    async def create(self, campaign: Campaign) -> Campaign:
        """Create a new campaign."""
        self.db.add(campaign)
        await self.db.commit()
        await self.db.refresh(campaign)
        logger.info(f"Created campaign {campaign.id}")
        return campaign
    
    async def get_by_id(self, campaign_id: UUID) -> Optional[Campaign]:
        """Get campaign by ID."""
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        status: Optional[CampaignStatus] = None,
        user_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Campaign], int]:
        """Get paginated list of campaigns with optional filters."""
        # Build query with filters
        conditions = []
        if status:
            conditions.append(Campaign.status == status)
        if user_id:
            conditions.append(Campaign.created_by_user_id == user_id)
        
        # Get total count
        count_stmt = select(func.count()).select_from(Campaign)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Get paginated results
        stmt = select(Campaign)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.offset(offset).limit(limit).order_by(Campaign.created_at.desc())
        
        result = await self.db.execute(stmt)
        campaigns = list(result.scalars().all())
        
        return campaigns, total
    
    async def update(self, campaign: Campaign, updates: dict) -> Campaign:
        """Update campaign with provided fields."""
        for field, value in updates.items():
            if value is not None:
                setattr(campaign, field, value)
        
        await self.db.commit()
        await self.db.refresh(campaign)
        logger.info(f"Updated campaign {campaign.id}")
        return campaign
    
    async def update_status(
        self, campaign_id: UUID, new_status: CampaignStatus
    ) -> Optional[Campaign]:
        """Update campaign status."""
        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            return None
        
        campaign.status = new_status
        await self.db.commit()
        await self.db.refresh(campaign)
        logger.info(f"Updated campaign {campaign_id} status to {new_status}")
        return campaign
    
    async def delete(self, campaign_id: UUID) -> bool:
        """Soft delete campaign by setting status to cancelled."""
        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.CANCELLED
        await self.db.commit()
        logger.info(f"Soft deleted campaign {campaign_id}")
        return True