"""
LLM Gateway interface definition.

REQ-011: LLM gateway integration
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from app.dialogue.llm.models import ChatRequest, ChatResponse, LLMProvider


@runtime_checkable
class LLMGateway(Protocol):
    """Protocol for LLM gateway implementations.

    Defines the interface for chat completion that all provider
    adapters must implement.
    """

    @property
    def provider(self) -> LLMProvider:
        """Get the LLM provider type."""
        ...

    @property
    def default_model(self) -> str:
        """Get the default model for this provider."""
        ...

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute a chat completion request.

        Args:
            request: The chat request containing messages and parameters.

        Returns:
            ChatResponse with the completion result.

        Raises:
            LLMTimeoutError: If the request times out.
            LLMRateLimitError: If rate limited by the provider.
            LLMAuthenticationError: If authentication fails.
            LLMProviderError: For other provider errors.
        """
        ...

    def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
        """Synchronous version of chat completion.

        This is introduced to allow ultra-fast, deterministic, sync-only
        unit tests (no event loop, no async fixtures).

        Production/E2E can keep using the async method.
        """
        ...

    async def health_check(self) -> bool:
        """Check if the LLM provider is healthy and accessible.

        Returns:
            True if healthy, False otherwise.
        """
        ...


class BaseLLMAdapter(ABC):
    """Base class for LLM adapter implementations.

    Provides common functionality for all LLM adapters.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the adapter.

        Args:
            api_key: API key for the provider.
            default_model: Default model to use.
            timeout_seconds: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
        """
        self._api_key = api_key
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """Get the LLM provider type."""
        raise NotImplementedError

    @property
    def default_model(self) -> str:
        """Get the default model for this provider."""
        return self._default_model

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Async chat completion (compatibility API).

        Default implementation delegates to the sync implementation.
        Adapters may override this method with a truly async implementation
        if needed, but unit tests for REQ-011 will use `chat_completion_sync`.
        """
        return self.chat_completion_sync(request)

    @abstractmethod
    def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
        """Execute a chat completion request synchronously."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM provider is healthy."""
        raise NotImplementedError
