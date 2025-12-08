"""Campaign repository for database operations."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.campaign import Campaign
from app.shared.models.contact import Contact
from app.shared.models.enums import CampaignStatus

class CampaignRepository:
    """Repository for campaign database operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository.
        
        Args:
            session: SQLAlchemy async session
        """
        self._session = session
    
    async def get_by_id(self, campaign_id: UUID) -> Optional[Campaign]:
        """
        Get campaign by ID.
        
        Args:
            campaign_id: UUID of the campaign
            
        Returns:
            Campaign if found, None otherwise
        """
        result = await self._session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()
    
    async def get_contact_count(self, campaign_id: UUID) -> int:
        """
        Get count of contacts for a campaign.
        
        Args:
            campaign_id: UUID of the campaign
            
        Returns:
            Number of contacts associated with the campaign
        """
        result = await self._session.execute(
            select(func.count(Contact.id)).where(Contact.campaign_id == campaign_id)
        )
        return result.scalar_one()
    
    async def list_campaigns(
        self,
        status_filter: Optional[CampaignStatus] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Campaign], int]:
        """
        List campaigns with optional filtering and pagination.
        
        Args:
            status_filter: Optional status to filter by
            offset: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (campaigns list, total count)
        """
        query = select(Campaign)
        count_query = select(func.count(Campaign.id))
        
        if status_filter:
            query = query.where(Campaign.status == status_filter)
            count_query = count_query.where(Campaign.status == status_filter)
        
        query = query.order_by(Campaign.created_at.desc()).offset(offset).limit(limit)
        
        result = await self._session.execute(query)
        campaigns = result.scalars().all()
        
        count_result = await self._session.execute(count_query)
        total = count_result.scalar_one()
        
        return campaigns, total
    
    async def create(self, campaign: Campaign) -> Campaign:
        """
        Create a new campaign.
        
        Args:
            campaign: Campaign entity to create
            
        Returns:
            Created campaign with generated ID
        """
        self._session.add(campaign)
        await self._session.flush()
        await self._session.refresh(campaign)
        return campaign
    
    async def update(self, campaign: Campaign) -> Campaign:
        """
        Update an existing campaign.
        
        Args:
            campaign: Campaign entity with updated fields
            
        Returns:
            Updated campaign
        """
        await self._session.flush()
        await self._session.refresh(campaign)
        return campaign
    
    async def update_status(
        self,
        campaign_id: UUID,
        new_status: CampaignStatus,
    ) -> Optional[Campaign]:
        """
        Update campaign status.
        
        Args:
            campaign_id: UUID of the campaign
            new_status: New status to set
            
        Returns:
            Updated campaign if found, None otherwise
        """
        campaign = await self.get_by_id(campaign_id)
        if campaign:
            campaign.status = new_status
            await self._session.flush()
            await self._session.refresh(campaign)
        return campaign