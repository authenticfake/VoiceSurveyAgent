"""
Campaign repository for database operations.

REQ-004: Campaign CRUD API
"""

from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.campaigns.models import Campaign, CampaignStatus
from app.shared.logging import get_logger

logger = get_logger(__name__)


class CampaignRepositoryProtocol(Protocol):
    """Protocol for campaign repository operations."""

    async def get_by_id(self, campaign_id: UUID) -> Campaign | None: ...
    async def get_list(
        self,
        status: CampaignStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Campaign], int]: ...
    async def create(self, campaign: Campaign) -> Campaign: ...
    async def update(self, campaign: Campaign) -> Campaign: ...
    async def delete(self, campaign: Campaign) -> None: ...
    async def count_contacts(self, campaign_id: UUID) -> int: ...


class CampaignRepository:
    """Repository for campaign database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get_by_id(self, campaign_id: UUID) -> Campaign | None:
        """Get campaign by ID.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            Campaign if found, None otherwise.
        """
        result = await self._session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
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
        # Build base query
        query = select(Campaign)
        count_query = select(func.count(Campaign.id))

        # Apply status filter if provided
        if status is not None:
            query = query.where(Campaign.status == status)
            count_query = count_query.where(Campaign.status == status)

        # Get total count
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(Campaign.created_at.desc()).offset(offset).limit(page_size)

        # Execute query
        result = await self._session.execute(query)
        campaigns = list(result.scalars().all())

        logger.debug(
            "Retrieved campaign list",
            extra={
                "status_filter": status.value if status else None,
                "page": page,
                "page_size": page_size,
                "total": total,
                "returned": len(campaigns),
            },
        )

        return campaigns, total

    async def create(self, campaign: Campaign) -> Campaign:
        """Create a new campaign.

        Args:
            campaign: Campaign entity to create.

        Returns:
            Created campaign with generated ID.
        """
        self._session.add(campaign)
        await self._session.flush()
        await self._session.refresh(campaign)

        logger.info(
            "Created campaign",
            extra={
                "campaign_id": str(campaign.id),
                "name": campaign.name,
                "status": campaign.status.value,
            },
        )

        return campaign

    async def update(self, campaign: Campaign) -> Campaign:
        """Update an existing campaign.

        Args:
            campaign: Campaign entity with updated values.

        Returns:
            Updated campaign.
        """
        await self._session.flush()
        await self._session.refresh(campaign)

        logger.info(
            "Updated campaign",
            extra={
                "campaign_id": str(campaign.id),
                "name": campaign.name,
                "status": campaign.status.value,
            },
        )

        return campaign

    async def delete(self, campaign: Campaign) -> None:
        """Delete a campaign (soft delete by setting status to cancelled).

        Args:
            campaign: Campaign entity to delete.
        """
        campaign.status = CampaignStatus.CANCELLED
        await self._session.flush()

        logger.info(
            "Soft deleted campaign",
            extra={
                "campaign_id": str(campaign.id),
                "name": campaign.name,
            },
        )

    async def count_contacts(self, campaign_id: UUID) -> int:
        """Count contacts for a campaign.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            Number of contacts associated with the campaign.
        """
        # Import here to avoid circular imports
        from sqlalchemy import text

        result = await self._session.execute(
            text("SELECT COUNT(*) FROM contacts WHERE campaign_id = :campaign_id"),
            {"campaign_id": campaign_id},
        )
        count = result.scalar_one()

        logger.debug(
            "Counted campaign contacts",
            extra={
                "campaign_id": str(campaign_id),
                "count": count,
            },
        )

        return count