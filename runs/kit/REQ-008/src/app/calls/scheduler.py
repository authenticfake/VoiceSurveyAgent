"""
Call scheduler service for outbound call orchestration.

REQ-008: Call scheduler service
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Protocol, Sequence
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.calls.models import CallAttempt
from app.calls.repository import CallAttemptRepository
from app.campaigns.models import Campaign, CampaignStatus
from app.contacts.models import Contact, ContactState
from app.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CallSchedulerConfig:
    """Configuration for the call scheduler."""

    interval_seconds: int = 60
    max_concurrent_calls: int = 10
    batch_size: int = 50


class TelephonyProviderProtocol(Protocol):
    """Protocol for telephony provider adapter."""

    async def initiate_call(
        self,
        to_number: str,
        from_number: str,
        callback_url: str,
        metadata: dict[str, str],
    ) -> str:
        """Initiate an outbound call.

        Args:
            to_number: Destination phone number.
            from_number: Caller ID number.
            callback_url: Webhook URL for call events.
            metadata: Call metadata.

        Returns:
            Provider call ID.
        """
        ...


class CallScheduler:
    """Scheduler service for outbound call orchestration.

    Runs as a background task every 60 seconds to:
    - Select eligible contacts (pending/not_reached, within time window)
    - Filter by attempts_count < campaign.max_attempts
    - Create CallAttempt records before initiating calls
    - Respect max_concurrent_calls limit
    """

    def __init__(
        self,
        session: AsyncSession,
        telephony_provider: TelephonyProviderProtocol | None = None,
        config: CallSchedulerConfig | None = None,
        callback_base_url: str = "http://localhost:8000",
        outbound_number: str = "+14155550000",
    ) -> None:
        """Initialize the call scheduler.

        Args:
            session: Async database session.
            telephony_provider: Telephony provider adapter (optional for testing).
            config: Scheduler configuration.
            callback_base_url: Base URL for webhooks.
            outbound_number: Outbound caller ID number.
        """
        self._session = session
        self._telephony_provider = telephony_provider
        self._config = config or CallSchedulerConfig()
        self._callback_base_url = callback_base_url
        self._outbound_number = outbound_number
        self._call_attempt_repo = CallAttemptRepository(session)
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the scheduler background task."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Call scheduler started",
            extra={"interval_seconds": self._config.interval_seconds},
        )

    async def stop(self) -> None:
        """Stop the scheduler background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Call scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(
                    "Scheduler iteration failed",
                    extra={"error": str(e)},
                    exc_info=True,
                )
            await asyncio.sleep(self._config.interval_seconds)

    async def run_once(self) -> int:
        """Run a single scheduler iteration.

        Returns:
            Number of calls initiated.
        """
        logger.debug("Starting scheduler iteration")

        # Get running campaigns
        campaigns = await self._get_running_campaigns()
        if not campaigns:
            logger.debug("No running campaigns found")
            return 0

        total_initiated = 0

        for campaign in campaigns:
            # Check current time against campaign's allowed window
            if not self._is_within_call_window(campaign):
                logger.debug(
                    "Campaign outside call window",
                    extra={"campaign_id": str(campaign.id)},
                )
                continue

            # Get eligible contacts for this campaign
            contacts = await self._get_eligible_contacts(
                campaign_id=campaign.id,
                max_attempts=campaign.max_attempts,
                limit=self._config.batch_size,
            )

            if not contacts:
                logger.debug(
                    "No eligible contacts for campaign",
                    extra={"campaign_id": str(campaign.id)},
                )
                continue

            # Initiate calls respecting concurrency limit
            remaining_slots = self._config.max_concurrent_calls - total_initiated
            if remaining_slots <= 0:
                logger.debug("Max concurrent calls reached")
                break

            contacts_to_call = contacts[:remaining_slots]
            initiated = await self._initiate_calls(campaign, contacts_to_call)
            total_initiated += initiated

        logger.info(
            "Scheduler iteration completed",
            extra={"calls_initiated": total_initiated},
        )
        return total_initiated

    async def _get_running_campaigns(self) -> Sequence[Campaign]:
        """Get all campaigns with running status.

        Returns:
            List of running campaigns.
        """
        stmt = select(Campaign).where(Campaign.status == CampaignStatus.RUNNING)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    def _is_within_call_window(self, campaign: Campaign) -> bool:
        """Check if current time is within campaign's allowed call window.

        Args:
            campaign: Campaign to check.

        Returns:
            True if within window, False otherwise.
        """
        now = datetime.now(timezone.utc)
        current_time = now.time()

        start_time = campaign.allowed_call_start_local
        end_time = campaign.allowed_call_end_local

        if start_time is None or end_time is None:
            # No time window configured, allow all times
            return True

        # Handle time comparison
        return start_time <= current_time <= end_time

    async def _get_eligible_contacts(
        self,
        campaign_id: UUID,
        max_attempts: int,
        limit: int,
    ) -> Sequence[Contact]:
        """Get contacts eligible for calling.

        Selects contacts with:
        - state in (pending, not_reached)
        - attempts_count < max_attempts
        - do_not_call = False

        Args:
            campaign_id: Campaign UUID.
            max_attempts: Maximum attempts per contact.
            limit: Maximum contacts to return.

        Returns:
            List of eligible contacts.
        """
        stmt = (
            select(Contact)
            .where(
                and_(
                    Contact.campaign_id == campaign_id,
                    Contact.state.in_([ContactState.PENDING, ContactState.NOT_REACHED]),
                    Contact.attempts_count < max_attempts,
                    Contact.do_not_call == False,  # noqa: E712
                )
            )
            .order_by(Contact.attempts_count.asc(), Contact.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def _initiate_calls(
        self,
        campaign: Campaign,
        contacts: Sequence[Contact],
    ) -> int:
        """Initiate calls for a batch of contacts.

        Args:
            campaign: Campaign for the calls.
            contacts: Contacts to call.

        Returns:
            Number of calls successfully initiated.
        """
        initiated = 0

        for contact in contacts:
            try:
                # Generate unique call ID
                call_id = f"call-{uuid4()}"

                # Update contact state to in_progress
                await self._update_contact_state(
                    contact_id=contact.id,
                    state=ContactState.IN_PROGRESS,
                    increment_attempts=True,
                )

                # Create call attempt record
                attempt = await self._call_attempt_repo.create(
                    contact_id=contact.id,
                    campaign_id=campaign.id,
                    attempt_number=contact.attempts_count + 1,
                    call_id=call_id,
                )

                # Initiate call via telephony provider
                if self._telephony_provider:
                    callback_url = f"{self._callback_base_url}/webhooks/telephony/events"
                    metadata = {
                        "campaign_id": str(campaign.id),
                        "contact_id": str(contact.id),
                        "call_id": call_id,
                        "language": contact.preferred_language or campaign.language,
                    }

                    provider_call_id = await self._telephony_provider.initiate_call(
                        to_number=contact.phone_number,
                        from_number=self._outbound_number,
                        callback_url=callback_url,
                        metadata=metadata,
                    )

                    # Update attempt with provider call ID
                    await self._call_attempt_repo.update_outcome(
                        attempt_id=attempt.id,
                        outcome=attempt.outcome,  # Keep existing (None)
                        provider_call_id=provider_call_id,
                    )

                initiated += 1
                logger.info(
                    "Call initiated",
                    extra={
                        "call_id": call_id,
                        "contact_id": str(contact.id),
                        "campaign_id": str(campaign.id),
                        "attempt_number": contact.attempts_count + 1,
                    },
                )

            except Exception as e:
                logger.error(
                    "Failed to initiate call",
                    extra={
                        "contact_id": str(contact.id),
                        "campaign_id": str(campaign.id),
                        "error": str(e),
                    },
                    exc_info=True,
                )
                # Revert contact state on failure
                await self._update_contact_state(
                    contact_id=contact.id,
                    state=ContactState.PENDING,
                    increment_attempts=False,
                )

        await self._session.commit()
        return initiated

    async def _update_contact_state(
        self,
        contact_id: UUID,
        state: ContactState,
        increment_attempts: bool = False,
    ) -> None:
        """Update contact state and optionally increment attempts.

        Args:
            contact_id: Contact UUID.
            state: New contact state.
            increment_attempts: Whether to increment attempts_count.
        """
        values: dict[str, ContactState | datetime | int] = {
            "state": state,
            "last_attempt_at": datetime.now(timezone.utc),
        }

        if increment_attempts:
            stmt = (
                update(Contact)
                .where(Contact.id == contact_id)
                .values(
                    state=state,
                    last_attempt_at=datetime.now(timezone.utc),
                    attempts_count=Contact.attempts_count + 1,
                )
            )
        else:
            stmt = update(Contact).where(Contact.id == contact_id).values(**values)

        await self._session.execute(stmt)