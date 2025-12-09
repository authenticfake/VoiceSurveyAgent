# HOWTO: REQ-014 Survey Response Persistence

## Prerequisites

### Required Software
- Python 3.12+
- PostgreSQL 14+ (for integration tests)
- pip or uv package manager

### Environment Setup

1. **Create virtual environment**:
   ```bash
   cd runs/kit/REQ-014
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate  # Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set PYTHONPATH**:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

4. **Configure database** (for integration tests):
   ```bash
   export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey"
   ```

## Running Tests

### Unit Tests (No Database Required)

```bash
cd runs/kit/REQ-014
pytest test/test_persistence.py -v
```

### Integration Tests (Requires Database)

```bash
cd runs/kit/REQ-014
export SKIP_INTEGRATION_TESTS=false
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey"
pytest test/test_persistence_integration.py -v
```

### All Tests with Coverage

```bash
pytest test/ -v --cov=src/app --cov-report=term-missing --cov-report=xml:reports/coverage.xml
```

### Generate JUnit Report

```bash
pytest test/ -v --junitxml=reports/junit.xml
```

## Type Checking

```bash
cd runs/kit/REQ-014
mypy src/app --ignore-missing-imports
```

## Linting

```bash
cd runs/kit/REQ-014
ruff check src/ test/
```

## Security Scan

```bash
cd runs/kit/REQ-014
bandit -r src/ -ll
```

## CI/CD Integration

### GitHub Actions

The LTC.json file defines test cases that can be executed by the Harper eval runner:

```yaml
- name: Run REQ-014 Tests
  run: |
    cd runs/kit/REQ-014
    pip install -r requirements.txt
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
    pytest test/ -v --junitxml=reports/junit.xml
```

### Jenkins

```groovy
stage('REQ-014 Tests') {
    steps {
        dir('runs/kit/REQ-014') {
            sh 'pip install -r requirements.txt'
            sh 'export PYTHONPATH="${PYTHONPATH}:$(pwd)/src" && pytest test/ -v'
        }
    }
}
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

1. Ensure PYTHONPATH includes the src directory:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

2. Or run pytest with the path:
   ```bash
   PYTHONPATH=src pytest test/ -v
   ```

### Database Connection Issues

1. Verify PostgreSQL is running:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Check DATABASE_URL format:
   ```
   postgresql+asyncpg://user:password@host:port/database
   ```

3. Ensure database exists and schema is applied (REQ-001 migrations)

### Async Test Issues

If async tests fail with event loop errors:

1. Ensure pytest-asyncio is installed
2. Check pytest.ini or pyproject.toml has:
   ```ini
   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   ```

## Artifacts

After running tests, find reports in:
- `reports/junit.xml` - JUnit test results
- `reports/coverage.xml` - Coverage report
- `.coverage` - Coverage data file
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-014**: Survey response persistence

### Rationale
REQ-014 depends on REQ-013 (Dialogue orchestrator Q&A flow) which is marked as `in_progress`. This REQ implements the persistence layer that stores completed survey responses atomically, ensuring all database updates (survey response creation, contact state update, call attempt outcome update) happen within a single transaction.

### In Scope
- `SurveyResponse` entity creation with all 3 answers
- Linking response to successful `CallAttempt`
- Updating `Contact` state to `completed`
- Recording completion timestamps
- Transaction atomicity for all updates
- Idempotency handling for duplicate persistence attempts
- Refused survey persistence

### Out of Scope
- Event publishing (REQ-015)
- Email notifications (REQ-016)
- Dashboard stats (REQ-017)
- Actual database migrations (handled by REQ-001)

### How to Run Tests

```bash
# Navigate to REQ-014 directory
cd runs/kit/REQ-014

# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run unit tests
pytest test/test_persistence.py -v

# Run all tests with coverage
pytest test/ -v --cov=src/app --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- PostgreSQL database with REQ-001 schema applied (for integration tests)
- Environment variables:
  - `DATABASE_URL`: PostgreSQL connection string
  - `SKIP_INTEGRATION_TESTS`: Set to `false` to run integration tests

### Dependencies and Mocks
- **Mocked**: Database session (`AsyncSession`), repositories in unit tests
- **Real**: SQLAlchemy models, domain models
- **Why**: Unit tests should not require database; integration tests verify actual persistence

### Product Owner Notes
- The persistence service is designed to be idempotent - calling `persist_completed_survey` multiple times with the same dialogue session will return the existing response rather than creating duplicates
- Confidence scores are stored per answer to support future quality analysis
- The service validates that exactly 3 answers are present before persisting

### RAG Citations
- `runs/kit/REQ-013/src/app/dialogue/models.py` - Reused `DialogueSession`, `CapturedAnswer`, `DialoguePhase`, `ConsentState`, `DialogueSessionState` models
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Referenced for database schema (survey_responses, contacts, call_attempts tables)
- `runs/kit/REQ-012/src/app/dialogue/consent.py` - Referenced for consent flow patterns
- `runs/kit/REQ-013/src/app/shared/__init__.py` - Extended shared module documentation

```json
{
  "index": [
    {
      "req": "REQ-014",
      "src": [
        "runs/kit/REQ-014/src/app/__init__.py",
        "runs/kit/REQ-014/src/app/shared/__init__.py",
        "runs/kit/REQ-014/src/app/shared/logging.py",
        "runs/kit/REQ-014/src/app/shared/database.py",
        "runs/kit/REQ-014/src/app/dialogue/__init__.py",
        "runs/kit/REQ-014/src/app/dialogue/models.py",
        "runs/kit/REQ-014/src/app/dialogue/persistence.py",
        "runs/kit/REQ-014/src/app/dialogue/persistence_models.py"
      ],
      "tests": [
        "runs/kit/REQ-014/test/test_persistence.py",
        "runs/kit/REQ-014/test/test_persistence_integration.py"
      ]
    }
  ]
}