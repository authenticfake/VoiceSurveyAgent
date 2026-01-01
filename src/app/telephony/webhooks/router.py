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
from datetime import datetime, timezone
from pathlib import Path
import re

import json
import os
import time
import inspect
import base64


from dataclasses import dataclass
from typing import Any, Annotated, Optional, Mapping
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, WebSocket, WebSocketDisconnect

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calls.repository import CallAttemptRepository
from app.campaigns.models import Campaign
from app.contacts.models import Contact
from app.shared.database import get_db_session, get_database_manager
from app.shared.logging import get_logger

from app.dialogue.persistence import SurveyPersistenceService
from app.dialogue.models import DialogueSession, CallContext, CapturedAnswer, ConsentState
from app.dialogue.llm.openai_adapter import OpenAIRealtimeSession

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
from app.config import get_settings
import logging

logger = get_logger(__name__)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logging.getLogger("websockets.server").setLevel(logging.WARNING)

router = APIRouter(prefix="/webhooks/telephony", tags=["webhooks"])

settings = get_settings()

_SIGNAL_RE = re.compile(r"(?:^|\n)\s*SIGNAL:\s*(\{.*?\})\s*(?:\n|$)", re.DOTALL)



def _read_text_file_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        logger.exception("Failed to read prompt file: %s", path)
        return ""

def _call_artifacts_dir(call_id: str) -> Path:
    settings = get_settings()
    base = Path(settings.call_artifacts_dir)
    safe_call_id = re.sub(r"[^a-zA-Z0-9_-]", "_", call_id)
    return base / safe_call_id


def _ensure_call_artifacts_dir(call_id: str) -> Path:
    d = _call_artifacts_dir(call_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _append_transcript_line(call_id: str, role: str, text: str) -> None:
    d = _ensure_call_artifacts_dir(call_id)
    p = d / "transcript.txt"
    with p.open("a", encoding="utf-8") as f:
        f.write(f"{role}: {text.strip()}\n")


def _rk_call_transcript(call_sid: str) -> str:
    return f"call:{call_sid}:transcript"


async def _redis_transcript_append(call_sid: str, role: str, text: str) -> None:
    r = await _get_redis()
    key = _rk_call_transcript(call_sid)
    now_ms = int(time.time() * 1000)
    await r.rpush(
        key,
        json.dumps({"t_ms": now_ms, "role": role, "text": text}, ensure_ascii=False),
    )
    await r.expire(key, 3600)


async def _redis_transcript_get(call_sid: str, limit: int = 2000) -> list[dict]:
    r = await _get_redis()
    key = _rk_call_transcript(call_sid)
    raw = await r.lrange(key, max(0, -limit), -1)
    out: list[dict] = []
    for item in raw:
        try:
            out.append(json.loads(item))
        except Exception:
            continue
    return out

def _render_placeholders(template: str, mapping: dict[str, str]) -> str:
    """
    Replace placeholders in the form ${table.field} with mapping values.
    Unresolved placeholders are replaced with empty string (but logged once).
    """
    unresolved: set[str] = set()

    def repl(m: re.Match[str]) -> str:
        key = m.group(1).strip()
        if key in mapping:
            return mapping[key]
        unresolved.add(key)
        return ""

    out = re.sub(r"\$\{([^}]+)\}", repl, template)
    if unresolved:
        logger.warning("Prompt has unresolved placeholders: %s", sorted(unresolved))
    return out


async def _redis_call_meta_set_signal(call_sid: str, signal_json: str) -> None:
    r = await _get_redis()
    key = f"call:{call_sid}:meta"
    now_ms = int(time.time() * 1000)
    await r.hset(
        key,
        mapping={
            "last_signal_at_ms": str(now_ms),
            "last_signal_json": signal_json,
        },
    )
    await r.expire(key, 3600)


async def _build_campaign_instructions(
    campaign_id: str,
    contact_id: str,
    language: str,
) -> str:
    """
    Build runtime instructions for OpenAI Realtime.
    Priority:
      1) campaigns.intro_script (if set and non-empty)
      2) bundled campaign_call_system.md

    Then append SIGNAL protocol rules.
    """
    # Load DB objects (keep it simple, no new abstractions now)
    dbm = get_database_manager()
    async with dbm.session() as session:
        campaign = await session.get(Campaign, campaign_id)
        contact = await session.get(Contact, contact_id)

    campaign_script = ""
    # bundled markdown shipped with the repo
    prompt_path = Path(__file__).resolve().parents[2] / "dialogue" / "llm" / "prompts" /"campaign_call_system.md"
    # NOTE: adjust this path if your repo stores it elsewhere
    campaign_script = _read_text_file_safely(prompt_path).strip()

    # Basic placeholder mapping (extend later without breaking retro-compat)
    mapping: dict[str, str] = {
        "campaigns.id": campaign_id,
        "campaigns.name": (campaign.name if campaign else "") or "",
        "campaigns.description": (campaign.description if campaign else "") or "",
        "campaigns.language": (str(campaign.language) if campaign else "") or "",
        "campaigns.intro_script": (campaign.intro_script if campaign else "") or "",
        "contacts.id": contact_id,
        "users.name": (campaign.name if campaign else "") or "",
        "contacts.name": (contact.name if contact else "") or "",
        "contacts.phone_number": (contact.phone_number if contact else "") or "",
        "contacts.preferred_language": (contact.preferred_language if contact else "en") or "",
        "runtime.language": language or "",
        "runtime.now_iso": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
    }

    rendered = _render_placeholders(campaign_script, mapping).strip()
    logger.info("Campaign instructions:\n%s", rendered)
    # Append SIGNAL protocol (Livello A)
    signal_rules = f"""
--- CONTROL SIGNALS (machine-readable) ---
You MUST emit CONTROL SIGNALS in TEXT modality only (never speak them aloud).
When the user asks for a callback (e.g. "richiamami domani alle 16"), or you infer a final outcome,
emit exactly ONE line:

SIGNAL: {{"type":"callback_requested","when":"<ISO_OR_NATURAL_LANGUAGE>","confidence":0.0-1.0}}

Other allowed types:
- "refused"
- "completed"
- "hangup_early"

**RULES**
Emit SIGNAL ONLY as TEXT output, exactly on one line, starting with SIGNAL:.
Emit SIGNAL as VOICE output is forbidden / Prohibited /Banned.
**Outputting a SIGNAL is mandatory** if the VOICE output is to be low, almost whisper-like.
Do NOT output multiple SIGNAL lines for the same turn.
Do NOT include extra commentary on the SIGNAL line.
"""

    return (rendered + "\n\n" + signal_rules).strip()

async def parse_telephony_event(
    *,
    provider: Any,
    request: Request,
    payload: dict[str, Any],
) -> Any:
    """
    Deterministic event parsing via provider.
    We don't assume an exact signature; we adapt at runtime.
    """
    # --- Correlation fields live in query params (not in Twilio payload) ---
    qp = request.query_params

    # Copy into payload if missing
    for key in ("call_id", "campaign_id", "contact_id", "language", "attempt_number"):
        v = qp.get(key)
        if v is not None and v != "" and key not in payload:
            payload[key] = v

    if "attempt_number" in payload:
        try:
            payload["attempt_number"] = int(payload["attempt_number"])
        except Exception:
            pass

    parse_fn = getattr(provider, "parse_webhook_event", None)
    if parse_fn is None:
        raise RuntimeError("TelephonyProvider has no parse_webhook_event()")

    headers = dict(request.headers)
    query_params = dict(request.query_params)

    sig = inspect.signature(parse_fn)
    kwargs: dict[str, Any] = {}

    # Common names across implementations
    for name in sig.parameters.keys():
        if name in ("payload", "form", "data"):
            kwargs[name] = payload
        elif name in ("headers",):
            kwargs[name] = headers
        elif name in ("query_params", "query", "params"):
            kwargs[name] = query_params
        elif name in ("request",):
            kwargs[name] = request

    result = parse_fn(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result



async def _twilio_send_audio(ws: WebSocket, stream_sid: str, b64_payload: str) -> None:
    await ws.send_json(
        {"event": "media", "streamSid": stream_sid, "media": {"payload": b64_payload}}
    )

# ---------------------------------------------------------
# Media Streams WebSocket (Patch 2)
# Path MUST match TelephonyConfig.media_streams_ws_path default:
#   /webhooks/telephony/streams
# This router prefix is /webhooks/telephony, so we declare "/streams".
# ---------------------------------------------------------

@router.websocket("/streams")
async def media_streams_ws(ws: WebSocket) -> None:
    """
    Twilio Media Streams bidirectional WebSocket.

    Patch 2 scope:
      - accept connection
      - parse 'connected' / 'start' / 'media' / 'stop' events
      - persist minimal deterministic SoT to Redis
      - no audio processing yet (Patch 3)
    """
    cfg = get_telephony_config()
    if getattr(cfg, "telephony_mode", "legacy") != "media_streams":
        # Policy Violation: endpoint exists but mode disabled.
        await ws.close(code=1008)
        return

    await ws.accept()

    # correlation from query string (set by /voice TwiML bootstrap)
    call_id = (ws.query_params.get("call_id") or "").strip()
    campaign_id = (ws.query_params.get("campaign_id") or "").strip()
    contact_id = (ws.query_params.get("contact_id") or "").strip()

    call_sid: str = ""
    stream_sid: str = ""
    last_seq: int = 0
    openai: OpenAIRealtimeSession | None = None
    openai_rx_task: asyncio.Task[None] | None = None
    assistant_speaking: bool = False
    response_pending: bool = False # nonlocal response_pending
    user_speech_started: bool = False # nonlocal user_speech_started  
    inbound_audio_bytes_since_speech: int = 0 # nonlocal inbound_audio_bytes_since_speech
   

    try:
        while True:
            # Starlette può dare text o bytes; Twilio in genere manda text JSON.
            raw = await ws.receive()
            if isinstance(raw, str):
                raw_text = raw
            elif isinstance(raw, dict):
                if raw.get("type") == "websocket.disconnect":
                    break
                if raw.get("text"):
                    raw_text = raw["text"]
                elif raw.get("bytes"):
                    raw_text = raw["bytes"].decode("utf-8", errors="replace")
            else:
                logger.error(
                    "media_streams_ws: unexpected ws.receive() type",
                    extra={"raw_type": type(raw).__name__},
                )
                continue
            
            raw_bytes: bytes | None = raw.get("bytes")

            if raw_text is None and raw_bytes is None:
                logger.warning("media_streams_ws: received empty frame", extra={"raw": str(raw)})
                continue

            if raw_text is None:
                try:
                    raw_text = raw_bytes.decode("utf-8")
                except Exception:
                    logger.error(
                        "media_streams_ws: failed to decode bytes frame",
                        extra={"bytes_len": len(raw_bytes) if raw_bytes else 0},
                    )
                    continue

            try:
                payload = json.loads(raw_text)
                if not isinstance(payload, dict):
                    logger.error(
                        "media_streams_ws: received non-object JSON payload",
                        extra={"payload_type": type(payload).__name__, "payload_preview": str(payload)[:200]},
                    )
                    continue
            except Exception:
                logger.error(
                    "media_streams_ws: invalid JSON message",
                    extra={"raw_prefix": raw_text[:200], "raw_len": len(raw_text)},
                )
                continue

           
            event = (payload.get("event") or "").strip().lower()
            logger.info(
                    "media_streams_ws: event=%s",
                    event,
                    extra={
                        "keys": sorted(list(payload.keys()))[:30],
                        "has_start": "start" in payload,
                        "has_media": "media" in payload,
                    },)
            if event == "connected":
                # Twilio: connected event has protocol info; no callSid yet
                logger.info("media_streams_ws: connected")
                continue

            if event == "start":
                start_obj = payload.get("start") or {}
                call_sid = (start_obj.get("callSid") or "").strip() or call_sid
                stream_sid = (start_obj.get("streamSid") or "").strip() or stream_sid

                custom = start_obj.get("customParameters") or {}
                if not isinstance(custom, dict):
                    logger.error(
                        "media_streams_ws: start customParameters is not a dict",
                        extra={"custom_params_type": type(custom).__name__},
                    )
                    custom = {}
                # fallback: se li avevi già letti da querystring, qui li sovrascriviamo solo se presenti
                call_id = (custom.get("call_id") or "").strip()
                campaign_id = (custom.get("campaign_id") or "").strip()
                contact_id = (custom.get("contact_id") or "").strip()
                language = (custom.get("language") or ws.query_params.get("language") or "it").strip() or "it"
                logger.info(
                    "media_streams_ws: start call_sid=%s stream_sid=%s call_id=%s campaign_id=%s contact_id=%s lang=%s",
                    call_sid,
                    stream_sid,
                    call_id,
                    campaign_id,
                    contact_id,
                    language,
                )
                artifacts_dir = _ensure_call_artifacts_dir(call_id)
                _append_jsonl(
                artifacts_dir / "realtime.jsonl",
                    {
                        "type": "start",
                        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
                        "call_sid": call_sid,
                        "stream_sid": stream_sid,
                        "call_id": call_id,
                        "campaign_id": campaign_id,
                        "contact_id": contact_id,
                        "language": language,
                    },
                )

                # NON chiudere la WS: a volte Twilio invia start senza customParameters,
                # e se per qualsiasi motivo callSid/streamSid non li stiamo leggendo bene,
                # chiudere qui ammazza la call (Twilio 31921).
                if not call_sid or not stream_sid:
                    logger.error(
                        "media_streams_ws: missing callSid/streamSid in start (continuo comunque)",
                        extra={"start_obj": start_obj},
                    )
                    # continua senza return/close
                    continue

                await _redis_call_meta_upsert(
                    call_sid=call_sid,
                    stream_sid=stream_sid,
                    call_id=call_id,
                    campaign_id=campaign_id,
                    contact_id=contact_id,
                )

                logger.info(
                    "media_streams_ws: start callSid=%s streamSid=%s call_id=%s campaign_id=%s contact_id=%s lang=%s",
                    call_sid,
                    stream_sid,
                    call_id,
                    campaign_id,
                    contact_id,
                    language,
                )

                # Connect OpenAI once per stream
                if openai is None:
                    # instructions = (
                    #     "You are a professional phone survey agent. "
                    #     "You speak in Italian, short sentences, no filler. "
                    #     "First: introduce yourself and ask to user for consent to proceed with a short survey. "
                    #     "If the user refuses, end politely and stop talking."
                    # )
                    # Build campaign-specific instructions (DB + template + SIGNAL rules)
                    instructions = await _build_campaign_instructions(
                        campaign_id=campaign_id,
                        contact_id=contact_id,
                        language=language,
                    )
                    
                    openai = OpenAIRealtimeSession.from_env(instructions=instructions)
                    await openai.connect()
                    inbound_frames = 0
                    LOG_EVERY_N_FRAMES = 50 
                    # --- Force server-side VAD so we get speech_started/speech_stopped and the model can take turns
                    # await openai.send_event({
                    #     "type": "session.update",
                    #         "session": {
                    #         "type": "realtime",
                    #         # Twilio Media Streams is G.711 µ-law (8kHz)
                    #         "audio": {
                    #             "input": {
                    #                 "format": {
                    #                     "type": "audio/pcmu",
                    #                 },
                    #                 "turn_detection": {
                    #                     "type": "server_vad",
                    #                     # these values are conservative; tweak later if needed
                    #                     "silence_duration_ms": 650,
                    #                     "prefix_padding_ms": 250,
                    #                 },
                    #                 },
                    #                 "output": {
                    #                     "format": {
                    #                         "type": "audio/pcmu",
                    #                     },
                    #                 },
                    #             },
                    #         },
                    #     })
                    # logger.info("media_streams_ws: openai session updated (server_vad enabled)")


                    async def _openai_rx_loop() -> None:
                        nonlocal assistant_speaking
                        nonlocal response_pending
                        nonlocal user_speech_started
                        nonlocal inbound_audio_bytes_since_speech
                        assert openai is not None
                        response_text_buf: dict[str, str] = {}
                        response_transcript_buf: dict[str, str] = {}
                        assistant_speaking = False
                        response_pending = False

                        # Turn-taking gating
                        user_speech_started = False
                        inbound_audio_bytes_since_speech = 0


                        while True:
                            evt = await openai.recv_event()
                            et = str(evt.get("type") or "")
                            logger.info("openai_realtime evt=%s", evt)
                                                        # Persist USER transcript (from OpenAI input audio transcription) for post-call summary/debug
                            if et in (
                                "conversation.item.input_audio_transcription.completed",
                                "conversation.item.input_audio_transcription.final",
                            ):
                                user_text = (evt.get("transcript") or "").strip()
                                if user_text:
                                    await _redis_transcript_append(call_sid, "user", user_text)
                                    _append_transcript_line(call_id, "USER", user_text)
                                    _append_jsonl(
                                        artifacts_dir / "realtime.jsonl",
                                        {
                                            "type": "user",
                                            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
                                            "text": user_text,
                                        },
                                    )
                               
                                continue

                            if et == "error":
                                err = evt.get("error", {})
                                logger.error("openai_realtime error evt=%s", evt)
                                code = err.get("code")

                                msg = err.get("message")
                                logger.error("openai_realtime error code=%s msg=%s", code, msg)
                                assistant_speaking = False
                                response_pending = False
                                continue

                              
                                # Se vuoi, puoi rendere non-fatale anche questo (dipende dalla tua fase di startup)
                                # if code == "unknown_parameter":
                                #     continue

                                #return
                            # ---- TEXT del modello (preferito per SIGNAL) ----
                            elif et in ("response.text.delta", "response.output_text.delta"):
                                rid = (evt.get("response_id") or "").strip() or "unknown"
                                delta = evt.get("delta") or ""
                                if delta:
                                    response_text_buf[rid] = response_text_buf.get(rid, "") + str(delta)

                                # opportunistic parse (SIGNAL might appear early)
                                buf = response_text_buf.get(rid, "")
                                m = _SIGNAL_RE.search(buf)
                                if m:
                                    signal_raw = m.group(1)
                                    logger.info("SIGNAL detected (text): %s", signal_raw)
                                    if call_sid:
                                        await _redis_call_meta_set_signal(call_sid, signal_raw)
                                continue
 
                            elif et in ("response.text.done", "response.output_text.done"):
                                rid = (evt.get("response_id") or "").strip() or "unknown"
                                buf = response_text_buf.get(rid, "")
                                m = _SIGNAL_RE.search(buf)
                                if m:
                                    signal_raw = m.group(1)
                                    logger.info("SIGNAL detected (text done): %s", signal_raw)
                                    if call_sid:
                                        await _redis_call_meta_set_signal(call_sid, signal_raw)
                                continue

                            # ---- Transcript dell'audio di output (fallback) ----
                            elif et in ("response.output_audio_transcript.delta",):
                                
                                rid = (evt.get("response_id") or "").strip() or "unknown"
                                try:
                                    delta = str(evt.get("delta") or "")
                                except Exception:
                                    delta = ""
                                
                                if delta:
                                    response_transcript_buf[rid] = response_transcript_buf.get(rid, "") + str(delta)
                                continue
                            
                            elif et in ("response.output_audio_transcript.done", "response.output_audio_transcript.completed"):
                                rid = (evt.get("response_id") or "").strip() or "unknown"

                                buf = "".join(response_transcript_buf.get(rid, []))

                                buf = (buf or "").strip()
                                if buf:
                                    await _redis_transcript_append(call_sid, "assistant", buf)
                                    _append_transcript_line(call_id, "ASSISTANT", buf)
                                    _append_jsonl(
                                        artifacts_dir / "realtime.jsonl",
                                        {
                                            "type": "assistant",
                                            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
                                            "text": buf,
                                        },
                                    )

                                continue

                            elif et in ("response.output_audio_transcript.done", "response.output_audio_transcript.completed"):
                                rid = (evt.get("response_id") or "").strip() or "unknown"
                                buf = response_transcript_buf.get(rid, "")
                                m = _SIGNAL_RE.search(buf)
                                if m:
                                    signal_raw = m.group(1)
                                    logger.info("SIGNAL detected (output transcript): %s", signal_raw)
                                    if call_sid:
                                        await _redis_call_meta_set_signal(call_sid, signal_raw)
                                continue

                            elif et == "input_audio_buffer.speech_started":
                                # barge-in: stop playing assistant audio
                                response_pending = False
                                user_speech_started = True
                                inbound_audio_bytes_since_speech = 0
                                if stream_sid:
                                    await _twilio_send_clear(ws, stream_sid)
                                try:
                                    await openai.cancel_response()
                                except Exception:
                                    logger.exception("openai: cancel_response failed")
                                assistant_speaking = False
                                continue

                            elif et in ("response.output_audio.delta", "response.audio.delta"):
                                delta = evt.get("delta")
                                if isinstance(delta, str) and delta:
                                    assistant_speaking = True
                                    await _twilio_send_media_pcmu_paced(ws, stream_sid, delta)
                                continue

                            elif et in ("response.output_audio.done", "response.audio.done"):
                                response_pending = False
                                assistant_speaking = False
                                continue
                            elif et == ("response.completed", "response.done", "response.cancelled", "response.failed"):
                                logger.info("openai: response completed")
                                response_pending = False
                                assistant_speaking = False
                                continue
                            
                            elif et in ("input_audio_buffer.speech_stopped", "input_audio_buffer.speech_ended"):
                                # Turn end: genera risposta SOLO se abbiamo davvero audio inbound dopo speech_started
                                if not user_speech_started:
                                    logger.info("OpenAI speech stopped but no prior speech_started -> IGNORE")
                                    continue

                                # soglia minimale: ~200ms di audio PCMU @ 8kHz => 1600 bytes
                                # (regola empirica per evitare falsi positivi su click/rumore)
                                MIN_BYTES = 1600
                                if inbound_audio_bytes_since_speech < MIN_BYTES:
                                    logger.info(
                                        "OpenAI speech stopped but too little audio -> IGNORE",
                                        extra={"bytes": inbound_audio_bytes_since_speech},
                                    )
                                    user_speech_started = False
                                    inbound_audio_bytes_since_speech = 0
                                    continue

                                if response_pending or assistant_speaking:
                                    logger.info(
                                        "OpenAI speech stopped but response already pending/speaking -> IGNORE",
                                        extra={"response_pending": response_pending, "assistant_speaking": assistant_speaking},
                                    )
                                    user_speech_started = False
                                    inbound_audio_bytes_since_speech = 0
                                    continue

                                logger.info("OpenAI speech stopped -> commit + request_response")
                                response_pending = True
                                user_speech_started = False

                                try:
                                    await openai.commit_audio()
                                except Exception:
                                    logger.exception("openai: commit_audio failed")
                                    response_pending = False
                                    inbound_audio_bytes_since_speech = 0
                                    continue

                                try:
                                    await openai.request_response()
                                except Exception:
                                    logger.exception("openai: request_response failed")
                                    response_pending = False

                                inbound_audio_bytes_since_speech = 0
                                continue

                            elif et == "input_audio_buffer.committed":
                                logger.info("OpenAI committed (ignored)")
                                continue


                    openai_rx_task = asyncio.create_task(_openai_rx_loop())
                    myevt: dict[str, Any] = {"type": "conversation.item.create"}
                    myevt["item"] = {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Inizia la chiamata ora: saluta e avvia lo script della campagna. Se serve chiedi conferma titolare.",
                            }
                        ],
                    }
                    # if text_hint:
                    #     evt["response"]["text_hint"] = text_hint
                    await openai.send_event(myevt)
                    await openai.request_response()

                    

                continue

            if event == "media":
                inbound_frames += 1

                # Log only once every N frames to avoid flooding
                if inbound_frames % LOG_EVERY_N_FRAMES == 0:
                    logger.info(
                        "media_streams_ws: inbound media (sampled)",
                        extra={
                            "callSid": call_sid,
                            "streamSid": stream_sid,
                            "seq": seq,
                            "track": track,
                            "payload_len": len(payload_b64) if payload_b64 else 0,
                            "frames_seen": inbound_frames,
                        },
                    )
                media = payload.get("media") or {}
                track = (media.get("track") or "").strip().lower()

                # PATCH ECHO (runtime): accetta solo inbound
                if track and track not in ("inbound", "inbound_track", "both", "both_tracks"):
                    continue

                seq_raw = payload.get("sequenceNumber") or payload.get("sequence_number") or last_seq

                try:
                    seq = int(seq_raw)
                except Exception:
                    seq = last_seq

                if seq > last_seq:
                    last_seq = seq

                if call_sid:
                    await _redis_call_meta_touch(call_sid, last_seq=last_seq)
          
                media_obj = payload.get("media") or {}
                track = media_obj.get("track")
                chunk_b64 = media_obj.get("payload") or ""
                if last_seq % 50 == 0:
                    logger.debug(
                        "media_streams_ws: media frame",
                        extra={"seq": last_seq, "track": track, "b64_len": len(chunk_b64)},
                    )
                if openai is not None:
                    payload_b64 = (media.get("payload") or "").strip()
                    if payload_b64:
                        if seq is not None:
                            try:
                                last_seq = int(seq)
                            except Exception:
                                pass

                        if not payload_b64:
                            logger.debug("media_streams_ws: empty payload", extra={"seq": seq, "track": track})
                            continue

                        # LOG di sanity (non spammare)
                        if last_seq in (0, 1, 2, 3, 4, 5) or (isinstance(last_seq, int) and last_seq % 50 == 0):
                            logger.info(
                                "media_streams_ws: inbound media",
                                extra={
                                    "callSid": call_sid,
                                    "streamSid": stream_sid,
                                    "seq": last_seq,
                                    "track": track,
                                    "payload_len": len(payload_b64),
                                },
                            )

                        # INOLTRO a OpenAI (input audio buffer append)
                        try:
                            await openai.append_audio_b64(payload_b64)
                            if user_speech_started and payload_b64:
                                try:
                                    inbound_audio_bytes_since_speech += len(base64.b64decode(payload_b64))
                                except Exception:
                                    # se base64 invalida, non bloccare il loop
                                    pass
                        except Exception:
                            logger.exception(
                                "media_streams_ws: failed to forward audio to OpenAI",
                                extra={"callSid": call_sid, "streamSid": stream_sid, "seq": last_seq},
                            )
                        
                            # non chiudere subito: prova a continuare a leggere
                            continue

                continue

            if event == "dtmf":
                # Optional: store dtmf for debugging (Patch 3+ can route it to LLM)
                if call_sid:
                    await _redis_call_meta_touch(call_sid, last_seq=last_seq)
                continue

            if event == "stop":
                stop = payload.get("stop") or {}
                call_sid = (stop.get("callSid") or "").strip() or call_sid
                stream_sid = (stop.get("streamSid") or "").strip() or stream_sid

                if call_sid:
                    await _redis_call_meta_close(call_sid, reason="twilio_stop")

                logger.info(
                    "media_streams_ws: stop callSid=%s streamSid=%s last_seq=%s",
                    call_sid,
                    stream_sid,
                    last_seq,
                )
                if openai_rx_task is not None:
                    openai_rx_task.cancel()
                    openai_rx_task = None
                if openai is not None:
                    await openai.close()
                    openai = None

                await ws.close(code=1000)
                return
            # Unknown event types: ignore deterministically
            continue

    except WebSocketDisconnect:
        if call_sid:
            try:
                await _redis_call_meta_close(call_sid, reason="ws_disconnect")
            except Exception:
                # Do not raise on disconnect cleanup
                pass
        
       
    except Exception as e:
        logger.exception("media_streams_ws: fatal error: %s", e)
        if call_sid:
            try:
                await _redis_call_meta_close(call_sid, reason="ws_error")
            except Exception:
                pass
        try:
            await ws.close(code=1011, reason="Internal Error")
        except Exception:
            pass 
      
    finally:
        if openai_rx_task:
            openai_rx_task.cancel()
            openai_rx_task = None
        if openai is not None:
            try:
                await openai.close()
            except Exception:
                pass
            openai = None

        try:
            if ws.client_state.name != "DISCONNECTED":
                await ws.close()
        except Exception:
            pass



# ----------------------------
# Redis (SoT for Media Streams)
# ----------------------------

_redis_client = None

def _redis_required_error() -> RuntimeError:
    return RuntimeError(
        "Redis client not available. Install dependency 'redis' (redis-py) and configure redis_url."
    )

async def _get_redis():
    """
    Lazy init Redis async client.

    Deterministic behavior:
      - If 'redis' package is missing -> raise RuntimeError
      - If connection fails -> raise RuntimeError
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        # redis-py provides redis.asyncio since v4.x
        import redis.asyncio as redis  # type: ignore
    except Exception as e:
        raise _redis_required_error() from e

    settings = get_settings()
    url = (settings.redis_url or "").strip()
    if not url:
        raise RuntimeError("redis_url is empty in Settings")

    client = redis.from_url(url, decode_responses=True)
    try:
        await client.ping()
    except Exception as e:
        raise RuntimeError(f"Redis ping failed for redis_url={url!r}") from e

    _redis_client = client
    return _redis_client


async def _redis_call_meta_upsert(
    call_sid: str,
    stream_sid: str,
    call_id: str,
    campaign_id: str,
    contact_id: str,
) -> None:
    """
    Minimal deterministic SoT record for the live call.
    """
    r = await _get_redis()
    key = f"call:{call_sid}:meta"
    now_ms = int(time.time() * 1000)
    await r.hset(
        key,
        mapping={
            "callSid": call_sid,
            "streamSid": stream_sid,
            "call_id": call_id,
            "campaign_id": campaign_id,
            "contact_id": contact_id,
            "connected_at_ms": str(now_ms),
            "last_activity_ms": str(now_ms),
            "last_seq": "0",
            "state": "streaming",
        },
    )
    # TTL: 1 hour (cleanup even if stop event missing)
    await r.expire(key, 3600)


async def _redis_call_meta_touch(call_sid: str, last_seq: Optional[int] = None) -> None:
    r = await _get_redis()
    key = f"call:{call_sid}:meta"
    now_ms = int(time.time() * 1000)
    mapping = {"last_activity_ms": str(now_ms)}
    if last_seq is not None:
        mapping["last_seq"] = str(last_seq)
    await r.hset(key, mapping=mapping)
    await r.expire(key, 3600)


async def _redis_call_meta_close(call_sid: str, reason: str) -> None:
    r = await _get_redis()
    key = f"call:{call_sid}:meta"
    now_ms = int(time.time() * 1000)
    await r.hset(
        key,
        mapping={
            "state": "closed",
            "closed_at_ms": str(now_ms),
            "close_reason": reason,
        },
    )
    await r.expire(key, 3600)

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


async def _twilio_send_media(ws: WebSocket, stream_sid: str, payload_b64: str) -> None:
    await ws.send_text(
        json.dumps(
            {
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": payload_b64},
            }
        )
    )

async def _twilio_send_media_pcmu_paced(ws: WebSocket, stream_sid: str, payload_b64: str) -> None:
    """
    Twilio Media Streams plays best with 20ms PCMU frames.
    PCMU is 8kHz, 1 byte/sample -> 20ms = 160 bytes.

    OpenAI 'response.output_audio.delta' (with output_format=audio/pcmu)
    may contain multiple frames bundled together.
    We split into 160-byte chunks and pace at 20ms.
    """
    raw = base64.b64decode(payload_b64)

    frame_size = 160  # bytes per 20ms @ PCMU/8000
    for i in range(0, len(raw), frame_size):
        chunk = raw[i : i + frame_size]
        if not chunk:
            continue

        await _twilio_send_media(
            ws,
            stream_sid,
            base64.b64encode(chunk).decode("ascii"),
        )

        # pace to real-time
        await asyncio.sleep(0.02)


async def _twilio_send_clear(ws: WebSocket, stream_sid: str) -> None:
    # Twilio Media Streams supports "clear" to flush queued audio on the call leg.
    await ws.send_text(json.dumps({"event": "clear", "streamSid": stream_sid}))

# ----------------------------
# Voice state (single source of truth: CallAttempt.metadata)
# ----------------------------

VOICE_KEY = "voice_convo_v1"
import os
from urllib.parse import urlencode

WS_PUBLIC_URL = (getattr(settings, "media_streams_ws_public_url", "") or "").strip().rstrip("/")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
def _ws_public_url(
    request: Request,
    cfg: Any,
    path: str,
    qs: dict[str, str],
) -> str:
    """
    Build a public WebSocket URL reachable by Twilio.

    Priority:
      1) TELEPHONY_MEDIA_STREAMS_WS_PUBLIC_URL (full wss://host[:port])
      2) WS_PUBLIC_URL / forwarded headers / request.base_url (existing logic)
    """
    # 1) explicit override from TelephonyConfig
    base_override = (getattr(settings, "media_streams_ws_public_url", "") or "").strip().rstrip("/")
    if base_override:
        q = urlencode({k: v for k, v in qs.items() if v is not None and str(v) != ""})
        if q:
            return f"{base_override}{path}?{q}"
        return f"{base_override}{path}"

    # 2) derive from existing public base rules
    base_http = _abs_base(request).rstrip("/")

    # convert http(s) -> ws(s)
    if base_http.startswith("https://"):
        base_ws = "wss://" + base_http[len("https://") :]
    elif base_http.startswith("http://"):
        base_ws = "ws://" + base_http[len("http://") :]
    else:
        # fallback: assume already a host-like string
        base_ws = base_http

    q = urlencode({k: v for k, v in qs.items() if v is not None and str(v) != ""})
    if q:
        return f"{base_ws}{path}?{q}"
    return f"{base_ws}{path}"

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
) -> Response:
    """
    FAST-ACK endpoint for Twilio call-progress / status callbacks.

    MUST return fast (<1s) to avoid Twilio 15003 / 502.
    Heavy work is executed in a background task with its own DB session.
    """
    raw_url = str(request.url)

    try:
        form = await request.form()
        payload: dict[str, Any] = dict(form)
    except Exception:
        payload = {}

    async def _process_async() -> None:
        try:
            # New DB session owned by the task (NOT request-scoped)
            dbm = get_database_manager()
            async with dbm.session() as session:
                task_handler = WebhookHandler(session=session)

                event = await parse_telephony_event(
                    provider=provider,
                    request=request,
                    payload=payload,
                )

                await task_handler.handle_event(event)
                await session.commit()

        except Exception as e:
            logger.exception("events: async processing failed: %s url=%s", e, raw_url)

    asyncio.create_task(_process_async())

    # Return immediately to Twilio
    return Response(status_code=200)




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
            attempt.ended_at = datetime.now(timezone.utc)

    elif phase == "refused":
        res = await svc.persist_refused_survey(session=session, dialogue_session=ds)
        if not res.success:
            raise RuntimeError(f"persist_refused_survey failed: {res.error_message}")

        attempt.outcome = CallOutcome.REFUSED
        if getattr(attempt, "ended_at", None) is None:
            attempt.ended_at = datetime.now(timezone.utc)

    elif phase == "failed":
        attempt.outcome = CallOutcome.FAILED
        if getattr(attempt, "ended_at", None) is None:
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
    
@router.get("/voice")
@router.post("/voice")
async def voice(request: Request, session: Annotated[AsyncSession, Depends(get_db_session)]) -> Any:
    qs = request.query_params
    mode = (qs.get("mode") or "entry").lower().strip()

    # ---------------------------------------------------------
    # PATCH (Media Streams bootstrap, Phase 1):
    # If telephony_mode == "media_streams", return ONLY TwiML
    # <Connect><Stream> to open bidirectional Media Stream WS.
    # No Gather, no Redirect orchestration.
    # ---------------------------------------------------------
    cfg = get_telephony_config()
    if getattr(cfg, "telephony_mode", "legacy") == "media_streams":
        # We keep correlation params in the WS query string.
        # Twilio will open the WS immediately after receiving this TwiML.
        call_id_q = (qs.get("call_id") or "").strip()
        campaign_id_q = (qs.get("campaign_id") or "").strip()
        contact_id_q = (qs.get("contact_id") or "").strip()
        language_q = (qs.get("language") or "it").strip()

        ws_path = getattr(cfg, "media_streams_ws_path", "/webhooks/telephony/streams")
        ws_url = _ws_public_url(
            request=request,
            cfg=cfg,
            path=ws_path,
            qs={
                "call_id": call_id_q,
                "campaign_id": campaign_id_q,
                "contact_id": contact_id_q,
                "language": language_q,

            },
        )
        ws_url_xml = ws_url.replace("&", "&amp;")

        logger.info("WS URL", extra={"ws_url": ws_url, "ws_url_xml": ws_url_xml})
        # ws_url = (
        #     f"{WS_PUBLIC_URL}/webhooks/telephony/streams"
        #     f"?call_id={call_id_q}&campaign_id={campaign_id_q}&contact_id={contact_id_q}&"
        # )

        tw = f"""<?xml version="1.0" encoding="UTF-8"?><Response><Connect><Stream url="{ws_url_xml}" track="inbound_track"><Parameter name="call_id" value="{_xml_escape(call_id_q)}"/><Parameter name="campaign_id" value="{_xml_escape(campaign_id_q)}"/><Parameter name="contact_id" value="{_xml_escape(contact_id_q)}"/><Parameter name="language" value="{_xml_escape(language_q or "")}"/></Stream></Connect></Response>"""
        return Response(content=tw, media_type="text/xml")

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
