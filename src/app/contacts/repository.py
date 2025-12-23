"""
Contact repository for database operations.

"""

from typing import Protocol, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Contact, ContactState


class ContactRepositoryProtocol(Protocol):
    """Protocol for contact repository operations."""

    async def count_by_campaign(self, campaign_id: UUID) -> int:
        """Count contacts for a campaign."""
        ...

    async def create_bulk(self, contacts: list[Contact]) -> list[Contact]:
        """Create multiple contacts in bulk."""
        ...

    async def get_by_campaign(
        self,
        campaign_id: UUID,
        page: int = 1,
        page_size: int = 50,
        state: ContactState | None = None,
    ) -> tuple[Sequence[Contact], int]:
        """Get contacts for a campaign with pagination."""
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
    
    async def update_flags(
        self,
        contact: Contact,
        *,
        has_prior_consent: bool | None = None,
        do_not_call: bool | None = None,
    ) -> Contact:
        """Update consent / DNC flags for a contact.

        Args:
            contact: ORM contact instance (must be attached to session).
            has_prior_consent: New value or None to leave unchanged.
            do_not_call: New value or None to leave unchanged.

        Returns:
            Updated contact.
        """
        if has_prior_consent is not None:
            contact.has_prior_consent = has_prior_consent
        if do_not_call is not None:
            contact.do_not_call = do_not_call

        await self._session.flush()
        await self._session.refresh(contact)
        return contact


    async def create(self, contact: Contact) -> Contact:
        """Create a single contact.

        Args:
            contact: Contact to create.

        Returns:
            Created contact with ID.
        """
        self._session.add(contact)
        await self._session.flush()
        await self._session.refresh(contact)
        return contact

    async def create_bulk(self, contacts: list[Contact]) -> list[Contact]:
        """Create multiple contacts in bulk.

        Args:
            contacts: List of contacts to create.

        Returns:
            List of created contacts with IDs.
        """
        if not contacts:
            return []

        self._session.add_all(contacts)
        await self._session.flush()

        # Refresh all contacts to get generated IDs
        for contact in contacts:
            await self._session.refresh(contact)

        return contacts

    async def get_by_campaign(
        self,
        campaign_id: UUID,
        page: int = 1,
        page_size: int = 50,
        state: ContactState | None = None,
    ) -> tuple[Sequence[Contact], int]:
        """Get contacts for a campaign with pagination.

        Args:
            campaign_id: Campaign UUID.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            state: Optional state filter.

        Returns:
            Tuple of (contacts list, total count).
        """
        # Build base query
        base_query = select(Contact).where(Contact.campaign_id == campaign_id)

        if state is not None:
            base_query = base_query.where(Contact.state == state)

        # Get total count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        stmt = (
            base_query
            .order_by(Contact.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        contacts = result.scalars().all()

        return contacts, total

    async def get_by_id(self, contact_id: UUID) -> Contact | None:
        """Get a contact by ID.

        Args:
            contact_id: Contact UUID.

        Returns:
            Contact if found, None otherwise.
        """
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone_and_campaign(
        self,
        phone_number: str,
        campaign_id: UUID,
    ) -> Contact | None:
        """Get a contact by phone number and campaign.

        Args:
            phone_number: Phone number to search.
            campaign_id: Campaign UUID.

        Returns:
            Contact if found, None otherwise.
        """
        stmt = select(Contact).where(
            Contact.phone_number == phone_number,
            Contact.campaign_id == campaign_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()