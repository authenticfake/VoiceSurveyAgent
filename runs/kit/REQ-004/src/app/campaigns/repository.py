"""
Campaign repository for database operations.

Provides data access layer for campaign entities.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.campaigns.models import Campaign, CampaignStatusEnum
from app.campaigns.schemas import CampaignStatus
from app.shared.logging import get_logger

logger = get_logger(__name__)

class CampaignRepository:
    """Repository for campaign database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self._session = session

    async def create(self, campaign: Campaign) -> Campaign:
        """Create a new campaign."""
        self._session.add(campaign)
        await self._session.flush()
        await self._session.refresh(campaign)
        logger.info("Created campaign", campaign_id=str(campaign.id))
        return campaign

    async def get_by_id(self, campaign_id: UUID) -> Campaign | None:
        """Get campaign by ID."""
        result = await self._session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def list_campaigns(
        self,
        status: CampaignStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Campaign], int]:
        """List campaigns with optional status filter and pagination."""
        query = select(Campaign)

        if status:
            query = query.where(Campaign.status == CampaignStatusEnum(status.value))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Campaign.created_at.desc())

        result = await self._session.execute(query)
        campaigns = list(result.scalars().all())

        return campaigns, total

    async def update(self, campaign: Campaign) -> Campaign:
        """Update an existing campaign."""
        await self._session.flush()
        await self._session.refresh(campaign)
        logger.info("Updated campaign", campaign_id=str(campaign.id))
        return campaign

    async def soft_delete(self, campaign: Campaign) -> Campaign:
        """Soft delete a campaign by setting status to cancelled."""
        campaign.status = CampaignStatusEnum.CANCELLED
        await self._session.flush()
        await self._session.refresh(campaign)
        logger.info("Soft deleted campaign", campaign_id=str(campaign.id))
        return campaign