# REQ-011: LLM Gateway Integration - Execution Guide

## Overview

This KIT implements the LLM gateway integration for the voicesurveyagent project. It provides:

- `LLMGateway` protocol defining the chat completion interface
- `OpenAIAdapter` for OpenAI API integration
- `AnthropicAdapter` for Anthropic API integration
- System prompt templates for survey dialogue
- Response parsing for control signals
- Factory function for creating gateway instances

## Prerequisites

### Required Software
- Python 3.12+
- pip (Python package manager)

### Environment Variables

For production use, set the appropriate API key:

bash
# For OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Optional: Set log level
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR

For testing, mock API keys are used automatically.

## Installation

bash
# From project root
pip install -r runs/kit/REQ-011/requirements.txt

## Running Tests

### Set PYTHONPATH

The tests require access to modules from REQ-001 and REQ-002:

bash
export PYTHONPATH="runs/kit/REQ-011/src:runs/kit/REQ-001/src:runs/kit/REQ-002/src"

### Run All Tests

bash
pytest runs/kit/REQ-011/test/ -v

### Run Individual Test Files

bash
# Test models
pytest runs/kit/REQ-011/test/test_llm_models.py -v

# Test prompts
pytest runs/kit/REQ-011/test/test_llm_prompts.py -v

# Test response parser
pytest runs/kit/REQ-011/test/test_llm_response_parser.py -v

# Test gateway interface
pytest runs/kit/REQ-011/test/test_llm_gateway.py -v

# Test OpenAI adapter
pytest runs/kit/REQ-011/test/test_llm_openai_adapter.py -v

# Test Anthropic adapter
pytest runs/kit/REQ-011/test/test_llm_anthropic_adapter.py -v

# Test factory
pytest runs/kit/REQ-011/test/test_llm_factory.py -v

### Run with Coverage

bash
pytest runs/kit/REQ-011/test/ -v --cov=runs/kit/REQ-011/src --cov-report=term-missing

## Usage Examples

### Creating an LLM Gateway

python
from app.dialogue.llm import create_llm_gateway, LLMProvider

# Create OpenAI gateway (reads OPENAI_API_KEY from env)
gateway = create_llm_gateway(provider=LLMProvider.OPENAI)

# Create with explicit API key
gateway = create_llm_gateway(
    provider="openai",
    api_key="sk-...",
    model="gpt-4.1-mini",
    timeout_seconds=30.0,
)

# Create Anthropic gateway
gateway = create_llm_gateway(
    provider=LLMProvider.ANTHROPIC,
    model="claude-3-5-sonnet-20241022",
)

### Making Chat Completion Requests

python
from app.dialogue.llm import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    SurveyContext,
)

# Simple request
request = ChatRequest(
    messages=[
        ChatMessage(role=MessageRole.USER, content="Hello"),
    ],
)
response = await gateway.chat_completion(request)
print(response.content)

# Request with survey context (auto-generates system prompt)
context = SurveyContext(
    campaign_name="Customer Satisfaction",
    language="en",
    intro_script="Hello, I'm calling about a brief survey...",
    question_1_text="How satisfied are you on a scale of 1-10?",
    question_1_type="scale",
    question_2_text="What could we improve?",
    question_2_type="free_text",
    question_3_text="Would you recommend us?",
    question_3_type="numeric",
    current_question=1,
    collected_answers=[],
)

request = ChatRequest(
    messages=[ChatMessage(role=MessageRole.USER, content="Yes, I agree")],
    survey_context=context,
)
response = await gateway.chat_completion(request)

# Check control signals
from app.dialogue.llm import ControlSignal
if ControlSignal.CONSENT_ACCEPTED in response.control_signals:
    print("User consented!")
if response.captured_answer:
    print(f"Captured answer: {response.captured_answer}")

### Error Handling

python
from app.dialogue.llm.models import (
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMProviderError,
)

try:
    response = await gateway.chat_completion(request)
except LLMTimeoutError as e:
    print(f"Request timed out: {e.correlation_id}")
except LLMRateLimitError as e:
    print(f"Rate limited, retry after: {e.retry_after}s")
except LLMAuthenticationError:
    print("Invalid API key")
except LLMProviderError as e:
    print(f"Provider error: {e}")

## Architecture

app/dialogue/
├── __init__.py           # Module exports
└── llm/
    ├── __init__.py       # LLM submodule exports
    ├── models.py         # Data models (ChatMessage, ChatRequest, etc.)
    ├── gateway.py        # LLMGateway protocol and BaseLLMAdapter
    ├── prompts.py        # System prompt templates
    ├── response_parser.py # Control signal extraction
    ├── openai_adapter.py  # OpenAI implementation
    ├── anthropic_adapter.py # Anthropic implementation
    └── factory.py        # Gateway factory function

## Control Signals

The LLM response parser extracts control signals from responses:

| Signal | Description |
|--------|-------------|
| `CONSENT_ACCEPTED` | User agreed to participate |
| `CONSENT_REFUSED` | User declined to participate |
| `ANSWER_CAPTURED` | An answer was captured (includes value) |
| `REPEAT_QUESTION` | User asked to repeat the question |
| `MOVE_TO_NEXT_QUESTION` | Ready to proceed to next question |
| `SURVEY_COMPLETE` | All questions answered |
| `UNCLEAR_RESPONSE` | Need clarification |

Signals are extracted from explicit `SIGNAL:` lines in the response or inferred from content patterns.

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`, ensure PYTHONPATH is set correctly:

bash
export PYTHONPATH="runs/kit/REQ-011/src:runs/kit/REQ-001/src:runs/kit/REQ-002/src"

### API Key Errors

Ensure the appropriate environment variable is set:

bash
# Check if set
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

### Timeout Issues

Increase timeout for slow networks:

python
gateway = create_llm_gateway(
    provider="openai",
    timeout_seconds=60.0,  # Increase from default 30s
)

### Rate Limiting

The adapters automatically retry with exponential backoff on rate limits. For high-volume usage, consider:

1. Using a lower `max_retries` value
2. Implementing request queuing
3. Using multiple API keys

## Integration with Other REQs

This module depends on:
- **REQ-001**: Database schema (for ProviderConfig model reference)
- **REQ-002**: Shared logging utilities

This module is used by:
- **REQ-012**: Dialogue orchestrator consent flow
- **REQ-013**: Dialogue orchestrator Q&A flow