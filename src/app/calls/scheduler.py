"""
Call scheduler servi ce for outbound call orchestration.

REQ-008: Call scheduler service
"""
import json
import os

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Protocol, Sequence, TYPE_CHECKING
from uuid import UUID, uuid4
from app.telephony.config import TelephonyConfig
from app.telephony.interface import CallInitiationRequest
from app.calls.models import CallAttempt, CallOutcome

from sqlalchemy import exists, or_


if TYPE_CHECKING:  # pragma: no cover
    # Imports only for type checking (mypy/pyright). Do NOT use this branch for runtime gating.
    from sqlalchemy import and_, func, select, update
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.calls.repository import CallAttemptRepository
    from app.campaigns.models import Campaign, CampaignStatus
    from app.contacts.models import Contact, ContactState

# Runtime imports (must work in production)
try:  # pragma: no cover
    from sqlalchemy import and_, func, select, update
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy import text 

    from app.calls.repository import CallAttemptRepository
    from app.campaigns.models import Campaign, CampaignStatus
    from app.contacts.models import Contact, ContactState

    SQLALCHEMY_AVAILABLE = True
except ImportError:  # pragma: no cover
    # Keep this module importable in environments without SQLAlchemy.
    # The async/ORM path will raise at runtime if used without SQLAlchemy.
    and_ = func = select = update = None  # type: ignore[assignment]
    AsyncSession = Any  # type: ignore[misc]
    CallAttemptRepository = Any  # type: ignore[misc]
    Campaign = Any  # type: ignore[misc]
    CampaignStatus = Any  # type: ignore[misc]
    Contact = Any  # type: ignore[misc]
    ContactState = Any  # type: ignore[misc]
    IntegrityError = Exception  # type: ignore[assignment]

    SQLALCHEMY_AVAILABLE = False




from app.calls.models import CallAttempt
from app.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CallSchedulerConfig:
    """Configuration for the call scheduler."""

    interval_seconds: int = 60
    max_concurrent_calls: int = 10
    batch_size: int = 50
    requeue_stale_minutes: int = 0



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
        telephony_config: TelephonyConfig | None = None,
        scheduler_config: CallSchedulerConfig | None = None,
        callback_base_url: str = "http://localhost:8880",
        outbound_number: str = "+10000000000",
    ) -> None:
        if not SQLALCHEMY_AVAILABLE:
            raise RuntimeError("SQLAlchemy is required for the async scheduler.")


        self._session = session
        self._telephony_provider = telephony_provider
        self._telephony_config = telephony_config

        self._config = scheduler_config or CallSchedulerConfig()
        self._callback_base_url = callback_base_url
        self._outbound_number = outbound_number

        self._call_attempt_repo = CallAttemptRepository(session)

        self._running = False
        self._task: asyncio.Task[None] | None = None

    
    

    async def _claim_contact_for_call(self, *, contact_id: object, max_attempts: int) -> int | None:
        """
        Claim atomico:
        - prende SOLO se è ancora pending/not_reached
        - incrementa attempts_count in DB
        - setta in_progress
        Ritorna l'attempt_number (= nuovo attempts_count) oppure None se non claimabile.
        """
        pending = self._contact_state_pending()
        not_reached = self._contact_state_not_reached()
        in_progress = self._contact_state_in_progress()

        now = datetime.now(timezone.utc)

        stmt = (
            update(Contact)
            .where(
                Contact.id == contact_id,
                Contact.do_not_call.is_(False),
                Contact.attempts_count < max_attempts,
                Contact.state.in_([pending, not_reached]),
            )
            .values(
                state=in_progress,
                attempts_count=Contact.attempts_count + 1,
                last_attempt_at=now,
                updated_at=now,
            )
            .returning(Contact.attempts_count)
        )

        result = await self._session.execute(stmt)
        row = result.first()

        await self._session._commit()

        if not row:
            return None

        # attempts_count è già incrementato: usalo come attempt_number
        attempt_number = int(row[0])
        return attempt_number

    def _contact_state_not_reached(self):
    # Stato usato per rimettere in coda un contatto che non è stato completato
    # (es. restart/crash o attempt “orfano”).
        return ContactState.NOT_REACHED

    def _contact_state_pending(self):
        return ContactState.PENDING
    
    def _contact_state_in_progress(self):
        return ContactState.IN_PROGRESS
    
    async def _claim_contact_for_attempt(
        self,
        contact_id: UUID,
        eligible_states: list[object],
        max_attempts: int,
        retry_interval_minutes: int,
    ) -> int | None:

        """
        Claim atomico: sposta il contatto in IN_PROGRESS e incrementa attempts_count.

        Ritorna:
            attempt_number (== attempts_count dopo incremento) se il claim riesce,
            altrimenti None (qualcun altro l'ha già preso / non è più eleggibile).
        """
        if update is None or and_ is None or func is None:
            raise RuntimeError("SQLAlchemy is required for the async scheduler.")

        # Retry window: se il contatto è NOT_REACHED, NON deve essere richiamabile prima di retry_interval_minutes
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=retry_interval_minutes)

        stmt = (
            update(Contact)
            .where(
                and_(
                    Contact.id == contact_id,
                    Contact.state.in_(eligible_states),
                    Contact.attempts_count < max_attempts,
                    # Se NOT_REACHED, rispetta il retry window
                    or_(
                        Contact.state != ContactState.NOT_REACHED,
                        Contact.last_attempt_at.is_(None),
                        Contact.last_attempt_at <= cutoff,
                    ),
                )
            )
            .values(
                state=ContactState.IN_PROGRESS,
                attempts_count=Contact.attempts_count + 1,
                last_attempt_at=func.now(),
                updated_at=func.now(),
            )
            .returning(Contact.attempts_count)
        )


        result = await self._session.execute(stmt)
        row = result.first()
        if not row:
            return None

        return int(row[0])


    async def _requeue_stale_in_progress(self, stale_after_minutes: int = 15) -> int:
        """Requeue contacts stuck in IN_PROGRESS.

        Two cases:
        1) Immediate requeue if the current attempt row is missing in call_attempts
           (means we claimed the contact but never persisted the attempt).
        2) Time-based requeue if attempt exists but the contact is stale.
        """
        in_progress = ContactState.IN_PROGRESS
        not_reached = ContactState.NOT_REACHED

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=stale_after_minutes)

        # Case 1: missing attempt row -> requeue immediately (no cutoff gate)
        missing_attempt_stmt = (
            update(Contact)
            .where(Contact.state == in_progress)
            .where(
                ~exists(
                    select(1)
                    .select_from(CallAttempt)
                    .where(CallAttempt.contact_id == Contact.id)
                    .where(CallAttempt.attempt_number == Contact.attempts_count)
                )
            )
            .values(state=not_reached, updated_at=func.now())
            .returning(Contact.id)
        )

        res1 = await self._session.execute(missing_attempt_stmt)
        requeued_missing = res1.scalars().all()

        # Case 2: stale in_progress -> requeue by cutoff
        stale_stmt = (
            update(Contact)
            .where(Contact.state == in_progress)
            .where(
                (Contact.last_attempt_at.is_(None)) | (Contact.last_attempt_at < cutoff)
            )
            .where(Contact.updated_at < cutoff)
            .values(state=not_reached, updated_at=func.now())
            .returning(Contact.id)
        )

        res2 = await self._session.execute(stale_stmt)
        requeued_stale = res2.scalars().all()

        total = len(requeued_missing) + len(requeued_stale)
        if total > 0:
            await self._session.commit()
            logger.info(
                "Requeued in_progress contacts",
                extra={
                    "requeued_total": total,
                    "requeued_missing_attempt": len(requeued_missing),
                    "requeued_stale": len(requeued_stale),
                },
            )
        else:
            await self._session.commit()

        return total

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
        # Safety: se c'erano contatti rimasti in 'in_progress' per restart/crash, li rimettiamo in coda.
        # DOPO: configurabile via env (default 15)
        requeue_minutes = int(os.getenv("SCHEDULER_REQUEUE_STALE_MINUTES", "15"))
        await self._requeue_stale_in_progress(stale_after_minutes=requeue_minutes)
        logger.info("Requeue stale in_progress executed", extra={"stale_after_minutes": requeue_minutes})

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
                retry_interval_minutes=campaign.retry_interval_minutes,
                limit=self._config.batch_size,
            )


            if not contacts:
                logger.debug("No eligible contacts for campaign", extra={"campaign_id": str(campaign.id)})
                continue

            initiated = 0
            eligible_states: list[object] = [ContactState.PENDING, ContactState.NOT_REACHED]

            for contact in contacts[: self._config.max_concurrent_calls]:
                # NB: catturo solo i campi “semplici” (non lazy-load)
                contact_id = contact.id
                phone_number = contact.phone_number
                preferred_language = getattr(contact, "preferred_language", None)

                try:
                    # 1) CLAIM atomico: solo 1 worker/process può riuscire su questo contatto
                    attempt_number = await self._claim_contact_for_attempt(
                        contact_id=contact_id,
                        eligible_states=eligible_states,
                        max_attempts=campaign.max_attempts,
                        retry_interval_minutes=campaign.retry_interval_minutes,
                    )

                    if attempt_number is None:
                        # già preso / non più eleggibile
                        continue

                    call_id = str(uuid4())


                    # Insert idempotente: se esiste già (contact_id, attempt_number) non fa nulla
                    insert_sql = text("""
                    INSERT INTO call_attempts (
                    id, campaign_id, contact_id, attempt_number, call_id, started_at
                    )
                    VALUES (
                    gen_random_uuid(), :campaign_id, :contact_id, :attempt_number, :call_id, :started_at
                    )
                    ON CONFLICT (contact_id, attempt_number) DO NOTHING
                    RETURNING id;
                    """)

                    res = await self._session.execute(
                        insert_sql,
                        {
                            "campaign_id": str(campaign.id),
                            "contact_id": str(contact_id),
                            "attempt_number": attempt_number,
                            "call_id": call_id,
                            "started_at": datetime.now(timezone.utc),
                        },

                    )

                    inserted_id = res.scalar_one_or_none()
                    attempt_id = str(inserted_id) if inserted_id else None
                    if not inserted_id:
                        logger.warning(
                            "Duplicate call_attempt prevented (contact_id=%s attempt_number=%s)",
                            str(contact_id),
                            attempt_number,
                        )
                        # Rimetti subito in coda: era stato claimato ma l'attempt esiste già
                        await self._session.execute(
                            update(Contact)
                            .where(Contact.id == contact_id)
                            .values(
                                state=ContactState.NOT_REACHED,
                                attempts_count=func.greatest(Contact.attempts_count - 1, 0),
                                updated_at=func.now(),
                            )
                        )
                        await self._session.commit()
                        logger.info(
                            "CallAttempt committed before provider call",
                            extra={
                                "campaign_id": str(campaign.id),
                                "contact_id": str(contact_id),
                                "attempt_number": attempt_number,
                                "call_id": call_id,
                                "attempt_id": attempt_id,
                            },
                        )
                        continue



                    # 3) Commit: DB consistente prima di chiamare il provider
                    await self._session.commit()
                    # 4) Initiate call AFTER DB is consistent
                    callback_url = f"{self._callback_base_url}/webhooks/telephony/events"
                    provider_call_id: str | None = None
                    provider_raw_status: str | None = None
                    call_metadata: dict[str, Any] = {}
                    if not self._outbound_number:
                        raise RuntimeError("Missing outbound_number (Twilio from number).")

                    if self._telephony_provider:
                        try:
                            # Preferred path: use the TelephonyProvider interface (REQ-009)
                            req = CallInitiationRequest(
                                to=contact.phone_number,
                                from_number=self._outbound_number or "",
                                callback_url=callback_url,
                                call_id=call_id,
                                campaign_id=campaign.id,
                                contact_id=contact.id,
                                language=getattr(campaign, "language", "it") or "it",
                                metadata={
                                    "attempt_number": attempt_number,
                                },
                            )

                            resp = await self._telephony_provider.initiate_call(req)  # type: ignore[arg-type]
                            provider_call_id = getattr(resp, "provider_call_id", None)
                            provider_raw_status = getattr(getattr(resp, "status", None), "value", None)
                            call_metadata = getattr(resp, "raw_response", {}) or {}

                            logger.info(
                                "Telephony initiate_call done and Outbound call initiated",
                                extra={
                                    "campaign_id": str(campaign.id),
                                    "contact_id": str(contact_id),
                                    "attempt_number": attempt_number,
                                    "call_id": call_id,
                                    "provider_call_id": provider_call_id,
                                    "attempt_id": attempt_id,
                                },
                            )

                            # Persist provider_call_id e metadata per troubleshooting
                            await self._session.execute(
                                text("""
                                    UPDATE call_attempts
                                    SET provider_call_id = :provider_call_id,
                                        provider_raw_status = :provider_raw_status,
                                        metadata = :metadata
                                    WHERE contact_id = :contact_id
                                    AND attempt_number = :attempt_number
                                """),
                                {
                                    "provider_call_id": provider_call_id,
                                    "provider_raw_status": "initiated",
                                    "metadata": json.dumps(call_metadata),
                                    "contact_id": str(contact_id),
                                    "attempt_number": attempt_number,
                                },
                            )
                            await self._session.commit()
                            logger.info(
                                "CallAttempt updated with provider identifiers",
                                extra={
                                    "campaign_id": str(campaign.id),
                                    "contact_id": str(contact_id),
                                    "attempt_number": attempt_number,
                                    "call_id": call_id,
                                    "attempt_id": attempt_id,
                                    "provider_call_id": provider_call_id,
                                    "provider_raw_status": provider_raw_status,
                                },
                            )


                        except TypeError:
                            # Backward-compat: older providers may still accept kwargs
                            provider_call_id = await self._telephony_provider.initiate_call(  # type: ignore[call-arg]
                                to_number=contact.phone_number,
                                from_number=getattr(self._telephony_config, "twilio_from_number", "") or "",
                                callback_url=callback_url,
                                timeout_seconds=self._telephony_config.call_timeout_seconds,
                                metadata={"call_id": call_id, "attempt_number": attempt_number},
                            )
                            provider_raw_status = "initiated"

                            logger.info(
                                "Outbound call initiated (legacy signature)",
                                extra={
                                    "call_id": call_id,
                                    "provider_call_id": provider_call_id,
                                    "contact_id": str(contact.id),
                                    "campaign_id": str(campaign.id),
                                },
                            )

                        # Persist provider_call_id (CRITICAL)
                        await self._session.execute(
                            update(CallAttempt)
                            .where(CallAttempt.call_id == call_id)
                            .values(
                                provider_call_id=provider_call_id,
                                provider_raw_status=provider_raw_status,
                                call_metadata=call_metadata,
                            )
                        )

                    initiated += 1

                except IntegrityError:
                    # Se aggiungi un vincolo UNIQUE (contact_id, attempt_number), qui intercetti il doppione “hard”
                    await self._session.rollback()
                    logger.warning(
                        "Duplicate call attempt prevented by DB constraint",
                        extra={"contact_id": str(contact_id), "campaign_id": str(campaign.id)},
                    )
                    continue

                except Exception as e:
                    await self._session.rollback()
                    logger.exception(
                        "Failed to initiate call",
                        extra={"contact_id": str(contact_id), "campaign_id": str(campaign.id)},
                    )
                    error_code = getattr(e, "error_code", None)
                    provider_resp = getattr(e, "provider_response", None)

                    await self._session.execute(
                        update(CallAttempt)
                        .where(CallAttempt.call_id == call_id)
                        .values(
                            outcome=CallOutcome.FAILED.value,
                            error_code=str(error_code) if error_code else "CALL_INIT_FAILED",
                            provider_raw_status="failed",
                            call_metadata={
                                "error": str(e),
                                "provider_response": provider_resp or {},
                            },
                        )
                    )
                    await self._session.commit()
                     

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
        eligible_states = [ContactState.PENDING, ContactState.NOT_REACHED]

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
        if not SQLALCHEMY_AVAILABLE:
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
        retry_interval_minutes: int,
        limit: int,
    ) -> list[Contact]:

        """Get contacts eligible for calling."""
        if not SQLALCHEMY_AVAILABLE:
            raise RuntimeError("SQLAlchemy is required for the async scheduler.")
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=retry_interval_minutes)

        stmt = (
            select(Contact)
            .where(
                and_(
                    Contact.campaign_id == campaign_id,
                    Contact.state.in_([ContactState.PENDING, ContactState.NOT_REACHED]),
                    Contact.attempts_count < max_attempts,
                    Contact.do_not_call.is_(False),
                    # Se NOT_REACHED, rispetta retry window anche in selezione
                    or_(
                        Contact.state != ContactState.NOT_REACHED,
                        Contact.last_attempt_at.is_(None),
                        Contact.last_attempt_at <= cutoff,
                    ),
                )
            )
            .order_by(Contact.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _update_contact_state(self, contact_id: UUID, state: object, increment_attempts: bool) -> None:
        """Update contact state in database (no commit; caller controls transaction)."""
        if update is None:
            raise RuntimeError("SQLAlchemy is required for the async scheduler.")

        values: dict[str, object] = {"state": state}
        if increment_attempts:
            values["attempts_count"] = func.coalesce(Contact.attempts_count, 0) + 1  # type: ignore[operator]

        stmt = update(Contact).where(Contact.id == contact_id).values(**values)
        await self._session.execute(stmt)
        await self._session.flush()


    
    
    


