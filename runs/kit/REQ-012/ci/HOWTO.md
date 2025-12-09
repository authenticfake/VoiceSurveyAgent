# REQ-012: Execution HOWTO

## Prerequisites

- Python 3.12+
- pip (latest version recommended)

## Environment Setup

### Option 1: Virtual Environment (Recommended)

bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
cd runs/kit/REQ-012
pip install -r requirements.txt

### Option 2: PYTHONPATH

bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/runs/kit/REQ-012/src"
cd runs/kit/REQ-012
pip install -r requirements.txt

## Running Tests

### All Tests

bash
cd runs/kit/REQ-012
PYTHONPATH=src pytest -v test/

### With Coverage

bash
cd runs/kit/REQ-012
PYTHONPATH=src pytest -v test/ --cov=app --cov-report=html

### Specific Test File

bash
cd runs/kit/REQ-012
PYTHONPATH=src pytest -v test/test_consent_flow.py

## Linting

bash
cd runs/kit/REQ-012
ruff check src/ test/

## Type Checking

bash
cd runs/kit/REQ-012
mypy src/ --ignore-missing-imports

## CI/CD Integration

### GitHub Actions

The LTC.json file defines the test contract. In CI:

yaml
- name: Run REQ-012 Tests
  run: |
    cd runs/kit/REQ-012
    pip install -r requirements.txt
    PYTHONPATH=src pytest -v test/ --junitxml=reports/junit.xml

### Jenkins

groovy
stage('REQ-012 Tests') {
    dir('runs/kit/REQ-012') {
        sh 'pip install -r requirements.txt'
        sh 'PYTHONPATH=src pytest -v test/ --junitxml=reports/junit.xml'
    }
}

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

1. Ensure PYTHONPATH includes the src directory:
   bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/runs/kit/REQ-012/src"
   

2. Or run pytest from the correct directory:
   bash
   cd runs/kit/REQ-012
   PYTHONPATH=src pytest test/
   

### Missing Dependencies

bash
pip install pytest pytest-asyncio pytest-cov mypy ruff

### Test Failures

Check that:
1. All mock classes implement the required protocols
2. Async tests use `@pytest.mark.asyncio` decorator
3. pytest-asyncio is installed

## Artifacts

After running tests with coverage:

- `reports/junit.xml` - JUnit test results
- `reports/coverage.xml` - Coverage report (XML)
- `htmlcov/` - Coverage report (HTML, if --cov-report=html used)

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-012**: Dialogue orchestrator consent flow

### Rationale
REQ-012 depends on REQ-010 (Telephony webhook handler) and REQ-011 (LLM gateway integration), both of which are marked as `in_progress` in the plan. This REQ implements the consent flow that triggers when a call is answered, using the LLM gateway for intent detection and telephony control for call management.

### In Scope
- Consent detection using LLM with fallback keyword matching
- Consent flow orchestration (intro → consent question → response handling)
- Session management for tracking dialogue state
- Event publishing for `survey.refused`
- Support for English and Italian languages
- Handling of positive, negative, unclear, and repeat-request intents
- Call termination on refusal
- Transcript recording

### Out of Scope
- Q&A flow (REQ-013)
- Survey response persistence (REQ-014)
- Actual telephony provider integration (uses protocol/interface)
- Actual LLM provider integration (uses protocol/interface)
- Database persistence of sessions

### How to Run Tests

bash
# Navigate to REQ-012 directory
cd runs/kit/REQ-012

# Install dependencies
pip install -r requirements.txt

# Run all tests
PYTHONPATH=src pytest -v test/

# Run with coverage
PYTHONPATH=src pytest -v test/ --cov=app --cov-report=html

# Run specific test file
PYTHONPATH=src pytest -v test/test_consent_flow.py

### Prerequisites
- Python 3.12+
- pytest >= 8.0.0
- pytest-asyncio >= 0.23.0
- ruff >= 0.2.0 (for linting)
- mypy >= 1.8.0 (for type checking)

### Dependencies and Mocks
All external dependencies are mocked for testing:
- **MockLLMGateway**: Simulates LLM responses for consent detection
- **MockTelephonyControl**: Captures play_text and terminate_call calls
- **MockEventPublisher**: Captures published events
- **MockEventBus**: Captures raw event bus messages

These mocks implement the protocols defined in the consent module, allowing the tests to run without actual external services.

### Product Owner Notes
- The consent detection uses a conservative approach: unclear responses after 2 attempts are treated as refusal
- Italian language support includes common consent/refusal phrases
- The 10-second termination requirement is met by immediate call termination after refusal detection
- Transcript recording enables future audit and compliance requirements

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Referenced for understanding the database schema and enum types
- `runs/kit/REQ-011/src/app/shared/__init__.py` - Referenced for shared module structure
- `runs/kit/REQ-010/src/app/auth/models.py` - Referenced for Base class pattern
- `runs/kit/REQ-003/src/app/auth/rbac.py` - Referenced for logging patterns

json
{
  "index": [
    {
      "req": "REQ-012",
      "src": [
        "runs/kit/REQ-012/src/app/__init__.py",
        "runs/kit/REQ-012/src/app/shared/__init__.py",
        "runs/kit/REQ-012/src/app/shared/logging.py",
        "runs/kit/REQ-012/src/app/dialogue/__init__.py",
        "runs/kit/REQ-012/src/app/dialogue/models.py",
        "runs/kit/REQ-012/src/app/dialogue/consent.py",
        "runs/kit/REQ-012/src/app/dialogue/events.py",
        "runs/kit/REQ-012/src/app/dialogue/integration.py"
      ],
      "tests": [
        "runs/kit/REQ-012/test/test_consent_detector.py",
        "runs/kit/REQ-012/test/test_consent_flow.py",
        "runs/kit/REQ-012/test/test_dialogue_models.py",
        "runs/kit/REQ-012/test/test_dialogue_events.py",
        "runs/kit/REQ-012/test/test_dialogue_integration.py"
      ]
    }
  ]
}