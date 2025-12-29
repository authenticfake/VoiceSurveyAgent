# KIT Documentation: REQ-011 - LLM Gateway Integration

## Summary

REQ-011 implements the LLM gateway integration for the voicesurveyagent system. This provides a unified interface for chat completion requests to multiple LLM providers (OpenAI and Anthropic), with support for survey-specific system prompts, control signal extraction, timeout handling, and comprehensive error management.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| LLMGateway interface defines chat_completion method | ✅ | `gateway.py` - `LLMGateway` protocol |
| Gateway supports configurable provider (OpenAI, Anthropic) | ✅ | `factory.py` - `create_llm_gateway()` |
| System prompt includes survey context and constraints | ✅ | `prompts.py` - `build_system_prompt()` |
| Timeout handling with configurable duration | ✅ | Both adapters support `timeout_seconds` |
| Gateway errors logged with correlation ID | ✅ | All errors include `correlation_id` |

## Module Structure

runs/kit/REQ-011/
├── src/app/dialogue/
│   ├── __init__.py
│   └── llm/
│       ├── __init__.py
│       ├── models.py          # Data models
│       ├── gateway.py         # Protocol definition
│       ├── prompts.py         # System prompts
│       ├── response_parser.py # Signal extraction
│       ├── openai_adapter.py  # OpenAI implementation
│       ├── anthropic_adapter.py # Anthropic implementation
│       └── factory.py         # Factory function
├── test/
│   ├── test_llm_models.py
│   ├── test_llm_prompts.py
│   ├── test_llm_response_parser.py
│   ├── test_llm_gateway.py
│   ├── test_llm_openai_adapter.py
│   ├── test_llm_anthropic_adapter.py
│   └── test_llm_factory.py
├── ci/
│   ├── LTC.json
│   └── HOWTO.md
└── requirements.txt

## Key Components

### LLMGateway Protocol

The `LLMGateway` protocol defines the interface that all provider adapters must implement:

python
@runtime_checkable
class LLMGateway(Protocol):
    @property
    def provider(self) -> LLMProvider: ...
    
    @property
    def default_model(self) -> str: ...
    
    async def chat_completion(self, request: ChatRequest) -> ChatResponse: ...
    
    async def health_check(self) -> bool: ...

### Survey Context

The `SurveyContext` model captures all information needed to generate appropriate system prompts:

- Campaign name and language
- Intro script for consent
- Three survey questions with types
- Current question number
- Previously collected answers

### Control Signals

The response parser extracts control signals from LLM responses:

- `CONSENT_ACCEPTED` / `CONSENT_REFUSED`
- `ANSWER_CAPTURED` (with captured value)
- `REPEAT_QUESTION`
- `SURVEY_COMPLETE`
- `UNCLEAR_RESPONSE`

### Error Handling

Comprehensive error hierarchy:
- `LLMError` - Base exception
- `LLMTimeoutError` - Request timeout
- `LLMRateLimitError` - Rate limiting (includes `retry_after`)
- `LLMAuthenticationError` - Invalid API key
- `LLMProviderError` - Generic provider errors

All errors include `correlation_id` for tracing.

## Dependencies

- **httpx**: Async HTTP client for API calls
- **pydantic**: Data validation and models
- **REQ-001**: Shared database models (Base class)
- **REQ-002**: Shared logging utilities

## Test Coverage

| Test File | Coverage |
|-----------|----------|
| test_llm_models.py | Model creation, validation, enums |
| test_llm_prompts.py | System prompt generation |
| test_llm_response_parser.py | Signal extraction |
| test_llm_gateway.py | Protocol compliance |
| test_llm_openai_adapter.py | OpenAI integration |
| test_llm_anthropic_adapter.py | Anthropic integration |
| test_llm_factory.py | Factory function |

## Configuration

Environment variables:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `LOG_LEVEL` - Logging level (default: INFO)


## Future Enhancements

- Streaming response support
- Token counting and budget management
- Response caching
- Additional provider adapters (Google, Azure)