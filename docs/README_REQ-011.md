# REQ-011: LLM Gateway Integration

## Quick Start

bash
# Install dependencies
pip install -r runs/kit/REQ-011/requirements.txt

# Set API key
export OPENAI_API_KEY="your-key"

# Run tests
PYTHONPATH="runs/kit/REQ-011/src:runs/kit/REQ-001/src:runs/kit/REQ-002/src" \
  pytest runs/kit/REQ-011/test/ -v

## Usage

python
from app.dialogue.llm import create_llm_gateway, ChatRequest, ChatMessage, MessageRole

# Create gateway
gateway = create_llm_gateway(provider="openai")

# Make request
request = ChatRequest(
    messages=[ChatMessage(role=MessageRole.USER, content="Hello")]
)
response = await gateway.chat_completion(request)
print(response.content)

## Documentation

- [Full HOWTO Guide](ci/HOWTO.md)
- [KIT Documentation](docs/KIT_REQ-011.md)

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-011**: LLM gateway integration

### Rationale
REQ-011 is the next open REQ that depends only on REQ-001 (database schema), which is already in_progress. This REQ provides the foundational LLM integration needed by REQ-012 (consent flow) and REQ-013 (Q&A flow).

### In Scope
- `LLMGateway` protocol definition with `chat_completion` method
- OpenAI adapter implementation with retry logic
- Anthropic adapter implementation with retry logic
- System prompt templates for survey context
- Response parser for control signal extraction
- Factory function for gateway creation
- Configurable timeout handling
- Comprehensive error types with correlation ID
- Unit tests for all components

### Out of Scope
- Streaming responses (future enhancement)
- Token budget management
- Response caching
- Additional providers (Google, Azure)
- Integration with actual telephony (REQ-012 scope)

### How to Run Tests

bash
# Set PYTHONPATH
export PYTHONPATH="runs/kit/REQ-011/src:runs/kit/REQ-001/src:runs/kit/REQ-002/src"

# Install dependencies
pip install -r runs/kit/REQ-011/requirements.txt

# Run all tests
pytest runs/kit/REQ-011/test/ -v

# Run specific test file
pytest runs/kit/REQ-011/test/test_llm_openai_adapter.py -v

### Prerequisites
- Python 3.12+
- httpx, pydantic, pytest, pytest-asyncio
- For production: Valid OPENAI_API_KEY or ANTHROPIC_API_KEY

### Dependencies and Mocks
- **httpx.AsyncClient**: Mocked in adapter tests to avoid real API calls
- **API keys**: Test keys used in unit tests; real keys needed for integration
- **Shared logging**: Uses `app.shared.logging` from REQ-002 structure

### Product Owner Notes
- The system prompt template includes prohibited topics (political, religious) as specified in SPEC
- Control signals are designed to be explicit (`SIGNAL:` prefix) but also inferred from content patterns for robustness
- Both OpenAI and Anthropic adapters implement identical retry logic with exponential backoff
- The factory function supports both enum and string provider names for flexibility

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Referenced for ProviderConfig entity structure (llm_provider, llm_model fields)
- `runs/kit/REQ-002/src/app/shared/__init__.py` - Reused shared module structure
- `runs/kit/REQ-010/src/app/shared/logging.py` - Pattern for structured logging

json
{
  "index": [
    {
      "req": "REQ-011",
      "src": [
        "runs/kit/REQ-011/src/app/__init__.py",
        "runs/kit/REQ-011/src/app/dialogue/__init__.py",
        "runs/kit/REQ-011/src/app/dialogue/llm/__init__.py",
        "runs/kit/REQ-011/src/app/dialogue/llm/models.py",
        "runs/kit/REQ-011/src/app/dialogue/llm/gateway.py",
        "runs/kit/REQ-011/src/app/dialogue/llm/prompts.py",
        "runs/kit/REQ-011/src/app/dialogue/llm/response_parser.py",
        "runs/kit/REQ-011/src/app/dialogue/llm/openai_adapter.py",
        "runs/kit/REQ-011/src/app/dialogue/llm/anthropic_adapter.py",
        "runs/kit/REQ-011/src/app/dialogue/llm/factory.py",
        "runs/kit/REQ-011/src/app/shared/__init__.py",
        "runs/kit/REQ-011/src/app/shared/logging.py"
      ],
      "tests": [
        "runs/kit/REQ-011/test/__init__.py",
        "runs/kit/REQ-011/test/test_llm_models.py",
        "runs/kit/REQ-011/test/test_llm_prompts.py",
        "runs/kit/REQ-011/test/test_llm_response_parser.py",
        "runs/kit/REQ-011/test/test_llm_gateway.py",
        "runs/kit/REQ-011/test/test_llm_openai_adapter.py",
        "runs/kit/REQ-011/test/test_llm_anthropic_adapter.py",
        "runs/kit/REQ-011/test/test_llm_factory.py"
      ]
    }
  ]
}