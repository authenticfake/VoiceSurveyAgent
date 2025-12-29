"""
Repository for call attempt database operations.

REQ-008: Call scheduler service
"""

from datetime import datetime,timezone
from typing import Any, Protocol, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calls.models import CallAttempt, CallOutcome


class CallAttemptRepositoryProtocol(Protocol):
    """Protocol for call attempt repository operations."""

    async def create(
        self,
        contact_id: UUID,
        campaign_id: UUID,
        attempt_number: int,
        call_id: str,
    ) -> CallAttempt:
        """Create a new call attempt record."""
        ...

    async def get_by_id(self, attempt_id: UUID) -> CallAttempt | None:
        """Get call attempt by ID."""
        ...

    async def get_by_call_id(self, call_id: str) -> CallAttempt | None:
        """Get call attempt by internal call ID."""
        ...

    async def update_outcome(
        self,
        attempt_id: UUID,
        outcome: CallOutcome,
        provider_call_id: str | None = None,
        provider_raw_status: str | None = None,
        error_code: str | None = None,
        answered_at: datetime | None = None,
        ended_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CallAttempt | None:
        """Update call attempt outcome."""
        ...

    async def get_by_contact(
        self,
        contact_id: UUID,
        limit: int = 10,
    ) -> Sequence[CallAttempt]:
        """Get call attempts for a contact."""
        ...


class CallAttemptRepository:
    """Repository for call attempt database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get_by_provider_call_id(self, provider_call_id: str) -> CallAttempt | None:
        """Get call attempt by provider call identifier (e.g., Twilio CallSid)."""
        stmt = select(CallAttempt).where(CallAttempt.provider_call_id == provider_call_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


    async def create(
        self,
        contact_id: UUID,
        campaign_id: UUID,
        attempt_number: int,
        call_id: str,
    ) -> CallAttempt:
        """Create a new call attempt record.

        Args:
            contact_id: Contact UUID.
            campaign_id: Campaign UUID.
            attempt_number: Attempt number for this contact.
            call_id: Internal unique call identifier.

        Returns:
            Created CallAttempt instance.
        """
        attempt = CallAttempt(
            contact_id=contact_id,
            campaign_id=campaign_id,
            attempt_number=attempt_number,
            call_id=call_id,
            started_at=datetime.now(timezone.utc),
        )
        self._session.add(attempt)
        await self._session.flush()
        await self._session.refresh(attempt)
        return attempt

    async def get_by_id(self, attempt_id: UUID) -> CallAttempt | None:
        """Get call attempt by ID.

        Args:
            attempt_id: Call attempt UUID.

        Returns:
            CallAttempt if found, None otherwise.
        """
        stmt = select(CallAttempt).where(CallAttempt.id == attempt_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_call_id(self, call_id: str) -> CallAttempt | None:
        """Get call attempt by internal call ID.

        Args:
            call_id: Internal call identifier.

        Returns:
            CallAttempt if found, None otherwise.
        """
        stmt = select(CallAttempt).where(CallAttempt.call_id == call_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_outcome(
        self,
        attempt_id: UUID,
        outcome: CallOutcome,
        provider_call_id: str | None = None,
        provider_raw_status: str | None = None,
        error_code: str | None = None,
        answered_at: datetime | None = None,
        ended_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CallAttempt | None:
        """Update call attempt outcome.

        Args:
            attempt_id: Call attempt UUID.
            outcome: Call outcome.
            provider_call_id: Provider's call identifier.
            provider_raw_status: Raw status from provider.
            error_code: Error code if failed.
            answered_at: When call was answered.
            ended_at: When call ended.
            metadata: Additional metadata.

        Returns:
            Updated CallAttempt if found, None otherwise.
        """
        attempt = await self.get_by_id(attempt_id)
        if attempt is None:
            return None

        attempt.outcome = outcome
        if provider_call_id is not None:
            attempt.provider_call_id = provider_call_id
        if provider_raw_status is not None:
            attempt.provider_raw_status = provider_raw_status
        if error_code is not None:
            attempt.error_code = error_code
        if answered_at is not None:
            attempt.answered_at = answered_at
        if ended_at is not None:
            attempt.ended_at = ended_at
        if metadata is not None:
            attempt.metadata = metadata

        await self._session.flush()
        await self._session.refresh(attempt)
        return attempt

    async def update_extra_metadata(
        self,
        attempt_id: UUID,
        extra_metadata: dict,
    ) -> CallAttempt:
        """Update extra_metadata atomically-ish (session flush + refresh)."""
        attempt = await self.get_by_id(attempt_id)
        if attempt is None:
            raise ValueError(f"CallAttempt not found: {attempt_id}")

        if hasattr(attempt, "extra_metadata"):
            attempt.extra_metadata = extra_metadata
        elif hasattr(attempt, "call_metadata"):
            attempt.call_metadata = extra_metadata
        else:
            # fallback: non dovrebbe succedere, ma evita crash in prod
            setattr(attempt, "extra_metadata", extra_metadata)

        await self._session.flush()
        await self._session.refresh(attempt)
        return attempt


    async def get_by_contact(
        self,
        contact_id: UUID,
        limit: int = 10,
    ) -> Sequence[CallAttempt]:
        """Get call attempts for a contact.

        Args:
            contact_id: Contact UUID.
            limit: Maximum number of attempts to return.

        Returns:
            List of CallAttempt instances.
        """
        stmt = (
            select(CallAttempt)
            .where(CallAttempt.contact_id == contact_id)
            .order_by(CallAttempt.started_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()