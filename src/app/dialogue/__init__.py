"""
Dialogue module for LLM integration and conversation orchestration.

REQ-011: LLM gateway integration
"""

from app.dialogue.llm.gateway import LLMGateway
from app.dialogue.llm.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LLMProvider,
    MessageRole,
)
from app.dialogue.llm.openai_adapter import OpenAIAdapter, OpenAIRealtimeSession
from app.dialogue.llm.anthropic_adapter import AnthropicAdapter
from app.dialogue.llm.factory import create_llm_gateway
from app.dialogue.consent import (
    ConsentDetector,
    ConsentFlowOrchestrator,
    ConsentIntent,
    ConsentResult,
)
from app.dialogue.events import (
    DialogueEvent,
    DialogueEventPublisher,
    DialogueEventType,
)

from app.dialogue.models import (
    CallContext,
    ConsentState,
    DialoguePhase,
    DialogueSession,
    DialogueSessionState,
    QuestionState,
)
from app.dialogue.qa import (
    AnswerResult,
    QAOrchestrator,
    QuestionDelivery,
    UserIntent,
)

__all__ = [
    "LLMGateway",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "LLMProvider",
    "MessageRole",
    "OpenAIAdapter",
    "OpenAIRealtimeSession",
    "AnthropicAdapter",
    "create_llm_gateway",
    "CallContext",
    "ConsentDetector",
    "ConsentFlowOrchestrator",
    "ConsentIntent",
    "ConsentResult",
    "ConsentState",
    "DialogueEvent",
    "DialogueEventPublisher",
    "DialogueEventType",
    "DialoguePhase",
    "DialogueSession",
    "DialogueSessionState",
    "QuestionState",
    "AnswerResult",
    "QAOrchestrator",
    "QuestionDelivery",
    "UserIntent",
]