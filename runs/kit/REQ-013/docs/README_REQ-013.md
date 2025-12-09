# REQ-013: Dialogue Orchestrator Q&A Flow

## Summary

This module implements the Q&A flow orchestration for the voice survey agent. After consent is granted (REQ-012), this orchestrator manages the sequential delivery of 3 survey questions, captures user answers, handles repeat requests, and transitions the dialogue to completion.

## Features

- **Sequential Question Flow**: Questions are asked in order (Q1 → Q2 → Q3)
- **Natural Language Delivery**: LLM generates conversational question delivery
- **Answer Extraction**: LLM extracts answers from natural language responses
- **Repeat Handling**: Users can request one repeat per question
- **Multi-Language Support**: English and Italian
- **Confidence Scoring**: Each answer includes a confidence score
- **Graceful Fallbacks**: Continues operation even if LLM fails

## Quick Start

```python
from app.dialogue.qa import QAOrchestrator
from app.dialogue.models import DialogueSession, CallContext

# Create orchestrator with LLM gateway
orchestrator = QAOrchestrator(llm_gateway)

# Start Q&A after consent
phase = orchestrator.start_qa_flow(session)

# Generate question delivery
delivery = await orchestrator.generate_question_delivery(session, 1)

# Process user response
result = await orchestrator.process_user_response(session, user_response)

# Handle the answer and get next phase
next_phase = orchestrator.handle_answer(session, result)
```

## Module Structure

```
src/app/dialogue/
├── __init__.py      # Public exports
├── models.py        # DialogueSession, QuestionState, QuestionAnswer
└── qa.py            # QAOrchestrator, AnswerResult, UserIntent
```

## Key Classes

### QAOrchestrator

Main orchestrator for the Q&A flow. Handles:
- Question delivery generation
- User response processing
- Answer capture and validation
- State transitions

### DialogueSession

Maintains dialogue state including:
- Current phase (QUESTION_1, QUESTION_2, QUESTION_3, COMPLETION)
- Question states and answers
- Repeat counts

### AnswerResult

Result of processing a user response:
- `intent`: ANSWER, REPEAT_REQUEST, UNCLEAR, or OFF_TOPIC
- `answer_text`: Extracted answer (if any)
- `confidence`: 0.0 to 1.0

## State Transitions

```
CONSENT_GRANTED → QUESTION_1 → QUESTION_2 → QUESTION_3 → COMPLETION
                      ↑              ↑              ↑
                      └──────────────┴──────────────┘
                         (repeat or unclear stays)
```

## Configuration

Questions are configured in `CallContext.questions`:

```python
questions = [
    ("How satisfied are you on a scale of 1-10?", "scale"),
    ("What could we improve?", "free_text"),
    ("How often do you use our service?", "numeric"),
]
```

## Testing

```bash
# Run all tests
python -m pytest runs/kit/REQ-013/test/ -v

# Run with coverage
python -m pytest runs/kit/REQ-013/test/ --cov=runs/kit/REQ-013/src
```

## Dependencies

- REQ-012: Consent flow (provides DialogueSession after consent)
- REQ-011: LLM gateway (provides chat_completion interface)
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-013**: Dialogue orchestrator Q&A flow

### Rationale
REQ-013 depends on REQ-012 (consent flow) which is marked as `in_progress`. This REQ implements the sequential Q&A flow that follows consent, handling question delivery, answer capture, repeat requests, and state transitions through all 3 survey questions.

### In Scope
- `QAOrchestrator` class for managing Q&A flow
- Question delivery generation with LLM
- Answer extraction and intent detection
- Repeat request handling (max 1 per question)
- State transitions (Q1 → Q2 → Q3 → COMPLETION)
- `QuestionState` enum and `QuestionAnswer` dataclass
- Unit and integration tests
- LTC.json and HOWTO.md

### Out of Scope
- Database persistence of answers (REQ-014)
- Event publishing (REQ-015)
- Telephony integration (handled by REQ-010)
- Actual LLM provider implementation (uses protocol/interface)

### How to Run Tests

```bash
# Set PYTHONPATH
export PYTHONPATH="runs/kit/REQ-013/src:runs/kit/REQ-012/src:runs/kit/REQ-011/src"

# Install dependencies
pip install -r runs/kit/REQ-013/requirements.txt

# Run all tests
python -m pytest runs/kit/REQ-013/test/ -v

# Run with coverage
python -m pytest runs/kit/REQ-013/test/ \
  --cov=runs/kit/REQ-013/src \
  --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- pytest, pytest-asyncio, pytest-cov
- Access to REQ-012 source (for DialogueSession models)

### Dependencies and Mocks
- **LLMGatewayProtocol**: Mocked in tests using `AsyncMock` and custom `MockLLMGateway`
- **DialogueSession**: Reused from REQ-012 models
- No external services required for testing

### Product Owner Notes
- Maximum 1 repeat per question as per SPEC ("simple repetitions upon user request")
- Unclear responses keep user on same question without counting as repeat
- Confidence scores provided for each answer to support future quality analysis
- Italian language support included per SPEC requirements

### RAG Citations
- `runs/kit/REQ-012/src/app/dialogue/consent.py` - Reused `LLMGatewayProtocol` interface pattern
- `runs/kit/REQ-012/src/app/dialogue/models.py` - Extended `DialogueSession` and `DialogueSessionState`
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Referenced `survey_responses` table schema for answer structure
- `runs/kit/REQ-011/src/app/shared/__init__.py` - Followed shared module pattern

### Index

```json
{
  "index": [
    {
      "req": "REQ-013",
      "src": [
        "runs/kit/REQ-013/src/app/__init__.py",
        "runs/kit/REQ-013/src/app/shared/__init__.py",
        "runs/kit/REQ-013/src/app/shared/logging.py",
        "runs/kit/REQ-013/src/app/dialogue/__init__.py",
        "runs/kit/REQ-013/src/app/dialogue/models.py",
        "runs/kit/REQ-013/src/app/dialogue/qa.py"
      ],
      "tests": [
        "runs/kit/REQ-013/test/test_qa_orchestrator.py",
        "runs/kit/REQ-013/test/test_qa_integration.py"
      ]
    }
  ]
}