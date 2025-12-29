"""
FastAPI router for telephony webhook endpoints.

FASE ORA: deterministic single-flow LLM-driven voice dialogue for outbound survey calls.

Key constraints:
- Twilio must always receive <2s response
- No complex logic in webhook
- No multiple redirects: only controlled poll loop
- Single source of truth: call_attempts.metadata JSONB
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any, Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calls.repository import CallAttemptRepository
from app.campaigns.models import Campaign
from app.shared.database import get_db_session, get_database_manager
from app.shared.logging import get_logger

from app.dialogue.persistence import SurveyPersistenceService
from app.dialogue.models import DialogueSession, CallContext, CapturedAnswer, ConsentState
from app.calls.models import CallOutcome

from app.dialogue.llm.factory import create_llm_gateway
from app.dialogue.llm.models import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    SurveyContext,
    ControlSignal,
    LLMProvider,
)
from app.telephony.config import get_telephony_config
from app.telephony.twilio_adapter import TwilioTelephonyControl
from app.telephony.factory import get_telephony_provider as build_provider
from app.telephony.interface import TelephonyProvider
from app.telephony.webhooks.handler import WebhookHandler

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/telephony", tags=["webhooks"])

# ----------------------------
# LLM + Integration (singleton)
# ----------------------------

_llm_singleton = None

def _get_llm_gateway():
    global _llm_singleton
    if _llm_singleton is not None:
        return _llm_singleton

    provider_str = (os.environ.get("LLM_PROVIDER") or "openai").lower().strip()
    provider = LLMProvider.OPENAI if provider_str == "openai" else LLMProvider.ANTHROPIC
    _llm_singleton = create_llm_gateway(provider=provider)
    return _llm_singleton


# ----------------------------
# Voice state (single source of truth: CallAttempt.metadata)
# ----------------------------

VOICE_KEY = "voice_convo_v1"
import os
from urllib.parse import urlencode

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

def _public_url(request: Request, path: str, qs: dict[str, str]) -> str:
    q = urlencode(qs)
    if PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL}{path}?{q}"

    # fallback: usa request, ma forza https se host sembra pubblico
    base = str(request.base_url).rstrip("/")  # es: http://127.0.0.1:8880
    host = request.headers.get("host", "")
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)

    # euristica: devtunnels / endpoint pubblici -> https
    if scheme != "https" and ("devtunnels.ms" in host or "ngrok" in host or "trycloudflare" in host):
        scheme = "https"
        base = base.replace("http://", "https://")

    return f"{base}{path}?{q}"


@dataclass(frozen=True)
class VoiceTurnResult:
    assistant_text: str
    end_call: bool
    updated_state: dict[str, Any]

def _now_ms() -> int:
    return int(time.time() * 1000)

def _get_metadata(attempt) -> dict[str, Any]:
    # model field is call_metadata but older code sometimes refers to extra_metadata
    md = getattr(attempt, "call_metadata", None) or getattr(attempt, "extra_metadata", None) or {}
    if not isinstance(md, dict):
        return {}
    return md

def _set_metadata(attempt, md: dict[str, Any]) -> None:
    if hasattr(attempt, "call_metadata"):
        attempt.call_metadata = md
        return
    if hasattr(attempt, "extra_metadata"):
        attempt.extra_metadata = md
        return
    # fallback
    setattr(attempt, "call_metadata", md)

def _init_voice_state_if_missing(md: dict[str, Any]) -> dict[str, Any]:
    state = md.get(VOICE_KEY)
    if isinstance(state, dict):
        return state

    state = {
        "phase": "consent",                # consent | q1 | q2 | q3 | done | refused | failed
        "current_question": 0,             # 0=consent, 1..3
        "collected_answers": [],           # list[str] answers (q1..q3)
        "turn_seq": 0,                     # monotonic
        "last_user_text": "",
        "last_assistant_text": "",
        "silence_count": 0,
        "reprompt_count": 0,
        "poll_count": 0,
        "pending": {                       # turn pipeline
            "status": "idle",              # idle|queued|running|done|failed
            "turn_seq": 0,
            "queued_at_ms": 0,
            "started_at_ms": 0,
            "done_at_ms": 0,
            "assistant_text": "",
            "signals": [],
            "captured_answer": None,
            "error": None,
        },
    }
    md[VOICE_KEY] = state
    return state

def _twiml(s: str) -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n' + s + "\n</Response>"

def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )



def _abs_base(request: Request) -> str:
    """
    Public base URL reachable by Twilio.

    Priority:
      1) env PUBLIC_BASE_URL (recommended)
      2) X-Forwarded-Proto / X-Forwarded-Host (when behind tunnel/proxy)
      3) request.base_url (last resort)

    Deterministic rule:
      - devtunnels MUST be https. If a devtunnels URL is http, force https.
    """
    env_base = (os.getenv("PUBLIC_BASE_URL") or "").strip()

    def _force_https_if_devtunnels(url: str) -> str:
        u = url.strip().rstrip("/")
        if ".devtunnels.ms" in u and u.startswith("http://"):
            return "https://" + u[len("http://") :]
        return u

    if env_base:
        return _force_https_if_devtunnels(env_base)

    xf_proto = (request.headers.get("x-forwarded-proto") or "").strip()
    xf_host = (request.headers.get("x-forwarded-host") or "").strip()
    if xf_host:
        proto = xf_proto or "https"
        return _force_https_if_devtunnels(f"{proto}://{xf_host}")

    return _force_https_if_devtunnels(str(request.base_url))

def _make_url(request: Request, path: str, qs: dict[str, str]) -> str:
    base = _abs_base(request)
    q = urlencode({k: v for k, v in qs.items() if v is not None and str(v) != ""})
    if q:
        return f"{base}{path}?{q}"
    return f"{base}{path}"

# Per-call lock to avoid race between concurrent Twilio retries
_LOCKS: dict[str, asyncio.Lock] = {}

def _get_lock(key: str) -> asyncio.Lock:
    lock = _LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _LOCKS[key] = lock
    return lock


# ----------------------------
# Existing /events remains (scheduler/status callbacks)
# ----------------------------

ProviderFactory = Any

def get_telephony_provider() -> TelephonyProvider:
    return build_provider()

def get_webhook_handler(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Any:
    return WebhookHandler(session=session)

@router.post("/events", status_code=status.HTTP_200_OK)
async def receive_webhook_event(
    request: Request,
    provider: Annotated[TelephonyProvider, Depends(get_telephony_provider)],
    handler: Annotated[Any, Depends(get_webhook_handler)],
) -> Any:
    # Twilio status callbacks must never break the call flow.
    # Build payload deterministically from form + query params.
    try:
        form = dict(await request.form())
    except Exception:
        form = {}

    payload = dict(form)
    payload.update(dict(request.query_params))

    try:
        event = provider.parse_webhook_event(payload)
        await handler.handle_event(event)
    except Exception:
        logger.exception("Failed to process webhook event (ACKing 200 to Twilio)")

    return {"ok": True}



def _build_dialogue_session_for_persistence(attempt: Any, campaign: Campaign, state: dict[str, Any]) -> DialogueSession:
    """
    Build a DialogueSession compatible with REQ-014 persistence service.
    Deterministic mapping from voice state -> DialogueSession.captured_answers.
    """
    ds = DialogueSession()

    ctx = CallContext(
        call_id=str(getattr(attempt, "call_id")),
        campaign_id=getattr(attempt, "campaign_id"),
        contact_id=getattr(attempt, "contact_id"),
        call_attempt_id=getattr(attempt, "id"),
        language=str(campaign.language.value) if getattr(campaign, "language", None) else None,
        intro_script=campaign.intro_script or None,
        question_1_text=campaign.question_1_text,
        question_1_type=str(campaign.question_1_type.value) if getattr(campaign, "question_1_type", None) else None,
        question_2_text=campaign.question_2_text,
        question_2_type=str(campaign.question_2_type.value) if getattr(campaign, "question_2_type", None) else None,
        question_3_text=campaign.question_3_text,
        question_3_type=str(campaign.question_3_type.value) if getattr(campaign, "question_3_type", None) else None,
    )
    # keep both for backward compatibility
    ds.call_context = ctx
    ds.context = ctx

    phase = str(state.get("phase") or "consent")
    if phase == "refused":
        ds.consent_state = ConsentState.REFUSED
    elif phase in ("q1", "q2", "q3", "done"):
        ds.consent_state = ConsentState.GIVEN
    else:
        ds.consent_state = ConsentState.PENDING

    answers = state.get("collected_answers") or []
    if not isinstance(answers, list):
        answers = []

    q_texts = [
        str(campaign.question_1_text),
        str(campaign.question_2_text),
        str(campaign.question_3_text),
    ]

    captured: list[CapturedAnswer] = []
    for i in range(3):
        if i < len(answers) and str(answers[i]).strip():
            captured.append(
                CapturedAnswer(
                    question_index=i + 1,
                    question_text=q_texts[i],
                    answer_text=str(answers[i]),
                    confidence=None,
                )
            )

    ds.captured_answers = captured
    return ds


async def _persist_terminal_outcome_once(
    session: AsyncSession,
    attempt: Any,
    campaign: Campaign,
    state: dict[str, Any],
) -> None:
    """
    Persist terminal outcomes (done/refused/failed) once, idempotently.
    Uses state flag state['persisted'] to avoid double writes on Twilio retries.
    """
    if state.get("persisted") is True:
        return

    phase = str(state.get("phase") or "")
    ds = _build_dialogue_session_for_persistence(attempt, campaign, state)

    svc = SurveyPersistenceService()

    # Terminal persistence:
    # - done -> create survey_response + set call outcome completed
    # - refused -> set call outcome refused
    # - failed -> set call outcome failed (minimal, no survey_response)
    if phase == "done":
        # REQ-014 service requires exactly 3 captured answers
        res = await svc.persist_completed_survey(session=session, dialogue_session=ds)
        if not res.success:
            # If persistence fails, do not mark persisted; next retry may succeed
            raise RuntimeError(f"persist_completed_survey failed: {res.error_message}")

        attempt.outcome = CallOutcome.COMPLETED
        # ended_at is set by service; keep consistency but ensure ended_at exists
        if getattr(attempt, "ended_at", None) is None:
            from datetime import datetime, timezone
            attempt.ended_at = datetime.now(timezone.utc)

    elif phase == "refused":
        res = await svc.persist_refused_survey(session=session, dialogue_session=ds)
        if not res.success:
            raise RuntimeError(f"persist_refused_survey failed: {res.error_message}")

        attempt.outcome = CallOutcome.REFUSED
        if getattr(attempt, "ended_at", None) is None:
            from datetime import datetime, timezone
            attempt.ended_at = datetime.now(timezone.utc)

    elif phase == "failed":
        attempt.outcome = CallOutcome.FAILED
        if getattr(attempt, "ended_at", None) is None:
            from datetime import datetime, timezone
            attempt.ended_at = datetime.now(timezone.utc)

    else:
        # Not terminal -> nothing
        return

    # Mark idempotency flag in metadata
    md = _get_metadata(attempt)
    state["persisted"] = True
    md[VOICE_KEY] = state
    _set_metadata(attempt, md)

    await session.flush()

# ----------------------------
# NEW: single-flow voice endpoint (ENTRY / TURN / POLL)
# ----------------------------

async def _load_attempt_and_campaign(
    session: AsyncSession,
    call_id: str | None,
    call_sid: str | None,
    campaign_id: str | None,
) -> tuple[Any, Campaign]:
    attempt_repo = CallAttemptRepository(session)

    attempt = None
    if call_id:
        attempt = await attempt_repo.get_by_call_id(call_id)
    if attempt is None and call_sid:
        attempt = await attempt_repo.get_by_provider_call_id(call_sid)

    if attempt is None:
        raise HTTPException(status_code=404, detail="CallAttempt not found")

    # Ensure provider_call_id is set early for resilience
    if call_sid and getattr(attempt, "provider_call_id", None) in (None, ""):
        attempt.provider_call_id = call_sid
        await session.flush()

    # Campaign
    if campaign_id:
        try:
            from uuid import UUID
            cid = UUID(str(campaign_id))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid campaign_id: {e}") from e
        res = await session.execute(select(Campaign).where(Campaign.id == cid))
        campaign = res.scalar_one_or_none()
    else:
        res = await session.execute(select(Campaign).where(Campaign.id == attempt.campaign_id))
        campaign = res.scalar_one_or_none()

    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return attempt, campaign


def _build_survey_context(campaign: Campaign, state: dict[str, Any]) -> SurveyContext:
    current_q = int(state.get("current_question", 0))
    collected = state.get("collected_answers") or []
    if not isinstance(collected, list):
        collected = []

    return SurveyContext(
        campaign_name=campaign.name or "Survey",
        language=str(campaign.language.value) if getattr(campaign, "language", None) else "it",
        intro_script=campaign.intro_script or "",
        question_1_text=campaign.question_1_text,
        question_1_type=str(campaign.question_1_type.value),
        question_2_text=campaign.question_2_text,
        question_2_type=str(campaign.question_2_type.value),
        question_3_text=campaign.question_3_text,
        question_3_type=str(campaign.question_3_type.value),
        current_question=current_q,
        collected_answers=[str(x) for x in collected],
    )


def _apply_llm_to_state(
    state: dict[str, Any],
    assistant_text: str,
    signals: list[ControlSignal],
    captured_answer: str | None,
) -> VoiceTurnResult:
    """
    Deterministic state transition based on parsed LLM signals.
    This is the core logic we unit test (no DB).
    """
    new_state = dict(state)
    new_state["last_assistant_text"] = assistant_text

    phase = str(new_state.get("phase", "consent"))
    current_q = int(new_state.get("current_question", 0))
    collected = new_state.get("collected_answers") or []
    if not isinstance(collected, list):
        collected = []
    silence_count = int(new_state.get("silence_count", 0))
    reprompt_count = int(new_state.get("reprompt_count", 0))

    sigset = set(signals)

    # Consent refused -> end call
    if ControlSignal.CONSENT_REFUSED in sigset:
        new_state["phase"] = "refused"
        new_state["current_question"] = 0
        return VoiceTurnResult(assistant_text=assistant_text, end_call=True, updated_state=new_state)

    # Consent accepted -> move to Q1
    if ControlSignal.CONSENT_ACCEPTED in sigset and current_q == 0:
        new_state["phase"] = "q1"
        new_state["current_question"] = 1
        new_state["reprompt_count"] = 0
        new_state["silence_count"] = 0
        return VoiceTurnResult(assistant_text=assistant_text, end_call=False, updated_state=new_state)

    # Repeat question / unclear -> don't advance; cap reprompts deterministically
    if ControlSignal.REPEAT_QUESTION in sigset or ControlSignal.UNCLEAR_RESPONSE in sigset:
        reprompt_count += 1
        new_state["reprompt_count"] = reprompt_count
        # hard cap: 2 reprompts -> fail-safe end
        if reprompt_count >= 2:
            new_state["phase"] = "failed"
            return VoiceTurnResult(
                assistant_text="Va bene, la ringrazio per il tempo. Arrivederci.",
                end_call=True,
                updated_state=new_state,
            )
        return VoiceTurnResult(assistant_text=assistant_text, end_call=False, updated_state=new_state)

    # Answer captured -> store answer (for current question 1..3)
    if ControlSignal.ANSWER_CAPTURED in sigset and current_q in (1, 2, 3):
        if captured_answer:
            # ensure list length
            while len(collected) < current_q:
                collected.append("")
            collected[current_q - 1] = captured_answer
            new_state["collected_answers"] = collected

    # Move to next question
    if ControlSignal.MOVE_TO_NEXT_QUESTION in sigset and current_q in (1, 2, 3):
        next_q = current_q + 1
        if next_q > 3:
            new_state["phase"] = "done"
            new_state["current_question"] = 3
            return VoiceTurnResult(assistant_text=assistant_text, end_call=True, updated_state=new_state)
        new_state["current_question"] = next_q
        new_state["phase"] = f"q{next_q}"
        new_state["reprompt_count"] = 0
        new_state["silence_count"] = 0
        return VoiceTurnResult(assistant_text=assistant_text, end_call=False, updated_state=new_state)

    # Survey complete
    if ControlSignal.SURVEY_COMPLETE in sigset:
        new_state["phase"] = "done"
        return VoiceTurnResult(assistant_text=assistant_text, end_call=True, updated_state=new_state)

    # No strong signal -> keep phase, keep going (turn-based)
    return VoiceTurnResult(assistant_text=assistant_text, end_call=False, updated_state=new_state)


async def _run_llm_turn(call_id: str, provider_call_sid: str) -> None:
    lock_key = (provider_call_sid or call_id) or "unknown"
    lock = _get_lock(lock_key)

    # -------- FASE A: prende dati + marca running (NO LLM qui) ----------
    dbm = get_database_manager()

    async with lock:
        async with dbm.session() as session:
            attempt_repo = CallAttemptRepository(session)

            attempt = None
            if call_id:
                attempt = await attempt_repo.get_by_call_id(call_id)
            if attempt is None and provider_call_sid:
                attempt = await attempt_repo.get_by_provider_call_id(provider_call_sid)
            if attempt is None:
                logger.warning("LLM worker: attempt not found", extra={"call_id": call_id, "call_sid": provider_call_sid})
                return

            md = _get_metadata(attempt)
            state = _init_voice_state_if_missing(md)

            pending = state.get("pending") or {}
            if pending.get("status") not in ("queued", "running"):
                return

            turn_seq = int(pending.get("turn_seq", 0))
            user_text = str(state.get("last_user_text") or "").strip() or "[NO_INPUT]"
            logger.info("llm_running", extra={"turn_seq": turn_seq})
            # mark running (idempotente)
            pending["status"] = "running"
            pending["started_at_ms"] = pending.get("started_at_ms") or _now_ms()
            state["pending"] = pending
            md[VOICE_KEY] = state
            _set_metadata(attempt, md)
            await session.flush()

            campaign_id = attempt.campaign_id  # salva fuori lock
            attempt_id = str(attempt.id)
            call_id_db = str(attempt.call_id)
            provider_call_id_db = str(attempt.provider_call_id or provider_call_sid or "")
            

    # -------- FASE B: LLM fuori lock ----------
    try:
        async with dbm.session() as session:
            # carica campaign (fuori lock, ok)
            res = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = res.scalar_one_or_none()

        if campaign is None:
            raise RuntimeError("Campaign not found")

        llm = _get_llm_gateway()

        # survey_ctx lo ricostruisco qui (non tocca DB)
        # Nota: se _build_survey_context usa solo campaign+state, serve state.
        # Per semplicità, ricostruisco state in FASE C prima di applicare, e qui passo solo user_text.
        req = ChatRequest(
            messages=[
                ChatMessage(role=MessageRole.SYSTEM, content=""),
                ChatMessage(role=MessageRole.USER, content=user_text),
            ],
            survey_context=_build_survey_context(campaign, {}),  # se ti serve state, spostalo in FASE C
            temperature=0.2,
            max_tokens=350,
        )

        resp = await llm.chat_completion(req)
        assistant_text = resp.content
        control_signals = resp.control_signals
        captured_answer = resp.captured_answer

    except Exception as e:
        assistant_text = ""
        control_signals = []
        captured_answer = None
        err_repr = repr(e)

        # -------- FASE C (failed): scrive errore sotto lock ----------
        async with lock:
            async with dbm.session() as session:
                attempt_repo = CallAttemptRepository(session)
                attempt = await attempt_repo.get_by_call_id(call_id_db)  # garantito esistere
                if attempt is None:
                    return

                md = _get_metadata(attempt)
                state = _init_voice_state_if_missing(md)
                pending = state.get("pending") or {}

                # scrivi failed solo se è ancora lo stesso turno
                if int(pending.get("turn_seq", 0)) == turn_seq:
                    pending["status"] = "failed"
                    pending["done_at_ms"] = _now_ms()
                    pending["error"] = err_repr
                    state["pending"] = pending
                    md[VOICE_KEY] = state
                    _set_metadata(attempt, md)
                    await session.flush()
        logger.exception("LLM worker failed", extra={"call_id": call_id_db, "turn_seq": turn_seq})
        return

    # -------- FASE C (done): applica e salva sotto lock ----------
    async with lock:
        async with dbm.session() as session:
            attempt_repo = CallAttemptRepository(session)
            attempt = await attempt_repo.get_by_call_id(call_id_db)
            if attempt is None:
                return

            md = _get_metadata(attempt)
            state = _init_voice_state_if_missing(md)
            pending = state.get("pending") or {}

            # se nel frattempo è cambiato turno, NON sovrascrivere
            if int(pending.get("turn_seq", 0)) != turn_seq:
                return

            # se ti serve state per survey_ctx/logic, qui hai lo state aggiornato
            # Applica output LLM a state
            result = _apply_llm_to_state(
                state=state,
                assistant_text=assistant_text,
                signals=control_signals,
                captured_answer=captured_answer,
            )

            pending["status"] = "done"
            pending["done_at_ms"] = _now_ms()
            pending["assistant_text"] = result.assistant_text
            pending["signals"] = [s.value for s in control_signals]
            pending["captured_answer"] = captured_answer
            pending["error"] = None

            new_state = result.updated_state
            new_state["pending"] = pending

            md[VOICE_KEY] = new_state
            _set_metadata(attempt, md)
            await session.flush()
    

@router.post("/voice")
async def voice(request: Request, session: Annotated[AsyncSession, Depends(get_db_session)]) -> Any:
    qs = request.query_params
    mode = (qs.get("mode") or "entry").lower().strip()

    form: dict[str, Any] = {}
    try:
        form = dict(await request.form())
    except Exception:
        form = {}

    logger.info(
        "VOICE webhook",
        extra={
            "mode": mode,
            "call_sid": (form.get("CallSid") or ""),
            "speech": (form.get("SpeechResult") or "")[:80],
        },
    )

    call_sid = (form.get("CallSid") or form.get("call_sid") or "").strip()
    call_id = (qs.get("call_id") or form.get("call_id") or "").strip() or None
    campaign_id = (qs.get("campaign_id") or "").strip() or None

    base_path = "/webhooks/telephony/voice"
    md: dict[str, Any] = {}
    state: dict[str, Any] = {}

    # ---- SAFE FALLBACKS: mai lasciare Twilio appeso
    def _safe_twiml_hangup(msg: str = "C'è stato un errore interno. Arrivederci.") -> Response:
        tw = f"""
  <Say language="it-IT">{_xml_escape(msg)}</Say>
  <Hangup />
"""
        return Response(content=_twiml(tw), media_type="application/xml")

    def _safe_twiml_retry(request: Request, url: str) -> Response:
        # risposta super-rapida e poi redirect (evita timeout 15s Twilio)
        tw = f"""
  <Pause length="1" />
  <Redirect method="POST">{_xml_escape(url)}</Redirect>
"""
        return Response(content=_twiml(tw), media_type="application/xml")

    # init vars (evita UnboundLocalError in qualunque ramo)
    attempt = None
    campaign = None


    lock_key = call_sid or (call_id or "unknown")
    lock = _get_lock(lock_key)

    async with lock:
        # 1) LOAD attempt/campaign in modo protetto
        try:
            attempt, campaign = await _load_attempt_and_campaign(session, call_id, call_sid, campaign_id)
            md = _get_metadata(attempt)
            state = _init_voice_state_if_missing(md)
        except Exception:
            logger.exception(
                "VOICE failed before state init (returning safe TwiML)",
                extra={"mode": mode, "call_id": call_id, "call_sid": call_sid},
            )
            
            logger.exception("VOICE failed (returning safe TwiML)", extra={...})
            tw = """ ... """
            return Response(content=_twiml(tw), media_type="application/xml")
        
        common_qs = {
            "call_id": str(attempt.call_id),
            "campaign_id": str(attempt.campaign_id),
        }

        if mode == "entry":
            state["phase"] = "consent"
            state["current_question"] = 0
            state["turn_seq"] = int(state.get("turn_seq", 0))
            state["reprompt_count"] = 0
            state["silence_count"] = 0
            state["poll_count"] = 0
            state["pending"]["status"] = "idle"

            md[VOICE_KEY] = state
            _set_metadata(attempt, md)

            try:
                await session.flush()
            except Exception:
                logger.exception("DB flush failed in mode=entry (continuing)")

            action_url = _public_url(request, base_path, {**common_qs, "mode": "turn"})

            # NB: Gather non self-close, per compatibilità Twilio (evita stranezze)
            tw = f"""
  <Say language="it-IT">{_xml_escape(campaign.intro_script or "Salve. Posso farle un breve sondaggio?")}</Say>
  <Gather input="speech dtmf" action="{_xml_escape(action_url)}" method="POST" language="it-IT" timeout="5" speechTimeout="auto">
    <Say language="it-IT">Dica sì per iniziare, oppure no per rifiutare.</Say>
  </Gather>
"""
            return Response(content=_twiml(tw), media_type="application/xml")

        if mode == "turn":
            speech = (form.get("SpeechResult") or "").strip()
            digits = (form.get("Digits") or "").strip()
            user_text = speech or digits or ""

            turn_seq = int(state.get("turn_seq", 0)) + 1
            state["turn_seq"] = turn_seq
            state["last_user_text"] = user_text

            if not user_text:
                state["silence_count"] = int(state.get("silence_count", 0)) + 1

            state["pending"] = {
                "status": "queued",
                "turn_seq": turn_seq,
                "queued_at_ms": _now_ms(),
                "started_at_ms": 0,
                "done_at_ms": 0,
                "assistant_text": "",
                "signals": [],
                "captured_answer": None,
                "error": None,
            }
            state["poll_count"] = 0

            md[VOICE_KEY] = state
            _set_metadata(attempt, md)

            asyncio.create_task(
                _run_llm_turn(call_id=str(attempt.call_id), provider_call_sid=str(attempt.provider_call_id or call_sid))
            )

            poll_url = _public_url(request, base_path, {**common_qs, "mode": "poll"})
            tw = f"""
  <Say language="it-IT">Ok.</Say>
  <Pause length="1" />
  <Redirect method="POST">{_xml_escape(poll_url)}</Redirect>
"""
            try:
                await session.flush()
            except Exception:
                logger.exception("DB flush failed in mode=turn (continuing)")

            return Response(content=_twiml(tw), media_type="application/xml")

        if mode == "poll":
            # 2) POLL deve essere bulletproof: mai crash, mai lento
            try:
                if not state:
                    tw = """
            <Say language="it-IT">C'è stato un errore interno. Arrivederci.</Say>
            <Hangup />
            """
                    return Response(content=_twiml(tw), media_type="application/xml")
    
                pending = state.get("pending") or {}
                status_p = pending.get("status") or "idle"

                state["poll_count"] = int(state.get("poll_count", 0)) + 1

                # cap polling
                if state["poll_count"] > 6:
                    return _safe_twiml_hangup("Non riesco a completare ora. La ringrazio per il tempo. Arrivederci.")

                # salva poll_count ma non far mai fallire la risposta Twilio
                try:
                    md[VOICE_KEY] = state
                    _set_metadata(attempt, md)
                    await session.flush()
                except Exception:
                    logger.exception("DB flush failed in mode=poll (continuing)")

                if status_p != "done":
                    poll_url = _public_url(request, base_path, {**common_qs, "mode": "poll"})
                    return _safe_twiml_retry(request, poll_url)

                assistant_text = str(pending.get("assistant_text") or "").strip() or "Ok."
                next_action = _public_url(request, base_path, {**common_qs, "mode": "turn"})

                tw = f"""
  <Say language="it-IT">{_xml_escape(assistant_text)}</Say>
  <Gather input="speech dtmf" action="{_xml_escape(next_action)}" method="POST" language="it-IT" timeout="6" speechTimeout="auto" />
"""
                return Response(content=_twiml(tw), media_type="application/xml")

            except Exception:
                logger.exception(
                    "VOICE poll failed (returning safe TwiML)",
                    extra={"mode": mode, "call_id": str(attempt.call_id), "call_sid": call_sid},
                )
                # IMPORTANTISSIMO: qui NON tocchi md/state
                poll_url = _public_url(request, base_path, {**common_qs, "mode": "poll"})
                return _safe_twiml_retry(request, poll_url)

        # mode sconosciuto
        return _safe_twiml_hangup("Richiesta non valida. Arrivederci.")
