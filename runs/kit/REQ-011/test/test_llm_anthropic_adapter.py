"""
Integration tests for Anthropic adapter.

REQ-011: LLM gateway integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.dialogue.llm.anthropic_adapter import AnthropicAdapter
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
def anthropic_adapter() -> AnthropicAdapter:
    """Create Anthropic adapter for testing."""
    return AnthropicAdapter(
        api_key="test-api-key",
        default_model="claude-3-5-sonnet-20241022",
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
def sample_anthropic_response() -> dict:
    """Create sample Anthropic API response."""
    return {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Hello! How can I help you?\nSIGNAL: CONSENT_ACCEPTED",
            }
        ],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
        },
    }

class TestAnthropicAdapterProperties:
    """Tests for Anthropic adapter properties."""

    def test_provider(self, anthropic_adapter: AnthropicAdapter) -> None:
        """Test provider property."""
        assert anthropic_adapter.provider == LLMProvider.ANTHROPIC

    def test_default_model(self, anthropic_adapter: AnthropicAdapter) -> None:
        """Test default model property."""
        assert anthropic_adapter.default_model == "claude-3-5-sonnet-20241022"

class TestAnthropicAdapterChatCompletion:
    """Tests for chat completion."""

    @pytest.mark.asyncio
    async def test_successful_completion(
        self,
        anthropic_adapter: AnthropicAdapter,
        sample_request: ChatRequest,
        sample_anthropic_response: dict,
    ) -> None:
        """Test successful chat completion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_anthropic_response

        with patch.object(
            anthropic_adapter, "_execute_with_retry", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_response

            response = await anthropic_adapter.chat_completion(sample_request)

            assert response.content == "Hello! How can I help you?"
            assert response.model == "claude-3-5-sonnet-20241022"
            assert response.provider == LLMProvider.ANTHROPIC
            assert response.correlation_id == "test-correlation-123"
            assert ControlSignal.CONSENT_ACCEPTED in response.control_signals
            assert response.usage["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_completion_with_survey_context(
        self,
        anthropic_adapter: AnthropicAdapter,
        sample_anthropic_response: dict,
    ) -> None:
        """Test completion with survey context uses system parameter."""
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
        mock_response.json.return_value = sample_anthropic_response

        with patch.object(
            anthropic_adapter, "_execute_with_retry", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_response

            await anthropic_adapter.chat_completion(request)

            # Verify system parameter was set
            call_args = mock_execute.call_args
            payload = call_args[0][1]  # Second positional arg is payload
            assert "system" in payload
            assert "Test Survey" in payload["system"]
            # Messages should not include system role
            for msg in payload["messages"]:
                assert msg["role"] != "system"

    @pytest.mark.asyncio
    async def test_system_message_extracted(
        self,
        anthropic_adapter: AnthropicAdapter,
    ) -> None:
        """Test that system messages are extracted to system parameter."""
        request = ChatRequest(
            messages=[
                ChatMessage(role=MessageRole.SYSTEM, content="You are helpful."),
                ChatMessage(role=MessageRole.USER, content="Hello"),
            ],
            correlation_id="test-123",
        )

        messages, system = anthropic_adapter._build_messages(request)

        assert system == "You are helpful."
        assert len(messages) == 1
        assert messages[0].role == MessageRole.USER

    @pytest.mark.asyncio
    async def test_timeout_error(
        self,
        anthropic_adapter: AnthropicAdapter,
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
                await anthropic_adapter.chat_completion(sample_request)

            assert exc_info.value.correlation_id == "test-correlation-123"
            assert exc_info.value.provider == LLMProvider.ANTHROPIC

class TestAnthropicAdapterRetry:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_authentication_error_no_retry(
        self,
        anthropic_adapter: AnthropicAdapter,
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
                await anthropic_adapter._execute_with_retry(
                    mock_client, {}, {}, "test-123"
                )

            assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_retry(
        self,
        anthropic_adapter: AnthropicAdapter,
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

            with patch.object(anthropic_adapter, "_sleep", new_callable=AsyncMock):
                result = await anthropic_adapter._execute_with_retry(
                    mock_client, {}, {}, "test-123"
                )

            assert result.status_code == 200
            assert mock_client.post.call_count == 2

class TestAnthropicAdapterHealthCheck:
    """Tests for health check."""

    @pytest.mark.asyncio
    async def test_health_check_success(
        self,
        anthropic_adapter: AnthropicAdapter,
    ) -> None:
        """Test successful health check."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await anthropic_adapter.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self,
        anthropic_adapter: AnthropicAdapter,
    ) -> None:
        """Test failed health check."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client

            result = await anthropic_adapter.health_check()
            assert result is False