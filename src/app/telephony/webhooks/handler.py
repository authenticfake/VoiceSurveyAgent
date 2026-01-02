# BEGIN FILE: src/app/telephony/webhooks/handler.py
"""Telephony webhook event handler.

Responsibilities
- Update CallAttempt lifecycle fields (started_at, ended_at, provider status).
- Finalize persistence exactly once (single choke point):
    - read artifacts from filesystem (transcript/realtime)
    - read realtime SIGNAL + hints from Redis (if enabled)
    - persist outcome/summary/transcript references into DB (call_attempt.call_metadata)
    - update Contact state/outcome in a way that does NOT clobber dialogue truth

Key rule
Dialogue/orchestrator is the source of truth for survey outcomes
(REFUSED / SURVEY_COMPLETED / CALLBACK_REQUESTED).
Telephony completion events must NOT overwrite a non-null CallAttempt.outcome already set by dialogue.

We still allow a fallback inference (e.g. no_answer/busy/failed) when outcome is missing.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.calls.models import CallAttempt, CallOutcome
from app.config import get_settings
from app.contacts.models import Contact, ContactOutcome, ContactState
from app.shared.logging import get_logger
from app.telephony.events import CallEvent, CallEventType

LOG = get_logger(__name__)


# -----------------------------
# Helpers
# -----------------------------
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso_z() -> str:
    return _utc_now().isoformat(timespec="seconds").replace("+00:00", "Z")


def _event_get(event: CallEvent, *keys: str, default: Any = None) -> Any:
    """Fetch first present key from event.payload (tries original/lower/upper)."""
    payload = event.payload or {}
    for k in keys:
        if k in payload:
            return payload[k]
        kl = k.lower()
        ku = k.upper()
        if kl in payload:
            return payload[kl]
        if ku in payload:
            return payload[ku]
    return default


def _artifacts_root() -> Path:
    # Keep same default convention as router.py
    base = os.getenv("VSA_CALL_ARTIFACTS_DIR", "var/calls")
    return Path(base)


def _call_artifacts_dir(call_id: UUID | str) -> Path:
    return _artifacts_root() / str(call_id)


def _safe_read_text(path: Path, max_chars: int = 400_000) -> str:
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
        return txt[:max_chars]
    except FileNotFoundError:
        return ""
    except Exception:
        LOG.exception("Failed reading text file: %s", path)
        return ""


def _extract_signal_from_text(text: str) -> Optional[str]:
    """Extract a one-    SIGNAL from transcript (best-effort)."""
    if not text:
        return None
    m = re.search(r"SIGNAL:\s*\{.*?\}", text, flags=re.MULTILINE)
    if not m:
        return None
    return ("SIGNAL: " + m.group(1).strip()).strip()


def _infer_outcome_if_missing(event: CallEvent, call_attempt: CallAttempt) -> Optional[CallOutcome]:
    """Infer telephony-level outcome only if dialogue didn't already set one."""
    if call_attempt.outcome is not None:
        return None

    et = event.event_type
    if et == CallEventType.NO_ANSWER:
        return CallOutcome.NO_ANSWER
    if et == CallEventType.BUSY:
        return CallOutcome.BUSY
    if et == CallEventType.FAILED:
        return CallOutcome.FAILED
    if et == CallEventType.CANCELED:
        return CallOutcome.CANCELED
    if et in (CallEventType.COMPLETED, CallEventType.STOPPED):
        # telephony completed but no dialogue-level outcome -> generic completed
        return CallOutcome.COMPLETED
    return None


def _map_call_outcome_to_contact(outcome: CallOutcome) -> tuple[ContactState, ContactOutcome]:
    """Translate CallOutcome to (ContactState, ContactOutcome)."""
    if outcome == CallOutcome.SURVEY_COMPLETED:
        return (ContactState.COMPLETED, ContactOutcome.COMPLETED)
    if outcome == CallOutcome.REFUSED:
        return (ContactState.REFUSED, ContactOutcome.REFUSED)
    if outcome == CallOutcome.CALLBACK_REQUESTED:
        # Non è "completed", ma è un esito positivo “operativo”
        return (ContactState.COMPLETED, ContactOutcome.COMPLETED)

    if outcome == CallOutcome.NO_ANSWER:
        return (ContactState.NOT_REACHED, ContactOutcome.NO_ANSWER)
    if outcome == CallOutcome.BUSY:
        return (ContactState.NOT_REACHED, ContactOutcome.BUSY)
    if outcome == CallOutcome.FAILED:
        return (ContactState.NOT_REACHED, ContactOutcome.FAILED)
    if outcome == CallOutcome.CANCELED:
        return (ContactState.NOT_REACHED, ContactOutcome.CANCELED)

    return (ContactState.NOT_REACHED, ContactOutcome.NOT_REACHED)


def _try_parse_json(value: str) -> Optional[dict[str, Any]]:
    try:
        return json.loads(value)
    except Exception:
        return None


async def _redis_get_call_meta(call_id: str) -> dict[str, str]:
    """Fetch redis hash call:meta:<call_id> if Redis configured; else {}.

    Router writes:
      - call:meta:<call_id> -> signal (JSON str)
    """
    settings = get_settings()
    if not (settings.redis_enabled and settings.redis_url):
        return {}

    try:
        import redis.asyncio as redis  # type: ignore
    except Exception:
        LOG.warning("redis not available (missing dependency). Skipping redis meta read.")
        return {}

    try:
        client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        key = f"call:meta:{call_id}"
        meta: dict[str, str] = await client.hgetall(key)
        # non close() hard: redis client is lightweight; but we can disconnect politely
        try:
            await client.aclose()
        except Exception:
            pass
        return meta or {}
    except Exception:
        LOG.exception("Failed reading redis call meta for call_id=%s", call_id)
        return {}


def _infer_outcome_from_signal(signal_obj: dict[str, Any]) -> Optional[CallOutcome]:
    """Best-effort mapping from SIGNAL JSON to CallOutcome.

    We support flexible shapes:
      { "outcome": "refused" | "survey_completed" | "callback_requested" ... }
      { "consent": true/false }
      { "callback": {...} } or { "callback_at": "..."} etc.
    """
    outcome_raw = (signal_obj.get("outcome") or signal_obj.get("call_outcome") or "").strip().lower()
    if outcome_raw:
        mapping = {
            "refused": CallOutcome.REFUSED,
            "declined": CallOutcome.REFUSED,
            "survey_completed": CallOutcome.SURVEY_COMPLETED,
            "completed": CallOutcome.SURVEY_COMPLETED,
            "callback_requested": CallOutcome.CALLBACK_REQUESTED,
            "callback": CallOutcome.CALLBACK_REQUESTED,
            "no_answer": CallOutcome.NO_ANSWER,
            "busy": CallOutcome.BUSY,
            "failed": CallOutcome.FAILED,
            "canceled": CallOutcome.CANCELED,
        }
        if outcome_raw in mapping:
            return mapping[outcome_raw]

    # consent false => refused
    if "consent" in signal_obj and signal_obj.get("consent") in (False, "false", "no", "NO", 0):
        return CallOutcome.REFUSED

    # callback hints => callback requested
    if any(k in signal_obj for k in ("callback", "callback_at", "callback_time", "callback_when")):
        return CallOutcome.CALLBACK_REQUESTED

    return None


# -----------------------------
# Handler
# -----------------------------
class WebhookHandler:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle_event(self, event: CallEvent) -> bool:
        """Handle a webhook event.

        Returns True if handled (even if idempotently), False if unknown call_id.
        """
        call_attempt = await self._load_call_attempt(event.call_id)
        if call_attempt is None:
            LOG.warning("Webhook event for unknown call_id=%s type=%s", event.call_id, event.event_type)
            return False

        # Idempotency guard: don't re-handle same event type
        if self._is_event_processed(call_attempt, event.event_type.value):
            LOG.info("Skipping already-processed event=%s call_id=%s", event.event_type, event.call_id)
            return True

        if event.event_type == CallEventType.ANSWERED:
            await self._handle_answered(call_attempt, event)
        elif event.event_type in (
            CallEventType.COMPLETED,
            CallEventType.STOPPED,
            CallEventType.FAILED,
            CallEventType.NO_ANSWER,
            CallEventType.BUSY,
            CallEventType.CANCELED,
        ):
            await self._handle_terminal(call_attempt, event)
        else:
            await self._handle_non_terminal(call_attempt, event)

        self._mark_event_processed(call_attempt, event.event_type.value)
        await self._session.commit()
        return True

    # -------- DB loaders --------
    async def _load_call_attempt(self, call_id: str) -> Optional[CallAttempt]:
        try:
            uuid = UUID(call_id)
        except Exception:
            return None
        return await self._session.get(CallAttempt, uuid)

    async def _load_contact(self, contact_id: UUID) -> Optional[Contact]:
        return await self._session.get(Contact, contact_id)

    # -------- processed flags --------
    def _is_event_processed(self, call_attempt: CallAttempt, event_type: str) -> bool:
        meta = dict(call_attempt.call_metadata or {})
        processed: Iterable[str] = meta.get("processed_events") or []
        return event_type in set(processed)

    def _mark_event_processed(self, call_attempt: CallAttempt, event_type: str) -> None:
        meta = dict(call_attempt.call_metadata or {})
        processed = list(meta.get("processed_events") or [])
        if event_type not in processed:
            processed.append(event_type)
        meta["processed_events"] = processed
        call_attempt.call_metadata = meta

    # -------- event handlers --------
    async def _handle_answered(self, call_attempt: CallAttempt, event: CallEvent) -> None:
        call_attempt.started_at = event.timestamp or call_attempt.started_at or _utc_now()
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

        contact = await self._load_contact(call_attempt.contact_id)
        if contact:
            contact.state = ContactState.IN_PROGRESS
            contact.last_attempt_at = call_attempt.started_at
            contact.attempts_count = (contact.attempts_count or 0) + 1

    async def _handle_non_terminal(self, call_attempt: CallAttempt, event: CallEvent) -> None:
        # Store provider status for observability
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

    async def _handle_terminal(self, call_attempt: CallAttempt, event: CallEvent) -> None:
        """Terminal events: update outcome + finalize artifacts + update contact.

        This is the SINGLE choke point for final persistence.
        """
        call_attempt.ended_at = event.timestamp or call_attempt.ended_at or _utc_now()
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

        # 1) If dialogue already set an outcome, keep it.
        # 2) Else try to derive from Redis SIGNAL JSON
        # 3) Else infer from telephony event type (no_answer/busy/failed/etc.)
        await self._maybe_apply_signal_outcome(call_attempt)

        inferred = _infer_outcome_if_missing(event, call_attempt)
        if inferred is not None:
            call_attempt.outcome = inferred

        # duration metadata
        if event.duration_seconds is not None:
            meta = dict(call_attempt.call_metadata or {})
            meta["duration_seconds"] = event.duration_seconds
            call_attempt.call_metadata = meta

        # Finalize artifacts into DB (idempotent)
        await self._finalize_persistence(call_attempt)

        # Update contact state based on final outcome
        if call_attempt.outcome is not None:
            await self._apply_outcome_to_contact(call_attempt)

    async def _maybe_apply_signal_outcome(self, call_attempt: CallAttempt) -> None:
        """Read redis signal JSON (if any) and apply outcome ONLY if outcome is missing."""
        if call_attempt.outcome is not None:
            return

        redis_meta = await _redis_get_call_meta(str(call_attempt.id))
        signal_raw = (redis_meta.get("signal") or "").strip()
        if not signal_raw:
            return

        signal_obj = _try_parse_json(signal_raw)
        if not signal_obj:
            # Store raw anyway for debugging
            meta = dict(call_attempt.call_metadata or {})
            meta["signal_raw"] = signal_raw[:2000]
            call_attempt.call_metadata = meta
            return

        inferred = _infer_outcome_from_signal(signal_obj)
        meta = dict(call_attempt.call_metadata or {})
        meta["signal_json"] = signal_obj
        meta["signal_raw"] = signal_raw[:2000]
        call_attempt.call_metadata = meta

        if inferred is not None:
            call_attempt.outcome = inferred

    async def _finalize_persistence(self, call_attempt: CallAttempt) -> None:
        """Single-point finalize:
        - FS: transcript/realtime jsonl paths + excerpt
        - SIGNAL: prefer redis JSON if present; else extract from transcript text line
        - summary_text: deterministic placeholder (or derived from signal), can be improved later
        """
        meta = dict(call_attempt.call_metadata or {})
        if meta.get("finalized_at"):
            return

        call_dir = _call_artifacts_dir(call_attempt.id)
        transcript_path = call_dir / "transcript.txt"
        realtime_jsonl_path = call_dir / "realtime.jsonl"

        transcript_text = _safe_read_text(transcript_path)
        signal_line_from_transcript = _extract_signal_from_text(transcript_text)

        # Attach FS references (paths are very useful in prod debugging)
        meta["artifacts_dir"] = str(call_dir)
        if transcript_path.exists():
            meta["transcript_path"] = str(transcript_path)
            meta["transcript_chars"] = len(transcript_text)
            meta["transcript_excerpt"] = transcript_text[:4000]
        if realtime_jsonl_path.exists():
            meta["realtime_jsonl_path"] = str(realtime_jsonl_path)

        # Prefer redis SIGNAL JSON if present in call_metadata (set by _maybe_apply_signal_outcome)
        signal_raw = (meta.get("signal_raw") or "").strip()
        if signal_raw and "signal_text" not in meta:
            # Keep a human-friendly version too
            meta["signal_text"] = f"SIGNAL: {signal_raw}"

        if (not meta.get("signal_text")) and signal_line_from_transcript:
            meta["signal_text"] = signal_line_from_transcript

        # summary_text: keep deterministic, avoid LLM here (per tuo desiderata tuning dopo)
        if "summary_text" not in meta:
            # If signal JSON exists, keep compact summary
            if isinstance(meta.get("signal_json"), dict):
                meta["summary_text"] = json.dumps(meta["signal_json"], ensure_ascii=False)[:2000]
            else:
                meta["summary_text"] = meta.get("signal_text") or ""

        meta["finalized_at"] = _utc_now_iso_z()
        call_attempt.call_metadata = meta

    async def _apply_outcome_to_contact(self, call_attempt: CallAttempt) -> None:
        contact = await self._load_contact(call_attempt.contact_id)
        if not contact or call_attempt.outcome is None:
            return

        state, last_outcome = _map_call_outcome_to_contact(call_attempt.outcome)

        contact.state = state
        contact.last_outcome = last_outcome
        contact.last_attempt_at = call_attempt.ended_at or contact.last_attempt_at

