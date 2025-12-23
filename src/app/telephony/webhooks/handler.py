"""
Webhook event handler for processing telephony events.

REQ-010: Telephony webhook handler
"""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.calls.models import CallAttempt, CallOutcome
from app.contacts.models import Contact, ContactState
from app.shared.logging import get_logger
from app.telephony.events import CallEvent, CallEventType

logger = get_logger(__name__)

class DialogueStarterProtocol(Protocol):
    """Protocol for dialogue orchestrator to start dialogue on call.answered."""

    async def start_dialogue(
        self,
        call_id: str,
        campaign_id: UUID,
        contact_id: UUID,
    ) -> None:
        """Start dialogue for an answered call."""
        ...

class WebhookHandler:
    """Handler for processing telephony webhook events.

    Processes CallEvent objects and updates database state accordingly.
    Handles idempotency via call_id to prevent duplicate processing.
    """

    def __init__(
        self,
        session: AsyncSession,
        dialogue_starter: DialogueStarterProtocol | None = None,
    ) -> None:
        """Initialize webhook handler.

        Args:
            session: Async database session.
            dialogue_starter: Optional dialogue orchestrator for call.answered events.
        """
        self._session = session
        self._dialogue_starter = dialogue_starter
        self._processed_events: set[str] = set()

    async def handle_event(self, event: CallEvent) -> bool:
        """Handle a telephony call event.

        Processes the event and updates database state. Handles idempotency
        by checking if the event has already been processed for this call_id
        and event_type combination.

        Args:
            event: Parsed CallEvent from webhook.

        Returns:
            True if event was processed, False if it was a duplicate.
        """
        # Create idempotency key from call_id and event_type
        idempotency_key = f"{event.call_id}:{event.event_type.value}"

        # Check in-memory cache first (for same-request duplicates)
        if idempotency_key in self._processed_events:
            logger.info(
                "Duplicate event skipped (in-memory)",
                extra={
                    "call_id": event.call_id,
                    "event_type": event.event_type.value,
                },
            )
            return False

        # Check database for existing processing
        call_attempt = await self._get_call_attempt(event.call_id)
        if call_attempt is None:
            logger.warning(
                "CallAttempt not found for event",
                extra={
                    "call_id": event.call_id,
                    "event_type": event.event_type.value,
                },
            )
            return False

        # Check if this event type has already been processed
        if await self._is_event_processed(call_attempt, event.event_type):
            logger.info(
                "Duplicate event skipped (database)",
                extra={
                    "call_id": event.call_id,
                    "event_type": event.event_type.value,
                },
            )
            return False

        # Process based on event type
        logger.info(
            "Processing telephony event",
            extra={
                "call_id": event.call_id,
                "event_type": event.event_type.value,
                "provider_call_id": event.provider_call_id,
            },
        )

        match event.event_type:
            case CallEventType.INITIATED:
                await self._handle_initiated(call_attempt, event)
            case CallEventType.RINGING:
                await self._handle_ringing(call_attempt, event)
            case CallEventType.ANSWERED:
                await self._handle_answered(call_attempt, event)
            case CallEventType.COMPLETED:
                await self._handle_completed(call_attempt, event)
            case CallEventType.NO_ANSWER:
                await self._handle_no_answer(call_attempt, event)
            case CallEventType.BUSY:
                await self._handle_busy(call_attempt, event)
            case CallEventType.FAILED:
                await self._handle_failed(call_attempt, event)

        # Mark as processed
        self._processed_events.add(idempotency_key)

        # Commit changes
        await self._session.commit()

        return True

    async def _get_call_attempt(self, call_id: str) -> CallAttempt | None:
        """Get CallAttempt by internal call_id.

        Args:
            call_id: Internal call identifier.

        Returns:
            CallAttempt if found, None otherwise.
        """
        stmt = select(CallAttempt).where(CallAttempt.call_id == call_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _is_event_processed(
        self,
        call_attempt: CallAttempt,
        event_type: CallEventType,
    ) -> bool:
        """Check if event type has already been processed for this call.

        Uses the call attempt's metadata to track processed events.

        Args:
            call_attempt: The call attempt record.
            event_type: Event type to check.

        Returns:
            True if already processed.
        """
        metadata = call_attempt.extra_metadata or {}
        processed_events = metadata.get("processed_events", [])
        return event_type.value in processed_events

    async def _mark_event_processed(
        self,
        call_attempt: CallAttempt,
        event_type: CallEventType,
    ) -> None:
        """Mark event type as processed in call attempt metadata.

        Args:
            call_attempt: The call attempt record.
            event_type: Event type to mark.
        """
        metadata = dict(call_attempt.extra_metadata or {})
        processed_events = list(metadata.get("processed_events", []))
        if event_type.value not in processed_events:
            processed_events.append(event_type.value)
        metadata["processed_events"] = processed_events
        call_attempt.extra_metadata = metadata

    async def _handle_initiated(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        """Handle call.initiated event.

        Args:
            call_attempt: The call attempt record.
            event: The call event.
        """
        call_attempt.provider_raw_status = event.raw_status
        await self._mark_event_processed(call_attempt, event.event_type)

    async def _handle_ringing(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        """Handle call.ringing event.

        Args:
            call_attempt: The call attempt record.
            event: The call event.
        """
        call_attempt.provider_raw_status = event.raw_status
        await self._mark_event_processed(call_attempt, event.event_type)

    async def _handle_answered(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        """Handle call.answered event.

        Updates call attempt with answered timestamp and triggers
        dialogue start if dialogue_starter is configured.

        Args:
            call_attempt: The call attempt record.
            event: The call event.
        """
        call_attempt.answered_at = event.timestamp
        call_attempt.provider_raw_status = event.raw_status
        await self._mark_event_processed(call_attempt, event.event_type)

        # Trigger dialogue start
        if self._dialogue_starter is not None:
            logger.info(
                "Triggering dialogue start",
                extra={
                    "call_id": event.call_id,
                    "campaign_id": str(event.campaign_id),
                    "contact_id": str(event.contact_id),
                },
            )
            await self._dialogue_starter.start_dialogue(
                call_id=event.call_id,
                campaign_id=event.campaign_id,
                contact_id=event.contact_id,
            )

    async def _handle_completed(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        """Handle call.completed event.

        Note: This handles the telephony-level completion. Survey completion
        is handled separately by the dialogue orchestrator.

        Args:
            call_attempt: The call attempt record.
            event: The call event.
        """
        call_attempt.ended_at = event.timestamp
        call_attempt.provider_raw_status = event.raw_status

        # Store duration in metadata
        if event.duration_seconds is not None:
            metadata = dict(call_attempt.extra_metadata or {})
            metadata["duration_seconds"] = event.duration_seconds
            call_attempt.extra_metadata = metadata

        await self._mark_event_processed(call_attempt, event.event_type)

    async def _handle_no_answer(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        """Handle call.no_answer event.

        Updates call attempt outcome and contact state.

        Args:
            call_attempt: The call attempt record.
            event: The call event.
        """
        call_attempt.ended_at = event.timestamp
        call_attempt.outcome = CallOutcome.NO_ANSWER
        call_attempt.provider_raw_status = event.raw_status
        await self._mark_event_processed(call_attempt, event.event_type)

        # Update contact state
        await self._update_contact_state(
            contact_id=event.contact_id,
            state=ContactState.NOT_REACHED,
            last_outcome=CallOutcome.NO_ANSWER,
        )

    async def _handle_busy(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        """Handle call.busy event.

        Updates call attempt outcome and contact state.

        Args:
            call_attempt: The call attempt record.
            event: The call event.
        """
        call_attempt.ended_at = event.timestamp
        call_attempt.outcome = CallOutcome.BUSY
        call_attempt.provider_raw_status = event.raw_status
        await self._mark_event_processed(call_attempt, event.event_type)

        # Update contact state
        await self._update_contact_state(
            contact_id=event.contact_id,
            state=ContactState.NOT_REACHED,
            last_outcome=CallOutcome.BUSY,
        )

    async def _handle_failed(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        """Handle call.failed event.

        Updates call attempt with error information and contact state.

        Args:
            call_attempt: The call attempt record.
            event: The call event.
        """
        call_attempt.ended_at = event.timestamp
        call_attempt.outcome = CallOutcome.FAILED
        call_attempt.provider_raw_status = event.raw_status
        call_attempt.error_code = event.error_code
        await self._mark_event_processed(call_attempt, event.event_type)

        # Store error message in metadata
        if event.error_message:
            metadata = dict(call_attempt.extra_metadata or {})
            metadata["error_message"] = event.error_message
            call_attempt.extra_metadata = metadata

        # Update contact state
        await self._update_contact_state(
            contact_id=event.contact_id,
            state=ContactState.NOT_REACHED,
            last_outcome=CallOutcome.FAILED,
        )

    async def _update_contact_state(
        self,
        contact_id: UUID,
        state: ContactState,
        last_outcome: CallOutcome,
    ) -> None:
        """Update contact state and last outcome.

        Args:
            contact_id: Contact UUID.
            state: New contact state.
            last_outcome: Last call outcome.
        """
        stmt = (
            update(Contact)
            .where(Contact.id == contact_id)
            .values(
                state=state,
                last_outcome=last_outcome.value,
            )
        )
        await self._session.execute(stmt)