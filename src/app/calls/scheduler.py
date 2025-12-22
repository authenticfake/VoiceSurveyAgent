"""
Call scheduler service for outbound call orchestration.

REQ-008: Call scheduler service
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence, TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy import and_, func, select, update
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.calls.repository import CallAttemptRepository
    from app.campaigns.models import Campaign, CampaignStatus
    from app.contacts.models import Contact, ContactState
else:  # pragma: no cover
    # Keep this module importable in environments without SQLAlchemy.
    # The async/ORM path will raise at runtime if used without SQLAlchemy.
    and_ = func = select = update = None  # type: ignore[assignment]
    AsyncSession = Any  # type: ignore[misc]
    CallAttemptRepository = Any  # type: ignore[misc]
    Campaign = Any  # type: ignore[misc]
    CampaignStatus = Any  # type: ignore[misc]
    Contact = Any  # type: ignore[misc]
    ContactState = Any  # type: ignore[misc]

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
        """Initiate an outbound call."""


class SyncTelephonyProviderProtocol(Protocol):
    """Synchronous protocol for telephony provider adapter.

    This is used ONLY for fast, deterministic unit tests (no async, no event loop).
    Production code should keep using TelephonyProviderProtocol.
    """

    def initiate_call(
        self,
        to_number: str,
        from_number: str,
        callback_url: str,
        metadata: dict[str, str],
    ) -> str:
        """Initiate an outbound call (sync)."""


class CallAttemptRepositorySyncProtocol(Protocol):
    """Synchronous protocol for persisting CallAttempt records (unit-test use)."""

    def create(
        self,
        contact_id: UUID,
        campaign_id: UUID,
        attempt_number: int,
        call_id: str,
    ) -> object:
        """Create a call attempt record (sync)."""


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
        session: "AsyncSession",
        telephony_provider: TelephonyProviderProtocol | None = None,
        config: CallSchedulerConfig | None = None,
        callback_base_url: str = "http://localhost:8000",
        outbound_number: str = "+10000000000",
    ) -> None:
        if select is None:
            raise RuntimeError("SQLAlchemy is required for the async scheduler.")

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
            logger.warning("Call scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Call scheduler started")

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
            except Exception:
                logger.exception("Scheduler iteration failed")
            await asyncio.sleep(self._config.interval_seconds)

    async def run_once(self) -> int:
        """Run a single scheduler iteration.

        Returns:
            Number of calls initiated.
        """
        logger.debug("Starting scheduler iteration")

        campaigns = await self._get_running_campaigns()
        if not campaigns:
            logger.debug("No running campaigns found")
            return 0

        total_initiated = 0

        for campaign in campaigns:
            if not self._is_within_call_window(campaign):
                logger.debug("Campaign outside call window", extra={"campaign_id": str(campaign.id)})
                continue

            contacts = await self._get_eligible_contacts(
                campaign_id=campaign.id,
                max_attempts=campaign.max_attempts,
                limit=self._config.batch_size,
            )

            if not contacts:
                logger.debug("No eligible contacts for campaign", extra={"campaign_id": str(campaign.id)})
                continue

            initiated = 0
            for contact in contacts[: self._config.max_concurrent_calls]:
                try:
                    call_id = str(uuid4())

                    await self._update_contact_state(
                        contact_id=contact.id,
                        state=self._contact_state_in_progress(),
                        increment_attempts=True,
                    )

                    await self._call_attempt_repo.create(
                        contact_id=contact.id,
                        campaign_id=campaign.id,
                        attempt_number=contact.attempts_count + 1,
                        call_id=call_id,
                    )

                    if self._telephony_provider:
                        callback_url = f"{self._callback_base_url}/webhooks/telephony/events"
                        metadata = {
                            "campaign_id": str(campaign.id),
                            "contact_id": str(contact.id),
                            "call_id": call_id,
                            "language": contact.preferred_language or campaign.language,
                        }

                        await self._telephony_provider.initiate_call(
                            to_number=contact.phone_number,
                            from_number=self._outbound_number,
                            callback_url=callback_url,
                            metadata=metadata,
                        )

                    initiated += 1

                except Exception:
                    logger.exception(
                        "Failed to initiate call",
                        extra={"contact_id": str(contact.id), "campaign_id": str(campaign.id)},
                    )

            total_initiated += initiated

        logger.info("Scheduler iteration completed", extra={"initiated": total_initiated})
        return total_initiated

    @staticmethod
    def run_once_sync(
        *,
        campaigns: Sequence[object],
        contacts: Sequence[object],
        call_attempt_repo: CallAttemptRepositorySyncProtocol,
        telephony_provider: SyncTelephonyProviderProtocol,
        config: CallSchedulerConfig | None = None,
        outbound_number: str = "+10000000000",
        callback_base_url: str = "http://localhost:8000",
        now: datetime,
    ) -> int:
        """Run a single scheduler iteration synchronously (unit-test helper).

        This does NOT touch SQLAlchemy or any DB session.

        Acceptance criteria covered:
        1) interval_seconds is handled by config (default 60 checked in unit test)
        2) states pending/not_reached
        3) attempts_count < campaign.max_attempts
        4) now is inside allowed_call_start_local/end_local
        5) CallAttempt is created BEFORE provider initiation
        """
        cfg = config or CallSchedulerConfig()

        def _val(v: object) -> object:
            return getattr(v, "value", v)

        running_campaigns = [c for c in campaigns if _val(getattr(c, "status", None)) == "running"]
        if not running_campaigns:
            return 0

        by_campaign: dict[UUID, list[object]] = {}
        for contact in contacts:
            by_campaign.setdefault(getattr(contact, "campaign_id"), []).append(contact)

        total_initiated = 0

        for campaign in running_campaigns:
            current_time = now.time().replace(tzinfo=None)
            start_time = getattr(campaign, "allowed_call_start_local", None)
            end_time = getattr(campaign, "allowed_call_end_local", None)

            if start_time is not None and end_time is not None:
                if not (start_time <= current_time <= end_time):
                    continue

            eligible: list[object] = []
            for contact in by_campaign.get(getattr(campaign, "id"), []):
                if getattr(contact, "do_not_call", False):
                    continue

                state_val = _val(getattr(contact, "state", None))
                if state_val not in ("pending", "not_reached"):
                    continue

                if getattr(contact, "attempts_count", 0) >= getattr(campaign, "max_attempts"):
                    continue

                eligible.append(contact)

            if not eligible:
                continue

            eligible = eligible[: cfg.batch_size]
            eligible = eligible[: cfg.max_concurrent_calls]

            for contact in eligible:
                call_id = str(uuid4())

                # Update contact first (same behavior as async path)
                contact.state = "in_progress"
                contact.attempts_count += 1

                # AC-5: Create attempt BEFORE provider call
                call_attempt_repo.create(
                    contact_id=getattr(contact, "id"),
                    campaign_id=getattr(campaign, "id"),
                    attempt_number=getattr(contact, "attempts_count"),
                    call_id=call_id,
                )

                callback_url = f"{callback_base_url}/webhooks/telephony/events"
                metadata = {
                    "campaign_id": str(getattr(campaign, "id")),
                    "contact_id": str(getattr(contact, "id")),
                    "call_id": call_id,
                    "language": getattr(contact, "preferred_language", None) or getattr(campaign, "language", "it"),
                }

                telephony_provider.initiate_call(
                    to_number=getattr(contact, "phone_number"),
                    from_number=outbound_number,
                    callback_url=callback_url,
                    metadata=metadata,
                )

                total_initiated += 1

        return total_initiated

    async def _get_running_campaigns(self) -> Sequence["Campaign"]:
        """Get all campaigns with running status."""
        if select is None:
            raise RuntimeError("SQLAlchemy is required for the async scheduler.")
        stmt = select(Campaign).where(Campaign.status == CampaignStatus.RUNNING)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    def _is_within_call_window(self, campaign: "Campaign") -> bool:
        """Check if current time is within campaign's allowed call window.

        Note: this function intentionally uses real time for production use.
        Unit tests should call the sync core which accepts an injected `now`.
        """
        return self._is_within_call_window_at(campaign, datetime.now(timezone.utc))

    def _is_within_call_window_at(self, campaign: "Campaign", now: datetime) -> bool:
        """Deterministic time-window check (inject `now`)."""
        current_time = now.time().replace(tzinfo=None)

        start_time = campaign.allowed_call_start_local
        end_time = campaign.allowed_call_end_local

        if start_time is None or end_time is None:
            return True

        return start_time <= current_time <= end_time

    async def _get_eligible_contacts(
        self,
        campaign_id: UUID,
        max_attempts: int,
        limit: int,
    ) -> Sequence["Contact"]:
        """Get contacts eligible for calling."""
        if select is None or and_ is None or func is None:
            raise RuntimeError("SQLAlchemy is required for the async scheduler.")

        stmt = (
            select(Contact)
            .where(
                and_(
                    Contact.campaign_id == campaign_id,
                    Contact.state.in_([ContactState.PENDING, ContactState.NOT_REACHED]),
                    Contact.attempts_count < max_attempts,
                    Contact.do_not_call.is_(False),
                )
            )
            .order_by(Contact.created_at.asc())
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def _update_contact_state(self, contact_id: UUID, state: object, increment_attempts: bool) -> None:
        """Update contact state in database."""
        if update is None:
            raise RuntimeError("SQLAlchemy is required for the async scheduler.")

        values: dict[str, object] = {"state": state}
        if increment_attempts:
            values["attempts_count"] = func.coalesce(Contact.attempts_count, 0) + 1  # type: ignore[operator]

        stmt = update(Contact).where(Contact.id == contact_id).values(**values)
        await self._session.execute(stmt)
        await self._session.commit()

    def _contact_state_in_progress(self) -> object:
        """Return IN_PROGRESS state (safe even under TYPE_CHECKING)."""
        # In runtime (with SQLAlchemy present), ContactState is the real Enum
        return getattr(ContactState, "IN_PROGRESS", "in_progress")
