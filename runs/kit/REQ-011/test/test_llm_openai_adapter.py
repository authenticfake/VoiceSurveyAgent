"""
Integration tests for OpenAI adapter.

REQ-011: LLM gateway integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.dialogue.llm.openai_adapter import OpenAIAdapter
from app.dialogue.llm.models import (
    ChatMessage,
    ChatRequest,
    ControlSignal,
    LLMAuthenticationError,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    MessageRole,
    SurveyContext,
)

@pytest.fixture
def openai_adapter() -> OpenAIAdapter:
    """Create OpenAI adapter for testing."""
    return OpenAIAdapter(
        api_key="test-api-key",
        default_model="gpt-4.1-mini",
        timeout_seconds=10.0,
        max_retries=2,
    )

@pytest.fixture
def sample_request() -> ChatRequest:
    """Create sample chat request."""
    return ChatRequest(
        messages=[
            ChatMessage(role=MessageRole.USER, content="Hello"),
        ],
        correlation_id="test-correlation-123",
    )

@pytest.fixture
def sample_openai_response() -> dict:
    """Create sample OpenAI API response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4.1-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you?\nSIGNAL: CONSENT_ACCEPTED",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }

class TestOpenAIAdapterProperties:
    """Tests for OpenAI adapter properties."""

    def test_provider(self, openai_adapter: OpenAIAdapter) -> None:
        """Test provider property."""
        assert openai_adapter.provider == LLMProvider.OPENAI

    def test_default_model(self, openai_adapter: OpenAIAdapter) -> None:
        """Test default model property."""
        assert openai_adapter.default_model == "gpt-4.1-mini"

class TestOpenAIAdapterChatCompletion:
    """Tests for chat completion."""

    @pytest.mark.asyncio
    async def test_successful_completion(
        self,
        openai_adapter: OpenAIAdapter,
        sample_request: ChatRequest,
        sample_openai_response: dict,
    ) -> None:
        """Test successful chat completion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_openai_response

        with patch.object(
            openai_adapter, "_execute_with_retry", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_response

            response = await openai_adapter.chat_completion(sample_request)

            assert response.content == "Hello! How can I help you?"
            assert response.model == "gpt-4.1-mini"
            assert response.provider == LLMProvider.OPENAI
            assert response.correlation_id == "test-correlation-123"
            assert ControlSignal.CONSENT_ACCEPTED in response.control_signals
            assert response.usage["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_completion_with_survey_context(
        self,
        openai_adapter: OpenAIAdapter,
        sample_openai_response: dict,
    ) -> None:
        """Test completion with survey context adds system prompt."""
        context = SurveyContext(
            campaign_name="Test Survey",
            intro_script="Hello, this is a test survey.",
            question_1_text="Q1",
            question_1_type="scale",
            question_2_text="Q2",
            question_2_type="free_text",
            question_3_text="Q3",
            question_3_type="numeric",
        )

        request = ChatRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Yes")],
            survey_context=context,
            correlation_id="test-123",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_openai_response

        with patch.object(
            openai_adapter, "_execute_with_retry", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_response

            await openai_adapter.chat_completion(request)

            # Verify system prompt was added
            call_args = mock_execute.call_args
            payload = call_args[0][1]  # Second positional arg is payload
            messages = payload["messages"]
            assert messages[0]["role"] == "system"
            assert "Test Survey" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_timeout_error(
        self,
        openai_adapter: OpenAIAdapter,
        sample_request: ChatRequest,
    ) -> None:
        """Test timeout handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMTimeoutError) as exc_info:
                await openai_adapter.chat_completion(sample_request)

            assert exc_info.value.correlation_id == "test-correlation-123"
            assert exc_info.value.provider == LLMProvider.OPENAI

class TestOpenAIAdapterRetry:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_authentication_error_no_retry(
        self,
        openai_adapter: OpenAIAdapter,
    ) -> None:
        """Test that auth errors don't retry."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMAuthenticationError):
                await openai_adapter._execute_with_retry(
                    mock_client, {}, {}, "test-123"
                )

            # Should only be called once (no retry)
            assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_retry(
        self,
        openai_adapter: OpenAIAdapter,
    ) -> None:
        """Test rate limit triggers retry."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "1"}

        success_response = MagicMock()
        success_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = [rate_limit_response, success_response]
            mock_client_class.return_value = mock_client

            # Mock sleep to avoid actual delay
            with patch.object(openai_adapter, "_sleep", new_callable=AsyncMock):
                result = await openai_adapter._execute_with_retry(
                    mock_client, {}, {}, "test-123"
                )

            assert result.status_code == 200
            assert mock_client.post.call_count == 2

class TestOpenAIAdapterHealthCheck:
    """Tests for health check."""

    @pytest.mark.asyncio
    async def test_health_check_success(
        self,
        openai_adapter: OpenAIAdapter,
    ) -> None:
        """Test successful health check."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await openai_adapter.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self,
        openai_adapter: OpenAIAdapter,
    ) -> None:
        """Test failed health check."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client

            result = await openai_adapter.health_check()
            assert result is False