"""
LLM Gateway module for chat completion integration.

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
]