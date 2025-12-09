# REQ-013: Dialogue Orchestrator Q&A Flow - Execution Guide

## Overview

This KIT implements the Q&A flow orchestration for the voice survey agent, handling:
- Sequential question delivery (Q1 → Q2 → Q3)
- Answer capture and validation
- Repeat request detection (max 1 repeat per question)
- State transitions between questions
- Natural language generation for question delivery and acknowledgments

## Prerequisites

### Required Software
- Python 3.12+
- pip (Python package manager)

### Dependencies
The following packages are required (installed via requirements.txt):
- pytest >= 8.0.0
- pytest-asyncio >= 0.23.0
- pytest-cov >= 4.1.0

### Environment Setup

```bash
# Set PYTHONPATH to include source directories
export PYTHONPATH="runs/kit/REQ-013/src:runs/kit/REQ-012/src:runs/kit/REQ-011/src"

# Optional: Set log level
export LOG_LEVEL="INFO"
```

## Running Tests

### Install Dependencies

```bash
pip install -r runs/kit/REQ-013/requirements.txt
```

### Run All Tests

```bash
# From project root
python -m pytest runs/kit/REQ-013/test/ -v
```

### Run Unit Tests Only

```bash
python -m pytest runs/kit/REQ-013/test/test_qa_orchestrator.py -v
```

### Run Integration Tests Only

```bash
python -m pytest runs/kit/REQ-013/test/test_qa_integration.py -v
```

### Run with Coverage

```bash
python -m pytest runs/kit/REQ-013/test/ \
  --cov=runs/kit/REQ-013/src \
  --cov-report=xml:runs/kit/REQ-013/reports/coverage.xml \
  --cov-report=term-missing \
  --junitxml=runs/kit/REQ-013/reports/junit.xml
```

## Module Structure

```
runs/kit/REQ-013/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── shared/
│       │   ├── __init__.py
│       │   └── logging.py
│       └── dialogue/
│           ├── __init__.py
│           ├── models.py      # DialogueSession, QuestionState, etc.
│           └── qa.py          # QAOrchestrator
├── test/
│   ├── test_qa_orchestrator.py    # Unit tests
│   └── test_qa_integration.py     # Integration tests
├── ci/
│   ├── LTC.json
│   └── HOWTO.md
├── docs/
│   ├── KIT_REQ-013.md
│   └── README_REQ-013.md
└── requirements.txt
```

## Key Components

### QAOrchestrator

The main orchestrator class that handles:
- `generate_question_delivery()` - Creates natural language question delivery
- `process_user_response()` - Extracts answers or detects intents
- `handle_answer()` - Updates session state and determines next phase
- `start_qa_flow()` - Initiates the Q&A sequence
- `should_repeat_question()` - Checks if repeat is needed

### DialogueSession

Maintains the complete dialogue state including:
- Current phase (QUESTION_1, QUESTION_2, QUESTION_3, COMPLETION)
- Question states (NOT_ASKED, ASKED, REPEAT_REQUESTED, ANSWERED)
- Captured answers with confidence scores
- Repeat counts per question

### UserIntent

Detected intents from user responses:
- ANSWER - User provided a valid answer
- REPEAT_REQUEST - User asked to repeat the question
- UNCLEAR - Cannot determine intent
- OFF_TOPIC - Response unrelated to question

## Integration with REQ-012

This module extends the dialogue flow from REQ-012 (consent flow):
- After consent is granted, `start_qa_flow()` transitions to QUESTION_1
- Uses the same `DialogueSession` and `CallContext` models
- Shares the `LLMGatewayProtocol` interface

## Troubleshooting

### Import Errors

If you see import errors, ensure PYTHONPATH includes all required source directories:

```bash
export PYTHONPATH="runs/kit/REQ-013/src:runs/kit/REQ-012/src:runs/kit/REQ-011/src"
```

### Test Discovery Issues

Ensure pytest-asyncio is installed for async test support:

```bash
pip install pytest-asyncio
```

### Coverage Reports Not Generated

Create the reports directory if it doesn't exist:

```bash
mkdir -p runs/kit/REQ-013/reports
```

## CI/CD Integration

The LTC.json file defines the test contract for CI runners:

1. `install_deps` - Installs Python dependencies
2. `unit_tests` - Runs unit tests
3. `integration_tests` - Runs integration tests
4. `all_tests_with_coverage` - Full test suite with coverage reporting

Gate policy requires:
- All tests pass
- Minimum 80% code coverage
- No high-severity security issues