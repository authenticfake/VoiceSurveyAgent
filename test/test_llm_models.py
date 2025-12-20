"""
Unit tests for LLM gateway models.

REQ-011: LLM gateway integration
"""

import pytest
from datetime import datetime

from app.dialogue.llm.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ControlSignal,
    LLMError,
    LLMProvider,
    LLMRateLimitError,
    LLMTimeoutError,
    MessageRole,
    SurveyContext,
)

class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_message_roles_exist(self) -> None:
        """Test that all required roles exist."""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"

class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_providers_exist(self) -> None:
        """Test that all required providers exist."""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"

class TestChatMessage:
    """Tests for ChatMessage model."""

    def test_create_message(self) -> None:
        """Test creating a chat message."""
        msg = ChatMessage(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"

    def test_message_is_frozen(self) -> None:
        """Test that message is immutable."""
        msg = ChatMessage(role=MessageRole.USER, content="Hello")
        with pytest.raises(Exception):  # Pydantic ValidationError
            msg.content = "Changed"  # type: ignore

class TestSurveyContext:
    """Tests for SurveyContext model."""

    def test_create_context(self) -> None:
        """Test creating survey context."""
        ctx = SurveyContext(
            campaign_name="Test Campaign",
            language="en",
            intro_script="Hello, this is a survey...",
            question_1_text="How satisfied are you?",
            question_1_type="scale",
            question_2_text="What could we improve?",
            question_2_type="free_text",
            question_3_text="Would you recommend us?",
            question_3_type="numeric",
        )
        assert ctx.campaign_name == "Test Campaign"
        assert ctx.current_question == 0
        assert ctx.collected_answers == []

    def test_context_with_answers(self) -> None:
        """Test context with collected answers."""
        ctx = SurveyContext(
            campaign_name="Test",
            intro_script="Intro",
            question_1_text="Q1",
            question_1_type="scale",
            question_2_text="Q2",
            question_2_type="free_text",
            question_3_text="Q3",
            question_3_type="numeric",
            current_question=2,
            collected_answers=["8"],
        )
        assert ctx.current_question == 2
        assert len(ctx.collected_answers) == 1

class TestChatRequest:
    """Tests for ChatRequest model."""

    def test_create_request(self) -> None:
        """Test creating a chat request."""
        req = ChatRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Hi")],
            model="gpt-4",
            temperature=0.5,
        )
        assert len(req.messages) == 1
        assert req.model == "gpt-4"
        assert req.temperature == 0.5
        assert req.correlation_id  # Auto-generated

    def test_request_defaults(self) -> None:
        """Test request default values."""
        req = ChatRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Hi")]
        )
        assert req.model is None
        assert req.temperature == 0.7
        assert req.max_tokens == 500

class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_create_response(self) -> None:
        """Test creating a chat response."""
        resp = ChatResponse(
            content="Hello!",
            model="gpt-4",
            provider=LLMProvider.OPENAI,
            correlation_id="test-123",
            latency_ms=150.5,
        )
        assert resp.content == "Hello!"
        assert resp.provider == LLMProvider.OPENAI
        assert resp.latency_ms == 150.5

    def test_response_with_signals(self) -> None:
        """Test response with control signals."""
        resp = ChatResponse(
            content="Thank you for agreeing!",
            model="gpt-4",
            provider=LLMProvider.OPENAI,
            correlation_id="test-123",
            latency_ms=100.0,
            control_signals=[ControlSignal.CONSENT_ACCEPTED],
            captured_answer="yes",
        )
        assert ControlSignal.CONSENT_ACCEPTED in resp.control_signals
        assert resp.captured_answer == "yes"

class TestControlSignal:
    """Tests for ControlSignal enum."""

    def test_all_signals_exist(self) -> None:
        """Test that all required signals exist."""
        signals = [
            ControlSignal.CONSENT_ACCEPTED,
            ControlSignal.CONSENT_REFUSED,
            ControlSignal.MOVE_TO_NEXT_QUESTION,
            ControlSignal.REPEAT_QUESTION,
            ControlSignal.ANSWER_CAPTURED,
            ControlSignal.SURVEY_COMPLETE,
            ControlSignal.UNCLEAR_RESPONSE,
        ]
        assert len(signals) == 7

class TestLLMErrors:
    """Tests for LLM error classes."""

    def test_base_error(self) -> None:
        """Test base LLM error."""
        err = LLMError(
            "Test error",
            correlation_id="test-123",
            provider=LLMProvider.OPENAI,
        )
        assert str(err) == "Test error"
        assert err.correlation_id == "test-123"
        assert err.provider == LLMProvider.OPENAI

    def test_timeout_error(self) -> None:
        """Test timeout error."""
        err = LLMTimeoutError("Timeout", correlation_id="test-123")
        assert isinstance(err, LLMError)

    def test_rate_limit_error(self) -> None:
        """Test rate limit error with retry_after."""
        err = LLMRateLimitError(
            "Rate limited",
            retry_after=30.0,
            correlation_id="test-123",
        )
        assert err.retry_after == 30.0