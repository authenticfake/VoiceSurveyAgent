"""
Anthropic adapter for LLM gateway.

REQ-011: LLM gateway integration
"""

from __future__ import annotations

import time
from typing import Any, Callable, Protocol

import httpx

from app.dialogue.llm.gateway import BaseLLMAdapter
from app.dialogue.llm.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LLMAuthenticationError,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    MessageRole,
)
from app.dialogue.llm.prompts import build_system_prompt
from app.dialogue.llm.response_parser import parse_llm_response
from app.shared.logging import get_logger

logger = get_logger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_API_VERSION = "2023-06-01"


class SyncHttpTransport(Protocol):
    """Minimal sync transport protocol (in-memory fakeable)."""

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> Any: ...


class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic adapter implementing the LLM gateway interface."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-3-5-sonnet-20241022",
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        base_url: str | None = None,
        transport: SyncHttpTransport | None = None,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        """Initialize Anthropic adapter."""
        super().__init__(api_key, default_model, timeout_seconds, max_retries)
        self._base_url = base_url or ANTHROPIC_API_BASE
        self._messages_endpoint = f"{self._base_url}/messages"
        self._transport = transport
        self._sleep_func = sleep_func

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.ANTHROPIC

    # --- SYNC PATH (used by REQ-011 unit tests, no event loop) ---

    def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
        start_time = time.monotonic()
        model = request.model or self._default_model

        messages, system_prompt = self._build_messages(request)

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "max_tokens": request.max_tokens,
        }
        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "Content-Type": "application/json",
        }

        logger.info(
            "Anthropic chat completion request",
            extra={
                "correlation_id": request.correlation_id,
                "model": model,
                "message_count": len(messages),
            },
        )

        try:
            response = self._execute_with_retry_sync(
                payload=payload,
                headers=headers,
                correlation_id=request.correlation_id,
            )

            latency_ms = (time.monotonic() - start_time) * 1000

            response_data = response.json()
            content = response_data["content"][0]["text"]
            usage = response_data.get("usage", {})

            parsed = parse_llm_response(content)

            logger.info(
                "Anthropic chat completion success",
                extra={
                    "correlation_id": request.correlation_id,
                    "model": model,
                    "latency_ms": latency_ms,
                    "signals": [s.value for s in parsed.signals],
                },
            )

            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            return ChatResponse(
                content=parsed.content,
                model=model,
                provider=self.provider,
                usage={
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                correlation_id=request.correlation_id,
                latency_ms=latency_ms,
                control_signals=parsed.signals,
                captured_answer=parsed.captured_answer,
            )

        except (httpx.TimeoutException, TimeoutError) as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "Anthropic request timeout",
                extra={"correlation_id": request.correlation_id, "latency_ms": latency_ms},
            )
            raise LLMTimeoutError(
                f"Request timed out after {self._timeout_seconds}s",
                correlation_id=request.correlation_id,
                provider=self.provider,
                original_error=e,
            )
        except Exception as e:
            logger.error(
                "Anthropic chat completion failed",
                extra={"correlation_id": request.correlation_id, "error": str(e)},
            )
            raise

    def _execute_with_retry_sync(
        self,
        *,
        payload: dict[str, Any],
        headers: dict[str, str],
        correlation_id: str,
    ) -> Any:
        last_error: Exception | None = None
        backoff = 1.0

        for attempt in range(self._max_retries):
            try:
                response = self._post_sync(payload=payload, headers=headers)

                if response.status_code == 200:
                    return response

                if response.status_code == 401:
                    logger.error(
                        "Anthropic authentication failed",
                        extra={"correlation_id": correlation_id},
                    )
                    raise LLMAuthenticationError(
                        "Invalid API key",
                        correlation_id=correlation_id,
                        provider=self.provider,
                    )

                if response.status_code == 429:
                    retry_after = float(getattr(response, "headers", {}).get("Retry-After", backoff))
                    if attempt < self._max_retries - 1:
                        logger.warning(
                            "Anthropic rate limited, retrying",
                            extra={
                                "correlation_id": correlation_id,
                                "attempt": attempt + 1,
                                "retry_after": retry_after,
                            },
                        )
                        self._sleep_sync(retry_after)
                        backoff *= 2
                        continue

                    logger.error(
                        "Anthropic rate limited (final)",
                        extra={"correlation_id": correlation_id, "retry_after": retry_after},
                    )
                    raise LLMRateLimitError(
                        "Rate limited by Anthropic",
                        retry_after=retry_after,
                        correlation_id=correlation_id,
                        provider=self.provider,
                    )

                error_data = response.json() if getattr(response, "content", None) else {}
                error_msg = error_data.get("error", {}).get("message", getattr(response, "text", ""))
                logger.error(
                    "Anthropic provider error",
                    extra={"correlation_id": correlation_id, "error": str(error_msg)},
                )
                raise LLMProviderError(
                    f"Anthropic API error: {error_msg}",
                    correlation_id=correlation_id,
                    provider=self.provider,
                )

            except LLMAuthenticationError:
                raise
            except LLMRateLimitError:
                raise
            except (httpx.TimeoutException, TimeoutError) as e:
                last_error = e
                raise
            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    logger.warning(
                        "Anthropic request failed, retrying",
                        extra={
                            "correlation_id": correlation_id,
                            "attempt": attempt + 1,
                            "error": str(e),
                        },
                    )
                    self._sleep_sync(backoff)
                    backoff *= 2
                    continue

        raise LLMProviderError(
            f"Anthropic request failed after {self._max_retries} attempts",
            correlation_id=correlation_id,
            provider=self.provider,
            original_error=last_error,
        )

    def _post_sync(self, *, payload: dict[str, Any], headers: dict[str, str]) -> Any:
        if self._transport is not None:
            return self._transport.post(
                self._messages_endpoint,
                json=payload,
                headers=headers,
                timeout=self._timeout_seconds,
            )

        with httpx.Client(timeout=self._timeout_seconds) as client:
            return client.post(self._messages_endpoint, json=payload, headers=headers)

    def _sleep_sync(self, seconds: float) -> None:
        if self._sleep_func is not None:
            self._sleep_func(seconds)
            return
        time.sleep(seconds)

    def _build_messages(self, request: ChatRequest) -> tuple[list[ChatMessage], str | None]:
        """Build message list and extract system prompt (Anthropic uses separate system param)."""
        messages: list[ChatMessage] = []
        system_prompt: str | None = None

        if request.survey_context:
            system_prompt = build_system_prompt(request.survey_context)

        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                if system_prompt:
                    system_prompt = f"{system_prompt}\n\n{msg.content}"
                else:
                    system_prompt = msg.content
            else:
                messages.append(msg)

        return messages, system_prompt

    # --- ASYNC PATH (kept for compatibility / E2E) ---

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Keep existing async API for E2E compatibility.

        NOTE: tests for REQ-011 use `chat_completion_sync`.
        """
        return self.chat_completion_sync(request)

    async def health_check(self) -> bool:
        """Check if Anthropic API is accessible (async, compatibility)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self._messages_endpoint,
                    json={
                        "model": self._default_model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": ANTHROPIC_API_VERSION,
                        "Content-Type": "application/json",
                    },
                )
                return response.status_code in (200, 400)
        except Exception as e:
            logger.warning(f"Anthropic health check failed: {e}")
            return False
