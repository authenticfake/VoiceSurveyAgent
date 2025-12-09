"""
OpenAI adapter for LLM gateway.

REQ-011: LLM gateway integration
"""

import time
from typing import Any

import httpx

from app.dialogue.llm.gateway import BaseLLMAdapter
from app.dialogue.llm.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ControlSignal,
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

OPENAI_API_BASE = "https://api.openai.com/v1"
OPENAI_CHAT_ENDPOINT = f"{OPENAI_API_BASE}/chat/completions"

class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI adapter implementing the LLM gateway interface."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4.1-mini",
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        base_url: str | None = None,
    ) -> None:
        """Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key.
            default_model: Default model to use.
            timeout_seconds: Request timeout in seconds.
            max_retries: Maximum number of retries.
            base_url: Optional custom base URL for API.
        """
        super().__init__(api_key, default_model, timeout_seconds, max_retries)
        self._base_url = base_url or OPENAI_API_BASE
        self._chat_endpoint = f"{self._base_url}/chat/completions"

    @property
    def provider(self) -> LLMProvider:
        """Get the LLM provider type."""
        return LLMProvider.OPENAI

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute a chat completion request to OpenAI.

        Args:
            request: The chat request.

        Returns:
            ChatResponse with the completion result.

        Raises:
            LLMTimeoutError: If the request times out.
            LLMRateLimitError: If rate limited.
            LLMAuthenticationError: If authentication fails.
            LLMProviderError: For other errors.
        """
        start_time = time.monotonic()
        model = request.model or self._default_model

        # Build messages with system prompt if survey context provided
        messages = self._build_messages(request)

        payload = {
            "model": model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        logger.info(
            "OpenAI chat completion request",
            extra={
                "correlation_id": request.correlation_id,
                "model": model,
                "message_count": len(messages),
            },
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await self._execute_with_retry(
                    client, payload, headers, request.correlation_id
                )

            latency_ms = (time.monotonic() - start_time) * 1000

            # Parse response
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
            usage = response_data.get("usage", {})

            # Parse for control signals
            parsed = parse_llm_response(content)

            logger.info(
                "OpenAI chat completion success",
                extra={
                    "correlation_id": request.correlation_id,
                    "model": model,
                    "latency_ms": latency_ms,
                    "signals": [s.value for s in parsed.signals],
                },
            )

            return ChatResponse(
                content=parsed.content,
                model=model,
                provider=self.provider,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                correlation_id=request.correlation_id,
                latency_ms=latency_ms,
                control_signals=parsed.signals,
                captured_answer=parsed.captured_answer,
            )

        except httpx.TimeoutException as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "OpenAI request timeout",
                extra={
                    "correlation_id": request.correlation_id,
                    "latency_ms": latency_ms,
                },
            )
            raise LLMTimeoutError(
                f"Request timed out after {self._timeout_seconds}s",
                correlation_id=request.correlation_id,
                provider=self.provider,
                original_error=e,
            )

    async def _execute_with_retry(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
        headers: dict[str, str],
        correlation_id: str,
    ) -> httpx.Response:
        """Execute request with retry logic.

        Args:
            client: HTTP client.
            payload: Request payload.
            headers: Request headers.
            correlation_id: Correlation ID for logging.

        Returns:
            HTTP response.

        Raises:
            LLMRateLimitError: If rate limited after retries.
            LLMAuthenticationError: If authentication fails.
            LLMProviderError: For other errors.
        """
        last_error: Exception | None = None
        backoff = 1.0

        for attempt in range(self._max_retries):
            try:
                response = await client.post(
                    self._chat_endpoint,
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    return response

                if response.status_code == 401:
                    raise LLMAuthenticationError(
                        "Invalid API key",
                        correlation_id=correlation_id,
                        provider=self.provider,
                    )

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff))
                    if attempt < self._max_retries - 1:
                        logger.warning(
                            "OpenAI rate limited, retrying",
                            extra={
                                "correlation_id": correlation_id,
                                "attempt": attempt + 1,
                                "retry_after": retry_after,
                            },
                        )
                        await self._sleep(retry_after)
                        backoff *= 2
                        continue
                    raise LLMRateLimitError(
                        "Rate limited by OpenAI",
                        retry_after=retry_after,
                        correlation_id=correlation_id,
                        provider=self.provider,
                    )

                # Other error
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", response.text)
                raise LLMProviderError(
                    f"OpenAI API error: {error_msg}",
                    correlation_id=correlation_id,
                    provider=self.provider,
                )

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    logger.warning(
                        "OpenAI request failed, retrying",
                        extra={
                            "correlation_id": correlation_id,
                            "attempt": attempt + 1,
                            "error": str(e),
                        },
                    )
                    await self._sleep(backoff)
                    backoff *= 2
                    continue

        raise LLMProviderError(
            f"OpenAI request failed after {self._max_retries} attempts",
            correlation_id=correlation_id,
            provider=self.provider,
            original_error=last_error,
        )

    def _build_messages(self, request: ChatRequest) -> list[ChatMessage]:
        """Build message list with system prompt if context provided.

        Args:
            request: Chat request.

        Returns:
            List of messages including system prompt.
        """
        messages = list(request.messages)

        # Add system prompt if survey context provided
        if request.survey_context:
            system_prompt = build_system_prompt(request.survey_context)
            # Insert system message at the beginning if not already present
            if not messages or messages[0].role != MessageRole.SYSTEM:
                messages.insert(0, ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))

        return messages

    async def _sleep(self, seconds: float) -> None:
        """Sleep for backoff (mockable for testing).

        Args:
            seconds: Seconds to sleep.
        """
        import asyncio
        await asyncio.sleep(seconds)

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False