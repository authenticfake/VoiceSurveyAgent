"""
Webhook event handler for processing telephony events.

REQ-010: Telephony webhook handler
"""

from typing import Any, Protocol
from uuid import UUID

import json
import time
from pathlib import Path

import redis.asyncio as redis

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.calls.models import CallAttempt, CallOutcome
from app.contacts.models import Contact, ContactOutcome, ContactState
from app.shared.logging import get_logger
from app.telephony.events import CallEvent, CallEventType
from app.config import get_settings
from app.dialogue.llm.factory import create_llm_gateway
from app.dialogue.llm.models import ChatMessage, ChatRequest, LLMProvider


logger = get_logger(__name__)

_REDIS: redis.Redis | None = None


async def _get_redis() -> redis.Redis:
    global _REDIS
    if _REDIS is not None:
        return _REDIS
    settings = get_settings()
    _REDIS = redis.from_url(settings.redis_url, decode_responses=True)
    return _REDIS


def _rk_call_meta(call_sid: str) -> str:
    return f"call:{call_sid}:meta"


def _rk_call_transcript(call_sid: str) -> str:
    return f"call:{call_sid}:transcript"


async def _redis_call_meta_get(call_sid: str) -> dict:
    r = await _get_redis()
    return await r.hgetall(_rk_call_meta(call_sid))


async def _redis_transcript_get(call_sid: str, limit: int = 2000) -> list[dict]:
    r = await _get_redis()
    raw = await r.lrange(_rk_call_transcript(call_sid), max(0, -limit), -1)
    out: list[dict] = []
    for item in raw:
        try:
            out.append(json.loads(item))
        except Exception:
            continue
    return out


def _call_artifacts_dir(call_id: str) -> Path:
    settings = get_settings()
    base = Path(settings.call_artifacts_dir)
    safe_call_id = re.sub(r"[^a-zA-Z0-9_-]", "_", call_id)
    return base / safe_call_id


def _read_transcript_fallback(call_id: str) -> str:
    p = _call_artifacts_dir(call_id) / "transcript.txt"
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _coerce_outcome(value: str) -> str:
    v = (value or "").strip().lower()
    mapping = {
        "completed": "completed",
        "consent_declined": "consent_declined",
        "not_reached": "not_reached",
        "busy": "busy",
        "failed": "failed",
        "callback_requested": "callback_requested",
    }
    return mapping.get(v, "failed")


async def _post_call_finalize(call_attempt: CallAttempt, meta: dict) -> tuple[str, dict]:
    call_sid = call_attempt.call_sid or ""
    call_id = str(call_attempt.id)

    rows = await _redis_transcript_get(call_sid) if call_sid else []
    if rows:
        lines = []
        for r in rows:
            role = (r.get("role") or "").upper()
            text = (r.get("text") or "").strip()
            if text:
                lines.append(f"{role}: {text}")
        transcript_text = "\n".join(lines)
    else:
        transcript_text = _read_transcript_fallback(call_id)

    last_signal = meta.get("last_signal") or ""
    last_signal_at = meta.get("last_signal_at") or ""

    system = (
        "Sei un motore di post-call analysis per una chiamata di survey. "
        "Dato il transcript, devi determinare l'OUTCOME finale della chiamata e produrre un breve riassunto. "
        "Rispondi ESCLUSIVAMENTE con un JSON valido (niente testo fuori dal JSON).\n\n"
        "Schema JSON richiesto:\n"
        "{\n"
        '  "final_outcome": one of [completed, consent_declined, not_reached, busy, failed, callback_requested],\n'
        '  "summary": string (max 400 chars),\n'
        '  "callback_datetime_iso": string|null,\n'
        '  "evidence": { "quotes": [string, ...] }\n'
        "}\n\n"
        "Regole:\n"
        "- Se l'utente chiede esplicitamente di essere richiamato in un momento specifico -> callback_requested.\n"
        "- Se l'utente rifiuta il consenso -> consent_declined.\n"
        "- Se transcript è vuoto/inutile -> not_reached o failed (scegli il più plausibile).\n"
        "- Usa last_signal se utile ma NON fidarti solo di quello."
    )

    user = (
        f"call_id={call_id}\n"
        f"call_sid={call_sid}\n"
        f"last_signal_at={last_signal_at}\n"
        f"last_signal={last_signal}\n\n"
        f"TRANSCRIPT:\n{transcript_text}"
    )

    gateway = create_llm_gateway()
    req = ChatRequest(
        adapter_type=LLMProvider.OPENAI,
        model=os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-mini"),
        messages=[
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user),
        ],
        temperature=0,
        max_tokens=400,
    )
    resp = await gateway.chat_completion(req)

    raw = (resp.content or "").strip()
    m = re.search(r"\{.*\}", raw, flags=re.S)
    payload = {}
    if m:
        try:
            payload = json.loads(m.group(0))
        except Exception:
            payload = {}

    final_outcome = _coerce_outcome(str(payload.get("final_outcome") or "failed"))
    patch = {
        "post_call": {
            "final_outcome": final_outcome,
            "summary": payload.get("summary"),
            "callback_datetime_iso": payload.get("callback_datetime_iso"),
            "evidence": payload.get("evidence"),
            "raw": raw[:2000],
        },
        "meta": {
            "last_signal": last_signal,
            "last_signal_at": last_signal_at,
        },
    }
    return final_outcome, patch

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
def _event_get(event, *names, default=None):
    for n in names:
        v = getattr(event, n, None)
        if v is not None:
            return v
    payload = getattr(event, "payload", None) or getattr(event, "raw", None)
    if isinstance(payload, dict):
        for n in names:
            if n in payload and payload[n] is not None:
                return payload[n]
    return default

def _attempt_metadata(attempt: Any) -> dict[str, Any]:
    # ordine di fallback: call_metadata -> metadata -> {}
    val = getattr(attempt, "call_metadata", None)
    if val is None:
        val = getattr(attempt, "metadata", None)
    if isinstance(val, dict):
        return val
    return {}

def _attempt_metadata_get(call_attempt: Any) -> dict:
    meta = getattr(call_attempt, "extra_metadata", None)
    if meta is None:
        meta = getattr(call_attempt, "call_metadata", None)
    return meta or {}


def _attempt_metadata_set(call_attempt: Any, meta: dict) -> None:
    if hasattr(call_attempt, "extra_metadata"):
        call_attempt.extra_metadata = meta
    elif hasattr(call_attempt, "call_metadata"):
        call_attempt.call_metadata = meta

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
        logger.info(
            "Processing telephony event",
            extra={
                "call_id": event.call_id,
                "provider_call_id": event.provider_call_id,
                "event_type": event.event_type.value,
            },
        )
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
                    "provider_call_id": event.provider_call_id,
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
        metadata = _attempt_metadata_get(call_attempt)
        processed_events = metadata.get("processed_events", [])
        return event_type.value in processed_events

    async def _mark_event_processed(self, call_attempt: CallAttempt, event_type: str) -> None:
        metadata = dict(_attempt_metadata_get(call_attempt))
        processed = dict(metadata.get("processed_events", {}))
        processed[event_type] = True
        metadata["processed_events"] = processed
        _attempt_metadata_set(call_attempt, metadata)


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
        call_attempt.provider_raw_status =_event_get(
            event,
            "raw_status", "provider_raw_status", "call_status", "status",
            "CallStatus", "Status",
            default=call_attempt.provider_raw_status,
        )
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
        call_attempt.provider_raw_status = _event_get(
            event,
            "raw_status", "provider_raw_status", "call_status", "status",
            "CallStatus", "Status",
            default=call_attempt.provider_raw_status,
        )

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
        call_attempt.provider_raw_status = _event_get(
            event,
            "raw_status", "provider_raw_status", "call_status", "status",
            "CallStatus", "Status",
            default=call_attempt.provider_raw_status,
        )

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

        Qui facciamo il finalize post-call (Decisione 2):
        - outcome finale (da last SIGNAL + transcript)
        - summary finale (se abilitata)
        - transcript_ref / artifact path
        - update contatto in modo compatibile con enum DB contact_outcome
        """
        call_attempt.ended_at = event.timestamp
        call_attempt.provider_raw_status = _event_get(
            event,
            "raw_status",
            "provider_raw_status",
            "call_status",
            "status",
            "CallStatus",
            "Status",
            default=call_attempt.provider_raw_status,
        )

        # duration -> metadata
        if event.duration_seconds is not None:
            md = dict(call_attempt.call_metadata or {})
            md["duration_seconds"] = event.duration_seconds
            call_attempt.call_metadata = md

        # ---- POST-CALL FINALIZE (idempotente) ----
        # Non facciamo fallire l'evento completed se il finalize fallisce:
        # meglio chiudere telephony e loggare, poi si può rilanciare manualmente.
        try:
            call_md = dict(call_attempt.call_metadata or {})
            final_outcome_str, call_md = await _post_call_finalize(call_attempt, call_md)

            # outcome finale sull'attempt
            final_outcome = _coerce_outcome(final_outcome_str)
            if final_outcome is not None:
                call_attempt.outcome = final_outcome
            call_attempt.call_metadata = call_md

            # update contact state/outcome (compat DB)
            await self._apply_final_outcome_to_contact(
                contact_id=call_attempt.contact_id,
                final_outcome=call_attempt.outcome,
                call_metadata=call_md,
            )

        except Exception:
            log.exception(
                "post-call finalize failed (continuing). call_id=%s attempt_id=%s",
                call_attempt.call_id,
                call_attempt.id,
            )
            # fallback: la chiamata è comunque avvenuta -> COMPLETED “coarse”
            await self._update_contact_state(
                contact_id=call_attempt.contact_id,
                state=ContactState.COMPLETED,
                last_outcome=ContactOutcome.COMPLETED,
            )

        await self._mark_event_processed(call_attempt, event.event_type)

    async def _apply_final_outcome_to_contact(
        self,
        *,
        contact_id: UUID,
        final_outcome: CallOutcome | None,
        call_metadata: dict[str, object],
    ) -> None:
        """Mappa outcome (CallOutcome) -> (ContactState, ContactOutcome) compatibili col DB."""
        state: ContactState = ContactState.COMPLETED
        last_outcome: ContactOutcome = ContactOutcome.COMPLETED

        if final_outcome == CallOutcome.CONSENT_DECLINED:
            state = ContactState.REFUSED
            last_outcome = ContactOutcome.NOT_REACHED
        elif final_outcome == CallOutcome.CALLBACK_REQUESTED:
            state = ContactState.CALLBACK_PENDING
            last_outcome = ContactOutcome.NOT_REACHED
        elif final_outcome in (CallOutcome.NO_ANSWER, CallOutcome.BUSY, CallOutcome.FAILED):
            state = ContactState.NOT_REACHED
            last_outcome = ContactOutcome.NOT_REACHED
        elif final_outcome in (CallOutcome.CONSENTED, CallOutcome.COMPLETED):
            state = ContactState.COMPLETED
            last_outcome = ContactOutcome.COMPLETED

        await self._update_contact_state(
            contact_id=contact_id,
            state=state,
            last_outcome=last_outcome,
        )

        # opzionale ma utile: dettagli in extra_metadata (non rompe schema)
        try:
            contact = await self.contact_repo.get_by_id(contact_id)
            extra = dict(getattr(contact, "extra_metadata", None) or {})
            extra["final_call_outcome"] = final_outcome.value if final_outcome else None
            extra["final_signal"] = call_metadata.get("final_signal")
            extra["summary"] = call_metadata.get("summary")
            extra["transcript_ref"] = call_metadata.get("transcript_ref") or call_metadata.get("transcript_path")
            contact.extra_metadata = extra
            await self.contact_repo.save(contact)
        except Exception:
            log.exception("failed to persist contact.extra_metadata (continuing). contact_id=%s", contact_id)

    async def _handle_no_answer(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        call_attempt.ended_at = event.timestamp
        call_attempt.outcome = CallOutcome.NO_ANSWER
        await self._update_contact_state(
            contact_id=call_attempt.contact_id,
            state=ContactState.NOT_REACHED,
            last_outcome=ContactOutcome.NOT_REACHED,
        )
        await self._mark_event_processed(call_attempt, event.event_type)

    async def _handle_busy(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        call_attempt.ended_at = event.timestamp
        call_attempt.outcome = CallOutcome.BUSY
        await self._update_contact_state(
            contact_id=call_attempt.contact_id,
            state=ContactState.NOT_REACHED,
            last_outcome=ContactOutcome.NOT_REACHED,
        )
        await self._mark_event_processed(call_attempt, event.event_type)

    async def _handle_failed(
        self,
        call_attempt: CallAttempt,
        event: CallEvent,
    ) -> None:
        call_attempt.ended_at = event.timestamp
        call_attempt.outcome = CallOutcome.FAILED
        await self._update_contact_state(
            contact_id=call_attempt.contact_id,
            state=ContactState.NOT_REACHED,
            last_outcome=ContactOutcome.NOT_REACHED,
        )
        await self._mark_event_processed(call_attempt, event.event_type)

    async def _update_contact_state(
        self,
        contact_id: UUID,
        state: ContactState,
        last_outcome: ContactOutcome,
    ) -> None:
        contact = await self.contact_repo.get_by_id(contact_id)
        contact.state = state
        contact.last_outcome = last_outcome.value  # enum DB contact_outcome
        await self.contact_repo.save(contact)

    async def _mark_event_processed(self, call_attempt: CallAttempt, event_type: CallEventType) -> None:
        processed = set(call_attempt.processed_events or [])
        processed.add(event_type.value)
        call_attempt.processed_events = sorted(processed)
        await self.call_attempt_repo.save(call_attempt)


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
        call_attempt.provider_raw_status = _event_get(
            event,
            "raw_status", "provider_raw_status", "call_status", "status",
            "CallStatus", "Status",
            default=call_attempt.provider_raw_status,
        )

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
        call_attempt.provider_raw_status = _event_get(
            event,
            "raw_status", "provider_raw_status", "call_status", "status",
            "CallStatus", "Status",
            default=call_attempt.provider_raw_status,
        )

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
        call_attempt.provider_raw_status = _event_get(
            event,
            "raw_status", "provider_raw_status", "call_status", "status",
            "CallStatus", "Status",
            default=call_attempt.provider_raw_status,
        )

        call_attempt.error_code = event.error_code
        await self._mark_event_processed(call_attempt, event.event_type)

        # Store error message in metadata
        if event.error_message:
            metadata = dict(call_attempt.call_metadata or {})
            metadata["error_message"] = event.error_message
            if hasattr(call_attempt, "extra_metadata"):
                call_attempt.extra_metadata = metadata
            elif hasattr(call_attempt, "call_metadata"):
                call_attempt.call_metadata = metadata
            else:
                call_attempt.metadata = metadata

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