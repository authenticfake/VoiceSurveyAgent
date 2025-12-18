"""
Repository for exclusion list database operations.

REQ-007: Exclusion list management
"""

from typing import Protocol, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.exclusions.models import ExclusionListEntry, ExclusionSource


class ExclusionRepositoryProtocol(Protocol):
    """Protocol for exclusion repository operations."""

    async def get_by_id(self, exclusion_id: UUID) -> ExclusionListEntry | None:
        """Get exclusion entry by ID."""
        ...

    async def get_by_phone(self, phone_number: str) -> ExclusionListEntry | None:
        """Get exclusion entry by phone number."""
        ...

    async def exists(self, phone_number: str) -> bool:
        """Check if phone number is in exclusion list."""
        ...

    async def exists_bulk(self, phone_numbers: list[str]) -> set[str]:
        """Check which phone numbers are in exclusion list."""
        ...

    async def create(
        self,
        phone_number: str,
        source: ExclusionSource,
        reason: str | None = None,
    ) -> ExclusionListEntry:
        """Create a new exclusion entry."""
        ...

    async def create_bulk(
        self,
        entries: list[tuple[str, ExclusionSource, str | None]],
    ) -> int:
        """Create multiple exclusion entries, ignoring duplicates."""
        ...

    async def delete(self, exclusion_id: UUID) -> bool:
        """Delete an exclusion entry by ID."""
        ...

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[Sequence[ExclusionListEntry], int]:
        """List all exclusion entries with pagination."""
        ...


class ExclusionRepository:
    """Repository for exclusion list database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get_by_id(self, exclusion_id: UUID) -> ExclusionListEntry | None:
        """Get exclusion entry by ID.

        Args:
            exclusion_id: Exclusion entry UUID.

        Returns:
            ExclusionListEntry if found, None otherwise.
        """
        stmt = select(ExclusionListEntry).where(ExclusionListEntry.id == exclusion_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> ExclusionListEntry | None:
        """Get exclusion entry by phone number.

        Args:
            phone_number: Phone number to look up.

        Returns:
            ExclusionListEntry if found, None otherwise.
        """
        stmt = select(ExclusionListEntry).where(
            ExclusionListEntry.phone_number == phone_number
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, phone_number: str) -> bool:
        """Check if phone number is in exclusion list.

        Args:
            phone_number: Phone number to check.

        Returns:
            True if phone number is excluded, False otherwise.
        """
        stmt = select(
            func.count(ExclusionListEntry.id)
        ).where(ExclusionListEntry.phone_number == phone_number)
        result = await self._session.execute(stmt)
        count = result.scalar_one()
        return count > 0

    async def exists_bulk(self, phone_numbers: list[str]) -> set[str]:
        """Check which phone numbers are in exclusion list.

        Args:
            phone_numbers: List of phone numbers to check.

        Returns:
            Set of phone numbers that are in the exclusion list.
        """
        if not phone_numbers:
            return set()

        stmt = select(ExclusionListEntry.phone_number).where(
            ExclusionListEntry.phone_number.in_(phone_numbers)
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result.fetchall()}

    async def create(
        self,
        phone_number: str,
        source: ExclusionSource,
        reason: str | None = None,
    ) -> ExclusionListEntry:
        """Create a new exclusion entry.

        Args:
            phone_number: Phone number to exclude.
            source: Source of the exclusion.
            reason: Optional reason for exclusion.

        Returns:
            Created ExclusionListEntry.
        """
        entry = ExclusionListEntry(
            phone_number=phone_number,
            source=source,
            reason=reason,
        )
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def create_bulk(
        self,
        entries: list[tuple[str, ExclusionSource, str | None]],
    ) -> int:
        """Create multiple exclusion entries, ignoring duplicates.

        Args:
            entries: List of (phone_number, source, reason) tuples.

        Returns:
            Number of entries actually inserted.
        """
        if not entries:
            return 0

        values = [
            {
                "phone_number": phone,
                "source": source,
                "reason": reason,
            }
            for phone, source, reason in entries
        ]

        stmt = insert(ExclusionListEntry).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["phone_number"])
        result = await self._session.execute(stmt)
        return result.rowcount

    async def delete(self, exclusion_id: UUID) -> bool:
        """Delete an exclusion entry by ID.

        Args:
            exclusion_id: Exclusion entry UUID.

        Returns:
            True if entry was deleted, False if not found.
        """
        stmt = delete(ExclusionListEntry).where(
            ExclusionListEntry.id == exclusion_id
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[Sequence[ExclusionListEntry], int]:
        """List all exclusion entries with pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Number of entries per page.

        Returns:
            Tuple of (entries, total_count).
        """
        # Get total count
        count_stmt = select(func.count(ExclusionListEntry.id))
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        # Get paginated entries
        offset = (page - 1) * page_size
        stmt = (
            select(ExclusionListEntry)
            .order_by(ExclusionListEntry.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        entries = result.scalars().all()

        return entries, total