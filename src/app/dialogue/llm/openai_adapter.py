# --- add near imports (top of file) ---
import asyncio
import contextlib
from dataclasses import dataclass
import json
import os
from typing import Any, Optional

import httpx
import websockets
from app.config import get_settings
from app.dialogue.llm.gateway import BaseLLMAdapter
from app.dialogue.llm.models import ChatRequest, ChatResponse, LLMProvider, LLMProviderError
from app.shared.logging import get_logger


logger = get_logger(__name__)




@dataclass(frozen=True)
class RealtimeConfig:
    api_key: str
    model: str = "gpt-realtime"
    # IMPORTANT: voice is NOT updatable via session.update (see docs).
    # Keep it as config for future usage if/when you pass it in an allowed place.
    voice: str = "alloy"
    # These are the allowed "string" formats in the Realtime schema (no rate fields here).
    # If you need Twilio PCMU/8000 end-to-end and OpenAI doesn't support g711_ulaw output,
    # you'll need to transcode in your bridge.
    input_audio_format: str = "audio/pcmu"
    output_audio_format: str = "audio/pcmu"
    text_enabled: bool = True
    transcription_enabled: bool = True
    transcription_model: str = "whisper-1"


class OpenAIRealtimeSession:
    """
    OpenAI Realtime WebSocket session (event-based).
    Used by Twilio Media Streams bridge.
    """

    def __init__(self, *, cfg: RealtimeConfig, instructions: str) -> None:
        self._cfg = cfg
        self._instructions = instructions
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected: bool = False

    @classmethod
    def from_env(cls, *, instructions: str) -> "OpenAIRealtimeSession":
        settings = get_settings()
        api_key = getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY (or settings.openai_api_key)")

        model = (
            getattr(settings, "openai_realtime_model", None)
            or os.getenv("OPENAI_REALTIME_MODEL")
            or "gpt-realtime"
        )
        voice = (
            getattr(settings, "openai_realtime_voice", None)
            or os.getenv("OPENAI_REALTIME_VOICE")
            or "alloy"
        )

        # Keep pcm16 default unless you *verified* g711_ulaw is supported by your Realtime schema.
        cfg = RealtimeConfig(
            api_key=api_key,
            model=model,
            voice=voice,
            input_audio_format=getattr(settings, "openai_realtime_input_format", "audio/pcmu"),
            output_audio_format=getattr(settings, "openai_realtime_output_format", "audio/pcmu"),
            text_enabled=getattr(settings, "openai_realtime_text_enabled", True),
            transcription_enabled=getattr(settings, "openai_realtime_transcription_enabled", True),
            transcription_model=getattr(settings, "openai_realtime_transcription_model", "whisper-1"),
           )
        return cls(cfg=cfg, instructions=instructions)

    async def connect(self) -> None:
        if self._connected and self._ws is not None:
            return

        url = f"wss://api.openai.com/v1/realtime?model={self._cfg.model}"
        headers = {"Authorization": f"Bearer {self._cfg.api_key}"}
        
        self._ws = await websockets.connect(  # type: ignore[arg-type]
            url,
            additional_headers=headers,
        )
        self._connected = True

        # IMPORTANT:
        # - Use output_modalities (NOT session.modalities)
        # - input_audio_format/output_audio_format are strings (NOT nested rate fields)
        # - DO NOT send session.voice (not updatable via session.update)
        modalities = ["audio"]
        if self._cfg.text_enabled:
            modalities.append("text")

        session_update: dict[str, Any] = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "output_modalities": ["audio", "text"] if self._cfg.text_enabled else ["audio"],
                "instructions": self._instructions,
                "audio": {
                    "input": {
                        "format": {
                            "type": self._cfg.input_audio_format,
                        },
                        "transcription": (
                            {"model": self._cfg.transcription_model}
                            if self._cfg.transcription_enabled
                            else None
                        ),
                        "turn_detection": {
                            "type": "server_vad",
                            "create_response": False,
                            "interrupt_response": True,
                            "prefix_padding_ms": 500,
                            "threshold": 0.40,
                            "silence_duration_ms": 900
                        },
                    },
                    "output": {
                        "format": {
                            "type": self._cfg.output_audio_format,
                        },
                        "voice": self._cfg.voice,
                    },
                },
            },
        }
        await self.send_event(session_update)

    async def close(self) -> None:
        ws = self._ws
        self._ws = None
        self._connected = False
        if ws is not None:
            with contextlib.suppress(Exception):
                await ws.close()

    async def send_event(self, evt: dict[str, Any]) -> None:
        if self._ws is None:
            raise RuntimeError("Realtime WS not connected")
        await self._ws.send(json.dumps(evt))

    async def recv_event(self) -> dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("Realtime WS not connected")
        raw = await self._ws.recv()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return json.loads(raw)

    async def append_audio_b64(self, b64_audio: str) -> None:
        # input_audio_buffer.append expects base64-encoded audio bytes
        await self.send_event({"type": "input_audio_buffer.append", "audio": b64_audio})

    async def commit_audio(self) -> None:
        await self.send_event({"type": "input_audio_buffer.commit"})

    async def cancel_response(self) -> None:
        if self._ws is None:
            return
        await self.send_event({"type": "response.cancel"})

    async def request_response(self, *, text_hint: str | None = None) -> None:
        # IMPORTANT: response.output_modalities (NOT response.modalities)
        evt: dict[str, Any] = {"type": "response.create"}
        evt["response"] = {
            "output_modalities": ["audio", "text"] if self._cfg.text_enabled else ["audio"],
        }
        # if text_hint:
        #     evt["response"]["text_hint"] = text_hint
        await self.send_event(evt)


    async def start_greeting(self, *, text_hint: str) -> None:
        await self.request_response(text_hint=text_hint)

class OpenAIAdapter(BaseLLMAdapter):
    """
    OpenAI HTTP adapter (REQ-011).
    Chat / text only. NO realtime.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4.1-mini",
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        super().__init__(api_key, default_model, timeout_seconds, max_retries)
        self._base_url = "https://api.openai.com/v1"
        self._chat_endpoint = f"{self._base_url}/chat/completions"

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI

    def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
        payload = {
            "model": request.model or self._default_model,
            "messages": [
                {"role": m.role.value, "content": m.content}
                for m in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self._timeout_seconds) as client:
            r = client.post(self._chat_endpoint, json=payload, headers=headers)

        if r.status_code != 200:
            raise LLMProviderError(
                f"OpenAI error {r.status_code}",
                provider=self.provider,
                correlation_id=request.correlation_id,
            )

        data = r.json()
        content = data["choices"][0]["message"]["content"]

        return ChatResponse(
            content=content,
            model=payload["model"],
            provider=self.provider,
            correlation_id=request.correlation_id,
            latency_ms=0.0,
        )

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        return await asyncio.to_thread(self.chat_completion_sync, request)

