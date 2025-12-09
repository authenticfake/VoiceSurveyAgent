# HOWTO: REQ-020 Call Detail View API

## Prerequisites

### Required Tools

- Python 3.12+
- pip (Python package manager)
- PostgreSQL 14+ (for full integration testing)

### Optional Tools

- ruff (linting)
- mypy (type checking)
- Docker (for containerized database)

## Environment Setup

### 1. Create Virtual Environment

```bash
cd runs/kit/REQ-020
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

# For development tools
pip install ruff mypy bandit
```

### 3. Set PYTHONPATH

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### 4. Database Configuration (Optional)

For integration tests with real database:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/voicesurvey"
```

## Running Tests

### All Tests

```bash
cd runs/kit/REQ-020
PYTHONPATH=src pytest -v test/
```

### Unit Tests Only

```bash
PYTHONPATH=src pytest -v test/test_call_models.py test/test_call_detail_service.py
```

### Integration Tests Only

```bash
PYTHONPATH=src pytest -v test/test_call_detail_router.py
```

### With Coverage

```bash
PYTHONPATH=src pytest -v test/ --cov=app.calls --cov-report=xml:reports/coverage.xml
```

### With JUnit Report

```bash
PYTHONPATH=src pytest -v test/ --junitxml=reports/junit.xml
```

## Running the API Server

### Development Mode

```bash
cd runs/kit/REQ-020
PYTHONPATH=src uvicorn app.main:app --reload --port 8000
```

### Production Mode

```bash
PYTHONPATH=src uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Code Quality Checks

### Linting

```bash
cd runs/kit/REQ-020
ruff check src/ test/
```

### Type Checking

```bash
mypy src/app/calls --ignore-missing-imports
```

### Security Scan

```bash
bandit -r src/
```

## API Testing

### Using curl

```bash
# Get call detail (requires valid auth token)
curl -X GET "http://localhost:8000/api/calls/call-abc123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Using Postman

Import the collection from `test/api/calls.json`.

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Database Connection Issues

If tests fail with database errors:

1. Ensure PostgreSQL is running
2. Check DATABASE_URL environment variable
3. Run migrations from REQ-001 first

### Test Discovery Issues

If pytest doesn't find tests:

```bash
# Run from the correct directory
cd runs/kit/REQ-020
pytest -v test/ --collect-only
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run REQ-020 Tests
  run: |
    cd runs/kit/REQ-020
    pip install -r requirements.txt
    PYTHONPATH=src pytest -v test/ --junitxml=reports/junit.xml
```

### Jenkins

```groovy
stage('REQ-020 Tests') {
    dir('runs/kit/REQ-020') {
        sh 'pip install -r requirements.txt'
        sh 'PYTHONPATH=src pytest -v test/'
    }
}
```

## Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| JUnit Report | `reports/junit.xml` | Test results in JUnit format |
| Coverage Report | `reports/coverage.xml` | Code coverage in Cobertura format |
| API Collection | `test/api/calls.json` | Postman collection for API testing |
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-020**: Call detail view API

### Rationale
REQ-020 is the next open REQ-ID with all dependencies satisfied (REQ-014 is in_progress). This REQ implements the `GET /api/calls/{call_id}` endpoint for retrieving detailed call information.

### In Scope
- `GET /api/calls/{call_id}` endpoint implementation
- Response model with all required fields (outcome, attempt_number, timestamps, transcript, recording URL)
- RBAC enforcement (campaign_manager and admin only)
- 404 handling for non-existent calls
- Unit and integration tests
- API documentation (Postman collection)

### Out of Scope
- Database migrations (uses existing tables from REQ-001/REQ-014)
- Full OIDC integration (stubs provided, actual implementation in REQ-002)
- Recording storage/retrieval (URL extracted from metadata if present)

### How to Run Tests

```bash
cd runs/kit/REQ-020

# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run all tests
pytest -v test/

# Run specific test files
pytest -v test/test_call_detail_service.py  # Unit tests
pytest -v test/test_call_detail_router.py   # Integration tests
```

### Prerequisites
- Python 3.12+
- pytest, pytest-asyncio
- httpx (for async HTTP testing)
- FastAPI, Pydantic

### Dependencies and Mocks
- **FakeCallRepository**: In-memory repository for service unit tests
- **FakeCallDetailService**: Fake service for router integration tests
- **CurrentUser stub**: Overridable dependency for authentication
- **get_call_detail_service stub**: Overridable dependency for service injection

All mocks/fakes are used only in tests; production code uses real implementations via dependency injection.

### Product Owner Notes
- The endpoint follows the SPEC's interface definition for `GET /api/calls/{call_id}`
- Transcript snippets are optional and only included if stored in the database
- Recording URLs are extracted from call attempt metadata if present
- Access control is enforced at two levels: role-based (campaign_manager/admin) and campaign-based (future multi-tenant support)

### RAG Citations
- `runs/kit/REQ-019/src/app/shared/__init__.py` - Pattern for shared module structure
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Schema reference for call_attempts and transcript_snippets tables
- `runs/kit/REQ-018/src/app/shared/__init__.py` - Module documentation pattern

```json
{
  "index": [
    {
      "req": "REQ-020",
      "src": [
        "runs/kit/REQ-020/src/app/__init__.py",
        "runs/kit/REQ-020/src/app/shared/__init__.py",
        "runs/kit/REQ-020/src/app/calls/__init__.py",
        "runs/kit/REQ-020/src/app/calls/models.py",
        "runs/kit/REQ-020/src/app/calls/exceptions.py",
        "runs/kit/REQ-020/src/app/calls/repository.py",
        "runs/kit/REQ-020/src/app/calls/service.py",
        "runs/kit/REQ-020/src/app/calls/router.py",
        "runs/kit/REQ-020/src/app/main.py"
      ],
      "tests": [
        "runs/kit/REQ-020/test/__init__.py",
        "runs/kit/REQ-020/test/test_call_detail_service.py",
        "runs/kit/REQ-020/test/test_call_detail_router.py",
        "runs/kit/REQ-020/test/test_call_models.py",
        "runs/kit/REQ-020/test/api/calls.json"
      ],
      "docs": [
        "runs/kit/REQ-020/docs/KIT_REQ-020.md",
        "runs/kit/REQ-020/docs/README_REQ-020.md"
      ],
      "ci": [
        "runs/kit/REQ-020/ci/LTC.json",
        "runs/kit/REQ-020/ci/HOWTO.md"
      ]
    }
  ]
}