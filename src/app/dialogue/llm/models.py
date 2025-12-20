"""
Data models for LLM gateway.

REQ-011: LLM gateway integration
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class MessageRole(str, Enum):
    """Message roles in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: MessageRole
    content: str

    model_config = {"frozen": True}

class SurveyContext(BaseModel):
    """Survey context for system prompt construction."""

    campaign_name: str
    language: str = "en"
    intro_script: str
    question_1_text: str
    question_1_type: str
    question_2_text: str
    question_2_type: str
    question_3_text: str
    question_3_type: str
    current_question: int = 0  # 0 = consent, 1-3 = questions
    collected_answers: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

class ChatRequest(BaseModel):
    """Request for chat completion."""

    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 500
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    survey_context: SurveyContext | None = None

    model_config = {"frozen": False}

class ControlSignal(str, Enum):
    """Control signals from LLM response parsing."""

    CONSENT_ACCEPTED = "consent_accepted"
    CONSENT_REFUSED = "consent_refused"
    MOVE_TO_NEXT_QUESTION = "move_to_next_question"
    REPEAT_QUESTION = "repeat_question"
    ANSWER_CAPTURED = "answer_captured"
    SURVEY_COMPLETE = "survey_complete"
    UNCLEAR_RESPONSE = "unclear_response"

class ChatResponse(BaseModel):
    """Response from chat completion."""

    content: str
    model: str
    provider: LLMProvider
    usage: dict[str, int] = Field(default_factory=dict)
    correlation_id: str
    latency_ms: float
    control_signals: list[ControlSignal] = Field(default_factory=list)
    captured_answer: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

class LLMError(Exception):
    """Base exception for LLM gateway errors."""

    def __init__(
        self,
        message: str,
        correlation_id: str | None = None,
        provider: LLMProvider | None = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id
        self.provider = provider
        self.original_error = original_error

class LLMTimeoutError(LLMError):
    """Timeout error for LLM requests."""

    pass

class LLMRateLimitError(LLMError):
    """Rate limit error for LLM requests."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

class LLMAuthenticationError(LLMError):
    """Authentication error for LLM requests."""

    pass

class LLMProviderError(LLMError):
    """Generic provider error for LLM requests."""

    pass