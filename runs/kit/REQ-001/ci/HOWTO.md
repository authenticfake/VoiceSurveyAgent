# REQ-001: Database Schema and Migrations - Execution Guide

## Prerequisites

### Required Tools
- PostgreSQL 15+ client (`psql`)
- Python 3.12+
- pip or poetry for dependency management

### Optional Tools
- Docker (for testcontainers)
- pgAdmin or DBeaver for visual inspection

## Environment Setup

### Option 1: Local PostgreSQL

```bash
# Create test database
createdb voicesurvey_test

# Set environment variable
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
export DISABLE_TESTCONTAINERS=1
```

### Option 2: Docker PostgreSQL

```bash
# Start PostgreSQL container
docker run -d \
  --name voicesurvey-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey_test \
  -p 5432:5432 \
  postgres:15-alpine

# Set environment variable
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
export DISABLE_TESTCONTAINERS=1
```

### Option 3: Testcontainers (automatic)

```bash
# Just ensure Docker is running
# Tests will automatically create/destroy containers
unset DISABLE_TESTCONTAINERS
```

## Running Migrations

### Upgrade (apply schema)

```bash
# Make scripts executable
chmod +x runs/kit/REQ-001/scripts/*.sh

# Run upgrade
./runs/kit/REQ-001/scripts/db_upgrade.sh
```

### Downgrade (revert schema)

```bash
./runs/kit/REQ-001/scripts/db_downgrade.sh
```

### Apply Seed Data

```bash
./runs/kit/REQ-001/scripts/db_seed.sh
```

## Running Tests

### Install Dependencies

```bash
pip install -r runs/kit/REQ-001/requirements.txt
```

### Run All Tests

```bash
# With testcontainers (Docker required)
pytest runs/kit/REQ-001/test/test_migration_sql.py -v

# With local PostgreSQL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
export DISABLE_TESTCONTAINERS=1
pytest runs/kit/REQ-001/test/test_migration_sql.py -v
```

### Run Specific Test Classes

```bash
# Schema shape tests only
pytest runs/kit/REQ-001/test/test_migration_sql.py::TestSchemaShape -v

# Idempotency tests only
pytest runs/kit/REQ-001/test/test_migration_sql.py::TestIdempotency -v

# Round-trip tests only
pytest runs/kit/REQ-001/test/test_migration_sql.py::TestRoundTrip -v

# Seed data tests only
pytest runs/kit/REQ-001/test/test_migration_sql.py::TestSeedData -v
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run REQ-001 Tests
  env:
    DATABASE_URL: postgresql://postgres:postgres@localhost:5432/voicesurvey_test
    DISABLE_TESTCONTAINERS: "1"
  run: |
    pip install -r runs/kit/REQ-001/requirements.txt
    pytest runs/kit/REQ-001/test/test_migration_sql.py -v --junitxml=reports/junit-req001.xml
```

### Jenkins

```groovy
stage('REQ-001 Migration Tests') {
    environment {
        DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/voicesurvey_test'
        DISABLE_TESTCONTAINERS = '1'
    }
    steps {
        sh 'pip install -r runs/kit/REQ-001/requirements.txt'
        sh 'pytest runs/kit/REQ-001/test/test_migration_sql.py -v --junitxml=reports/junit-req001.xml'
    }
}
```

## Troubleshooting

### Common Issues

1. **psql: command not found**
   - Install PostgreSQL client: `brew install postgresql` (macOS) or `apt install postgresql-client` (Ubuntu)

2. **Connection refused**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL format and credentials
   - Verify port 5432 is accessible

3. **Permission denied on scripts**
   - Run: `chmod +x runs/kit/REQ-001/scripts/*.sh`

4. **Testcontainers not starting**
   - Ensure Docker daemon is running
   - Check Docker permissions: `docker ps`

5. **Tests skipped**
   - If using local PostgreSQL, set `DISABLE_TESTCONTAINERS=1`
   - Ensure `DATABASE_URL` is set correctly

### Verifying Schema

```bash
# Connect to database
psql $DATABASE_URL

# List tables
\dt

# Describe a table
\d users

# List enum types
\dT+

# Exit
\q
```

## Artifacts

| Path | Description |
|------|-------------|
| `src/storage/sql/V0001.up.sql` | Schema creation DDL |
| `src/storage/sql/V0001.down.sql` | Schema rollback DDL |
| `src/storage/seed/seed.sql` | Idempotent seed data |
| `scripts/db_upgrade.sh` | Migration runner |
| `scripts/db_downgrade.sh` | Rollback runner |
| `scripts/db_seed.sh` | Seed data runner |
| `test/test_migration_sql.py` | Schema validation tests |