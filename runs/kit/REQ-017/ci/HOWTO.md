# HOWTO: REQ-017 Campaign Dashboard Stats API

## Prerequisites

### Required Software

- Python 3.12+
- PostgreSQL 14+ (or Docker for containerized testing)
- Redis 7+ (or Docker for containerized testing)
- pip (Python package manager)

### Optional Tools

- Docker & Docker Compose (for containerized dependencies)
- ruff (Python linter)
- mypy (Python type checker)
- bandit (Python security scanner)

## Environment Setup

### 1. Python Virtual Environment

```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r runs/kit/REQ-017/requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root or export variables:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="your-secret-key-here"
export LOG_LEVEL="INFO"
export PYTHONPATH="runs/kit/REQ-017/src"
```

### 3. Database Setup

#### Option A: Local PostgreSQL

```bash
# Create database
createdb voicesurvey

# Run migrations (from REQ-001)
psql -d voicesurvey -f runs/kit/REQ-001/src/storage/sql/V0001.up.sql

# Optionally seed data
psql -d voicesurvey -f runs/kit/REQ-001/src/storage/seed/seed.sql
```

#### Option B: Docker PostgreSQL

```bash
docker run -d \
  --name voicesurvey-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey \
  -p 5432:5432 \
  postgres:14
```

### 4. Redis Setup

#### Option A: Local Redis

```bash
# Start Redis server
redis-server
```

#### Option B: Docker Redis

```bash
docker run -d \
  --name voicesurvey-redis \
  -p 6379:6379 \
  redis:7
```

## Running Tests

### All Tests

```bash
# Set PYTHONPATH
export PYTHONPATH="runs/kit/REQ-017/src"

# Run all tests
pytest -v runs/kit/REQ-017/test/
```

### With Coverage

```bash
pytest --cov=app --cov-report=html --cov-report=term runs/kit/REQ-017/test/
```

### Specific Test Files

```bash
# Unit tests only
pytest -v runs/kit/REQ-017/test/test_dashboard_service.py
pytest -v runs/kit/REQ-017/test/test_dashboard_repository.py
pytest -v runs/kit/REQ-017/test/test_schemas.py

# Integration tests
pytest -v runs/kit/REQ-017/test/test_dashboard_api.py
```

### Test with SQLite (No PostgreSQL Required)

The tests use SQLite in-memory database by default, so PostgreSQL is not required for running tests.

## Running the Application

### Development Server

```bash
export PYTHONPATH="runs/kit/REQ-017/src"
cd runs/kit/REQ-017/src
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Testing

### Health Check

```bash
curl http://localhost:8000/health
```

### Get Campaign Stats (requires valid JWT)

```bash
# Generate a test token (for development only)
python -c "
from jose import jwt
token = jwt.encode({
    'sub': '11111111-1111-1111-1111-111111111111',
    'email': 'test@example.com',
    'name': 'Test User',
    'role': 'campaign_manager',
    'oidc_sub': 'oidc|test001'
}, 'your-secret-key-here', algorithm='HS256')
print(token)
"

# Use the token
curl -X GET "http://localhost:8000/api/campaigns/{campaign_id}/stats" \
  -H "Authorization: Bearer {token}"
```

## Code Quality Checks

### Linting

```bash
# Install ruff
pip install ruff

# Run linter
ruff check runs/kit/REQ-017/src/
```

### Type Checking

```bash
# Install mypy
pip install mypy

# Run type checker
mypy runs/kit/REQ-017/src/ --ignore-missing-imports
```

### Security Scanning

```bash
# Install bandit
pip install bandit

# Run security scan
bandit -r runs/kit/REQ-017/src/ -ll
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure PYTHONPATH is set correctly:

```bash
export PYTHONPATH="runs/kit/REQ-017/src:$PYTHONPATH"
```

### Database Connection Issues

1. Verify PostgreSQL is running: `pg_isready`
2. Check connection URL format: `postgresql://user:pass@host:port/dbname`
3. Ensure database exists: `psql -l | grep voicesurvey`

### Redis Connection Issues

1. Verify Redis is running: `redis-cli ping`
2. Check connection URL format: `redis://host:port/db`

### Test Failures

1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Check PYTHONPATH is set correctly
3. Run tests with verbose output: `pytest -vvs`

## CI/CD Integration

### GitHub Actions

The LTC.json file defines the test cases for CI:

```yaml
- name: Run REQ-017 Tests
  run: |
    pip install -r runs/kit/REQ-017/requirements.txt
    export PYTHONPATH="runs/kit/REQ-017/src"
    pytest -v runs/kit/REQ-017/test/
```

### Jenkins

```groovy
stage('REQ-017 Tests') {
    steps {
        sh 'pip install -r runs/kit/REQ-017/requirements.txt'
        sh 'export PYTHONPATH="runs/kit/REQ-017/src" && pytest -v runs/kit/REQ-017/test/'
    }
}
```

## Artifacts and Reports

After running tests with coverage:

- **JUnit XML**: `reports/junit.xml`
- **Coverage XML**: `reports/coverage.xml`
- **Coverage HTML**: `htmlcov/index.html`

Generate reports:

```bash
pytest --junitxml=reports/junit.xml --cov=app --cov-report=xml:reports/coverage.xml runs/kit/REQ-017/test/
```
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-017**: Campaign dashboard stats API

### Rationale
REQ-017 is the next open REQ-ID that depends on REQ-014 (Survey response persistence), which is marked as in_progress. The dashboard stats API provides aggregate metrics for campaign monitoring, including contact state distributions, call outcome counts, completion rates, and time series data.

### In Scope
- GET /api/campaigns/{id}/stats endpoint returning aggregate metrics
- Contact state counts (total, pending, in_progress, completed, refused, not_reached, excluded)
- Call outcome counts (total_attempts, completed, refused, no_answer, busy, failed)
- Completion and conversion rates calculation
- Call duration statistics (average, min, max, total)
- Time series data for hourly (24h) and daily (30d) call activity
- Redis caching with 60-second TTL
- RBAC enforcement (admin, campaign_manager, viewer can access)
- Cache invalidation endpoint (admin only)

### Out of Scope
- CSV export functionality (REQ-018)
- Frontend dashboard UI (REQ-024)
- Real-time WebSocket updates
- Advanced analytics or BI features

### How to Run Tests

```bash
# Set up environment
export PYTHONPATH="runs/kit/REQ-017/src"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="test-secret-key"

# Install dependencies
pip install -r runs/kit/REQ-017/requirements.txt

# Run all tests
pytest -v runs/kit/REQ-017/test/

# Run with coverage
pytest --cov=app --cov-report=html runs/kit/REQ-017/test/
```

### Prerequisites
- Python 3.12+
- PostgreSQL 14+ (for production; tests use SQLite in-memory)
- Redis 7+ (for caching; tests use mock cache)
- Dependencies from requirements.txt

### Dependencies and Mocks
- **Database**: Tests use SQLite in-memory database via aiosqlite for isolation
- **Cache**: Tests use MockCacheClient that stores data in a Python dict
- **Authentication**: Tests generate valid JWT tokens using python-jose
- **No external services required for testing**

### Product Owner Notes
- Stats are cached with 60-second TTL to meet the <500ms response time requirement for campaigns with 10k contacts
- Time series data uses PostgreSQL's `date_trunc` function for efficient bucketing
- Cache invalidation is restricted to admin role to prevent abuse
- All rates are calculated as percentages (0-100) with 2 decimal precision

### RAG Citations
- Used `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` for database schema reference (Contact, Campaign, CallAttempt table structures)
- Used `runs/kit/REQ-015/src/app/shared/__init__.py` for shared module structure pattern
- Used `runs/kit/REQ-014/src/app/dialogue/__init__.py` for module organization pattern
- Aligned with existing enum types from REQ-001 schema (contact_state, contact_outcome, campaign_status)

```json
{
  "index": [
    {
      "req": "REQ-017",
      "src": [
        "runs/kit/REQ-017/src/app/__init__.py",
        "runs/kit/REQ-017/src/app/main.py",
        "runs/kit/REQ-017/src/app/shared/__init__.py",
        "runs/kit/REQ-017/src/app/shared/config.py",
        "runs/kit/REQ-017/src/app/shared/database.py",
        "runs/kit/REQ-017/src/app/shared/cache.py",
        "runs/kit/REQ-017/src/app/shared/auth.py",
        "runs/kit/REQ-017/src/app/dashboard/__init__.py",
        "runs/kit/REQ-017/src/app/dashboard/models.py",
        "runs/kit/REQ-017/src/app/dashboard/schemas.py",
        "runs/kit/REQ-017/src/app/dashboard/repository.py",
        "runs/kit/REQ-017/src/app/dashboard/service.py",
        "runs/kit/REQ-017/src/app/dashboard/router.py"
      ],
      "tests": [
        "runs/kit/REQ-017/test/__init__.py",
        "runs/kit/REQ-017/test/conftest.py",
        "runs/kit/REQ-017/test/test_dashboard_service.py",
        "runs/kit/REQ-017/test/test_dashboard_repository.py",
        "runs/kit/REQ-017/test/test_dashboard_api.py",
        "runs/kit/REQ-017/test/test_schemas.py"
      ],
      "docs": [
        "runs/kit/REQ-017/docs/KIT_REQ-017.md",
        "runs/kit/REQ-017/docs/README_REQ-017.md"
      ],
      "ci": [
        "runs/kit/REQ-017/ci/LTC.json",
        "runs/kit/REQ-017/ci/HOWTO.md"
      ]
    }
  ]
}