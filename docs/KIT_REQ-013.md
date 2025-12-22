# KIT Documentation: REQ-013 - Dialogue Orchestrator Q&A Flow

## Requirement Summary

**REQ-013: Dialogue orchestrator Q&A flow**

Implements the sequential question-and-answer flow for the voice survey agent, handling question delivery, answer capture, repeat requests, and state transitions through all 3 survey questions.

## Acceptance Criteria

| Criterion | Implementation | Status |
|-----------|----------------|--------|
| Questions asked sequentially after consent | `QAOrchestrator.start_qa_flow()` transitions to Q1, then Q2, Q3 | ✅ |
| Each question text from campaign configuration | `DialogueSession.get_question_text()` retrieves from `CallContext.questions` | ✅ |
| Answer captured and stored in draft state | `QAOrchestrator.handle_answer()` stores `QuestionAnswer` in session | ✅ |
| Repeat request detected and question re-asked once | `UserIntent.REPEAT_REQUEST` detected, max 1 repeat per question | ✅ |
| All 3 answers captured before completion flow | `DialogueSession.all_questions_answered()` validates, transitions to COMPLETION | ✅ |

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     QAOrchestrator                          │
├─────────────────────────────────────────────────────────────┤
│ + generate_question_delivery(session, q_num, is_repeat)     │
│ + process_user_response(session, response) -> AnswerResult  │
│ + handle_answer(session, result) -> DialoguePhase           │
│ + start_qa_flow(session) -> DialoguePhase                   │
│ + should_repeat_question(session) -> bool                   │
│ + generate_acknowledgment(session, answer) -> str           │
│ + generate_completion_message(session) -> str               │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   LLMGatewayProtocol                        │
├─────────────────────────────────────────────────────────────┤
│ + chat_completion(messages, system_prompt, ...) -> str      │
└─────────────────────────────────────────────────────────────┘
```

### State Machine

```
                    ┌──────────────┐
                    │   CONSENT    │
                    │   GRANTED    │
                    └──────┬───────┘
                           │ start_qa_flow()
                           ▼
                    ┌──────────────┐
              ┌────►│  QUESTION_1  │◄────┐
              │     └──────┬───────┘     │
              │            │             │
    repeat    │            │ answer      │ unclear/
    (max 1)   │            ▼             │ off-topic
              │     ┌──────────────┐     │
              └─────│   handle     │─────┘
                    │   answer     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
              ┌────►│  QUESTION_2  │◄────┐
              │     └──────┬───────┘     │
              │            │             │
              │            ▼             │
              └─────[same pattern]───────┘
                           │
                           ▼
                    ┌──────────────┐
              ┌────►│  QUESTION_3  │◄────┐
              │     └──────┬───────┘     │
              │            │             │
              │            ▼             │
              └─────[same pattern]───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  COMPLETION  │
                    └──────────────┘
```

## Key Design Decisions

### 1. Maximum One Repeat Per Question

**Decision**: Limit repeat requests to 1 per question.

**Rationale**: 
- Prevents infinite loops in the dialogue
- Balances user experience with survey completion
- Aligns with SPEC requirement for "simple repetitions"

**Implementation**: `MAX_REPEATS_PER_QUESTION = 1` in `QAOrchestrator`

### 2. LLM-Based Answer Extraction

**Decision**: Use LLM to extract answers and detect intents.

**Rationale**:
- Handles natural language variations
- Supports multiple question types (scale, numeric, free_text)
- Provides confidence scores for answer quality

**Implementation**: `_build_answer_extraction_prompt()` with structured output format

### 3. Fallback Mechanisms

**Decision**: Provide fallbacks when LLM fails.

**Rationale**:
- Ensures survey can continue even with LLM errors
- Maintains user experience during degraded conditions

**Implementation**: 
- Question delivery falls back to raw question text
- Acknowledgments fall back to simple "Thank you"
- Completion messages have language-specific defaults

### 4. Draft State for Answers

**Decision**: Store answers immediately in session state.

**Rationale**:
- Enables recovery if call drops
- Supports future persistence to database
- Allows review before final submission

**Implementation**: `QuestionAnswer` dataclass with `captured_at` timestamp

## Dependencies

### Upstream (Required)
- **REQ-012**: Dialogue orchestrator consent flow
  - Provides `DialogueSession`, `CallContext`, `ConsentState`
  - Consent must be granted before Q&A starts

- **REQ-011**: LLM gateway integration
  - Provides `LLMGatewayProtocol` interface
  - Used for question delivery and answer extraction

### Downstream (Consumers)
- **REQ-014**: Survey response persistence
  - Will consume `DialogueSession.get_all_answers()`
  - Will persist `QuestionAnswer` objects to database

## Test Coverage

### Unit Tests (`test_qa_orchestrator.py`)
- Question delivery generation
- Answer extraction parsing
- State transitions
- Repeat request handling
- Acknowledgment generation

### Integration Tests (`test_qa_integration.py`)
- Complete Q&A flow (all 3 questions)
- Flow with repeat requests
- Max repeats enforcement
- Unclear response handling
- Italian language support

## API Reference

### QAOrchestrator

```python
class QAOrchestrator:
    MAX_REPEATS_PER_QUESTION = 1
    
    def __init__(self, llm_gateway: LLMGatewayProtocol) -> None: ...
    
    async def generate_question_delivery(
        self,
        session: DialogueSession,
        question_number: int,
        is_repeat: bool = False,
    ) -> QuestionDelivery: ...
    
    async def process_user_response(
        self,
        session: DialogueSession,
        user_response: str,
    ) -> AnswerResult: ...
    
    def handle_answer(
        self,
        session: DialogueSession,
        answer_result: AnswerResult,
    ) -> DialoguePhase: ...
    
    def start_qa_flow(self, session: DialogueSession) -> DialoguePhase: ...
    
    def should_repeat_question(self, session: DialogueSession) -> bool: ...
    
    async def generate_acknowledgment(
        self,
        session: DialogueSession,
        answer: QuestionAnswer,
    ) -> str: ...
    
    async def generate_completion_message(
        self,
        session: DialogueSession,
    ) -> str: ...
```

### Data Classes

```python
@dataclass
class AnswerResult:
    intent: UserIntent
    answer_text: str | None
    confidence: float
    raw_response: str
    reasoning: str | None = None

@dataclass
class QuestionDelivery:
    question_number: int
    question_text: str
    question_type: str
    delivery_text: str
    is_repeat: bool = False

@dataclass
class QuestionAnswer:
    question_number: int
    question_text: str
    answer_text: str
    confidence: float
    captured_at: datetime
    was_repeated: bool = False
```

### Enums

```python
class UserIntent(str, Enum):
    ANSWER = "answer"
    REPEAT_REQUEST = "repeat_request"
    UNCLEAR = "unclear"
    OFF_TOPIC = "off_topic"

class QuestionState(str, Enum):
    NOT_ASKED = "not_asked"
    ASKED = "asked"
    REPEAT_REQUESTED = "repeat_requested"
    ANSWERED = "answered"