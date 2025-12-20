"""
Unit tests for LLM gateway interface and base adapter.

REQ-011: LLM gateway integration
"""

import pytest

from app.dialogue.llm.gateway import LLMGateway, BaseLLMAdapter
from app.dialogue.llm.models import (
    ChatRequest,
    ChatResponse,
    LLMProvider,
)


class TestLLMGatewayProtocol:
    """Tests for LLMGateway protocol."""

    def test_mock_implementation_satisfies_protocol(self) -> None:
        """Test that a mock implementation satisfies the protocol."""

        class MockGateway:
            @property
            def provider(self) -> LLMProvider:
                return LLMProvider.OPENAI

            @property
            def default_model(self) -> str:
                return "test-model"

            async def chat_completion(self, request: ChatRequest) -> ChatResponse:
                return ChatResponse(
                    content="test",
                    model="test-model",
                    provider=LLMProvider.OPENAI,
                    correlation_id=request.correlation_id,
                    latency_ms=100.0,
                )

            def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
                return ChatResponse(
                    content="test",
                    model="test-model",
                    provider=LLMProvider.OPENAI,
                    correlation_id=request.correlation_id,
                    latency_ms=50.0,
                )

            async def health_check(self) -> bool:
                return True

        gateway = MockGateway()
        assert isinstance(gateway, LLMGateway)


class TestBaseLLMAdapter:
    """Tests for BaseLLMAdapter base class."""

    def test_cannot_instantiate_directly(self) -> None:
        """Test that base adapter cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseLLMAdapter(  # type: ignore
                api_key="test",
                default_model="test",
            )

    def test_concrete_implementation(self) -> None:
        """Test that concrete implementation works."""

        class ConcreteAdapter(BaseLLMAdapter):
            @property
            def provider(self) -> LLMProvider:
                return LLMProvider.OPENAI

            def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
                return ChatResponse(
                    content="test",
                    model=self._default_model,
                    provider=self.provider,
                    correlation_id=request.correlation_id,
                    latency_ms=50.0,
                )

            async def health_check(self) -> bool:
                return True

        adapter = ConcreteAdapter(
            api_key="test-key",
            default_model="test-model",
            timeout_seconds=15.0,
            max_retries=2,
        )

        assert adapter.provider == LLMProvider.OPENAI
        assert adapter.default_model == "test-model"
        assert adapter._timeout_seconds == 15.0
        assert adapter._max_retries == 2
