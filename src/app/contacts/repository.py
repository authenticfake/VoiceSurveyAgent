"""
Contact repository for database operations.

REQ-005: Campaign validation service (contact count for validation)
REQ-006: Contact CSV upload and parsing (future)
"""

from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Contact


class ContactRepositoryProtocol(Protocol):
    """Protocol for contact repository operations."""

    async def count_by_campaign(self, campaign_id: UUID) -> int:
        """Count contacts for a campaign."""
        ...


class ContactRepository:
    """Repository for contact database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session.
        """
        self._session = session

    async def count_by_campaign(self, campaign_id: UUID) -> int:
        """Count contacts for a campaign.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            Number of contacts for the campaign.
        """
        stmt = select(func.count(Contact.id)).where(
            Contact.campaign_id == campaign_id
        )
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count if count is not None else 0