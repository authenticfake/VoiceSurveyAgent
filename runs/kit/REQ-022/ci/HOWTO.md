# HOWTO: REQ-022 Data Retention Jobs

## Prerequisites

### Required Tools
- Python 3.12+
- PostgreSQL 14+ (for database tests)
- AWS CLI (for S3 operations)
- Docker (optional, for containerized testing)

### Environment Variables

```bash
# Required
export DATABASE_URL=postgresql://user:password@localhost:5432/voicesurvey
export PYTHONPATH=runs/kit/REQ-022/src:runs/kit/REQ-019/src:runs/kit/REQ-001/src

# Optional (for S3 storage)
export S3_BUCKET_NAME=voicesurvey-recordings
export AWS_REGION=eu-central-1
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
```

## Local Development

### 1. Install Dependencies

```bash
cd runs/kit/REQ-022
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Apply migrations (requires prior migrations from REQ-001, REQ-019)
./scripts/db_upgrade.sh

# Seed test data
psql $DATABASE_URL -f src/storage/seed/seed.sql
```

### 3. Run Tests

```bash
# Unit tests only (no database required)
pytest test/ -v -k "not migration"

# All tests (requires database)
pytest test/ -v

# With coverage
pytest test/ -v --cov=src --cov-report=xml
```

### 4. Lint and Type Check

```bash
# Lint
ruff check src/

# Type check
mypy src/ --ignore-missing-imports
```

## Container Testing

### Using Docker Compose

```bash
# Start PostgreSQL
docker compose -f docker-compose.test.yml up -d postgres

# Wait for database
sleep 5

# Run tests
docker compose -f docker-compose.test.yml run --rm tests
```

### Using Testcontainers

Tests automatically use Testcontainers when available:

```python
# In conftest.py
@pytest.fixture(scope="session")
def database():
    with PostgresContainer("postgres:14") as postgres:
        yield postgres.get_connection_url()
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run REQ-022 Tests
  env:
    DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
    PYTHONPATH: runs/kit/REQ-022/src
  run: |
    pip install -r runs/kit/REQ-022/requirements.txt
    pytest runs/kit/REQ-022/test/ -v --tb=short
```

### Jenkins Pipeline

```groovy
stage('REQ-022 Tests') {
    environment {
        DATABASE_URL = credentials('test-db-url')
        PYTHONPATH = 'runs/kit/REQ-022/src'
    }
    steps {
        sh 'pip install -r runs/kit/REQ-022/requirements.txt'
        sh 'pytest runs/kit/REQ-022/test/ -v --junitxml=reports/junit.xml'
    }
    post {
        always {
            junit 'reports/junit.xml'
        }
    }
}
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'infra'`:

```bash
# Option 1: Set PYTHONPATH
export PYTHONPATH=runs/kit/REQ-022/src:$PYTHONPATH

# Option 2: Install as editable
pip install -e runs/kit/REQ-022/
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Migration Failures

```bash
# Check current schema
psql $DATABASE_URL -c "\dt"

# Rollback and retry
./scripts/db_downgrade.sh
./scripts/db_upgrade.sh
```

### S3 Access Issues

```bash
# Verify credentials
aws sts get-caller-identity

# Test bucket access
aws s3 ls s3://$S3_BUCKET_NAME/
```

## Artifacts

After running tests, find reports at:

- `reports/junit.xml` - JUnit test results
- `reports/coverage.xml` - Coverage report
- `reports/coverage-html/` - HTML coverage report

## Related REQs

- **REQ-019**: Admin configuration API (provides retention settings)
- **REQ-001**: Database schema (base tables)
- **REQ-021**: Observability (logging integration)
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-022**: Data retention jobs

### Rationale
REQ-022 depends on REQ-019 (Admin configuration API) which provides the `ProviderConfig` entity with `recording_retention_days` and `transcript_retention_days` settings. This REQ implements the scheduled retention job system and GDPR deletion request processing.

### In Scope
- Retention job scheduler running daily
- Recording deletion from S3/local storage
- Transcript deletion from database
- GDPR deletion request creation and processing
- 72-hour deadline enforcement for GDPR requests
- Audit logging for all deletion operations
- Admin API endpoints for manual triggering
- Database migrations for new tables (gdpr_deletion_requests, retention_job_history)
- Partial failure handling

### Out of Scope
- Frontend UI for retention management (deferred to future REQ)
- Complex retention policies per campaign (single global policy)
- Real-time deletion notifications

### How to Run Tests

```bash
# Set environment
export PYTHONPATH=runs/kit/REQ-022/src:runs/kit/REQ-019/src:runs/kit/REQ-001/src

# Install dependencies
pip install -r runs/kit/REQ-022/requirements.txt

# Run unit tests (no database required)
pytest runs/kit/REQ-022/test/ -v -k "not migration"

# Run all tests (requires DATABASE_URL)
DATABASE_URL=postgresql://user:pass@localhost:5432/voicesurvey pytest runs/kit/REQ-022/test/ -v
```

### Prerequisites
- Python 3.12+
- PostgreSQL 14+ (for database tests)
- Prior migrations from REQ-001 and REQ-019 applied
- AWS credentials (for S3 storage backend)

### Dependencies and Mocks
- **MockStorageBackend**: Used in tests to simulate S3 operations without actual AWS calls
- **MockRetentionRepository**: Used in tests to simulate database operations
- **InMemoryAuditLogger**: Used in tests to capture audit logs without database
- **MockRetentionService/MockGDPRService**: Used in API tests

### Product Owner Notes
- Retention job runs at 2 AM UTC by default (configurable)
- GDPR requests have a 72-hour processing deadline per GDPR requirements
- Partial failures are tracked and reported but don't stop the job
- All deletions are logged to audit_logs table for compliance

### RAG Citations
- `runs/kit/REQ-019/src/storage/sql/V0003.up.sql` - Referenced for audit_logs table structure
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Referenced for base schema patterns
- `runs/kit/REQ-019/src/storage/seed/seed.sql` - Referenced for seed data patterns

```json
{
  "index": [
    {
      "req": "REQ-022",
      "src": [
        "runs/kit/REQ-022/src/app/__init__.py",
        "runs/kit/REQ-022/src/app/shared/__init__.py",
        "runs/kit/REQ-022/src/infra/__init__.py",
        "runs/kit/REQ-022/src/infra/retention/__init__.py",
        "runs/kit/REQ-022/src/infra/retention/models.py",
        "runs/kit/REQ-022/src/infra/retention/interfaces.py",
        "runs/kit/REQ-022/src/infra/retention/service.py",
        "runs/kit/REQ-022/src/infra/retention/gdpr.py",
        "runs/kit/REQ-022/src/infra/retention/scheduler.py",
        "runs/kit/REQ-022/src/infra/retention/repository.py",
        "runs/kit/REQ-022/src/infra/retention/storage.py",
        "runs/kit/REQ-022/src/infra/retention/audit.py",
        "runs/kit/REQ-022/src/infra/retention/api.py",
        "runs/kit/REQ-022/src/storage/sql/V0004.up.sql",
        "runs/kit/REQ-022/src/storage/sql/V0004.down.sql",
        "runs/kit/REQ-022/src/storage/seed/seed.sql"
      ],
      "tests": [
        "runs/kit/REQ-022/test/__init__.py",
        "runs/kit/REQ-022/test/test_retention_models.py",
        "runs/kit/REQ-022/test/test_retention_service.py",
        "runs/kit/REQ-022/test/test_gdpr_service.py",
        "runs/kit/REQ-022/test/test_retention_scheduler.py",
        "runs/kit/REQ-022/test/test_retention_api.py",
        "runs/kit/REQ-022/test/test_migration_sql.py",
        "runs/kit/REQ-022/test/test_storage_backends.py"
      ]
    }
  ]
}