# HOWTO: REQ-007 Exclusion List Management

## Prerequisites

### System Requirements
- Python 3.12+
- PostgreSQL 15+
- pip or poetry for dependency management

### Database Setup
Ensure the database schema from REQ-001 is applied:
```bash
cd runs/kit/REQ-001
./scripts/db_upgrade.sh
```

### Environment Variables
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey"
export LOG_LEVEL="INFO"
export PYTHONPATH="runs/kit/REQ-007/src:runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
```

## Local Development

### Install Dependencies
```bash
cd runs/kit/REQ-007
pip install -r requirements.txt
```

### Run Unit Tests
```bash
pytest test/test_exclusions_unit.py -v
```

### Run Integration Tests
```bash
# Start PostgreSQL (if using Docker)
docker run -d --name postgres-test \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey_test \
  -p 5432:5432 \
  postgres:15

# Run tests
pytest test/test_exclusions_integration.py -v
```

### Run All Tests with Coverage
```bash
pytest test/ \
  --cov=src/app/contacts/exclusions \
  --cov-report=term-missing \
  --cov-report=xml:reports/coverage.xml \
  --junitxml=reports/junit.xml
```

### Linting
```bash
ruff check src/app/contacts/exclusions
ruff format src/app/contacts/exclusions
```

### Type Checking
```bash
mypy src/app/contacts/exclusions --ignore-missing-imports
```

## CI/CD Integration

### GitHub Actions
The LTC.json file defines test cases that can be executed by the CI runner:

```yaml
- name: Run REQ-007 Tests
  run: |
    cd runs/kit/REQ-007
    pip install -r requirements.txt
    pytest test/ -v --tb=short
```

### Docker-based Testing
```bash
docker build -t voicesurvey-test -f Dockerfile.test .
docker run --rm \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/voicesurvey_test \
  voicesurvey-test \
  pytest runs/kit/REQ-007/test/ -v
```

## Troubleshooting

### Import Errors
If you see import errors, ensure PYTHONPATH includes all dependent REQ directories:
```bash
export PYTHONPATH="runs/kit/REQ-007/src:runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
```

### Database Connection Issues
1. Verify PostgreSQL is running
2. Check DATABASE_URL format
3. Ensure database exists and schema is applied

### Test Failures
1. Check database is clean (drop and recreate test database)
2. Verify all migrations are applied
3. Check for conflicting data from previous test runs

## API Testing with curl

### Get Auth Token (mock for testing)
```bash
export TOKEN="your-jwt-token"
```

### Test Import Endpoint
```bash
echo 'phone_number,reason
+14155551234,Test
+14155555678,Test2' > /tmp/test.csv

curl -X POST "http://localhost:8000/api/exclusions/import" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test.csv"
```

### Test Create Endpoint
```bash
curl -X POST "http://localhost:8000/api/exclusions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+14155559999", "reason": "Manual add"}'
```

### Test List Endpoint
```bash
curl "http://localhost:8000/api/exclusions" \
  -H "Authorization: Bearer $TOKEN"
```
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
**REQ-007: Exclusion list management**

### Rationale
REQ-007 is the next open REQ in the dependency chain. It depends on REQ-006 (Contact CSV upload and parsing) which is marked as in_progress. The exclusion list management feature builds on the contact management infrastructure to provide do-not-call list functionality.

### In Scope
- ExclusionListEntry SQLAlchemy model
- ExclusionRepository with CRUD and bulk operations
- ExclusionService with CSV import and contact sync
- REST API endpoints for exclusion management
- RBAC enforcement (admin-only deletion)
- Phone number normalization to E.164 format
- Unit and integration tests
- LTC.json and HOWTO.md

### Out of Scope
- Scheduler integration (REQ-008 will use exclusion checks)
- Automatic periodic sync (can be triggered via API)
- UI components (frontend REQs)

### How to Run Tests

```bash
# Set up environment
export PYTHONPATH="runs/kit/REQ-007/src:runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test"

# Install dependencies
cd runs/kit/REQ-007
pip install -r requirements.txt

# Run unit tests (no database required)
pytest test/test_exclusions_unit.py -v

# Run integration tests (requires PostgreSQL)
pytest test/test_exclusions_integration.py -v

# Run all tests with coverage
pytest test/ --cov=src/app/contacts/exclusions --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ with test database
- Database schema from REQ-001 applied
- Shared modules from REQ-002 (auth), REQ-003 (RBAC), REQ-006 (contacts)

### Dependencies and Mocks
- **Database**: Integration tests use real PostgreSQL via asyncpg
- **Auth/RBAC**: Tests mock `get_current_user` dependency to provide test user
- **Session**: Tests use real SQLAlchemy async sessions

### Product Owner Notes
- CSV import supports both `phone_number` and `phone` column names for flexibility
- Phone numbers are normalized to E.164 format before storage
- Duplicate handling: duplicates within file are rejected, duplicates in DB are silently ignored
- The `sync-contacts` endpoint allows manual triggering of exclusion checks

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql`: Used for exclusion_list_entries table schema
- `runs/kit/REQ-003/src/app/auth/rbac.py`: Used for RBAC patterns (RBACChecker, require_admin)
- `runs/kit/REQ-006/src/app/contacts/models.py`: Used for Contact model and ContactState enum
- `runs/kit/REQ-006/src/app/contacts/repository.py`: Used as pattern for repository implementation
- `docs/harper/lane-guides/python.md`: Used for testing tools and patterns

```json
{
  "index": [
    {
      "req": "REQ-007",
      "src": [
        "runs/kit/REQ-007/src/app/contacts/exclusions/__init__.py",
        "runs/kit/REQ-007/src/app/contacts/exclusions/models.py",
        "runs/kit/REQ-007/src/app/contacts/exclusions/repository.py",
        "runs/kit/REQ-007/src/app/contacts/exclusions/schemas.py",
        "runs/kit/REQ-007/src/app/contacts/exclusions/service.py",
        "runs/kit/REQ-007/src/app/contacts/exclusions/router.py"
      ],
      "tests": [
        "runs/kit/REQ-007/test/test_exclusions_unit.py",
        "runs/kit/REQ-007/test/test_exclusions_integration.py",
        "runs/kit/REQ-007/test/conftest.py"
      ],
      "docs": [
        "runs/kit/REQ-007/docs/KIT_REQ-007.md",
        "runs/kit/REQ-007/docs/README_REQ-007.md"
      ],
      "ci": [
        "runs/kit/REQ-007/ci/LTC.json",
        "runs/kit/REQ-007/ci/HOWTO.md"
      ]
    }
  ]
}