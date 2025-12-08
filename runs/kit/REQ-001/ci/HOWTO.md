# REQ-001: Database Schema and Migrations - Execution Guide

## Overview

This KIT implements the foundational database schema for the voicesurveyagent system, including all entities from the SPEC data model with proper Alembic-compatible migrations.

## Prerequisites

### Required Tools
- PostgreSQL 15+ (local or Docker)
- Python 3.12+
- psql CLI (PostgreSQL client)
- Docker (optional, for testcontainers)

### Environment Variables
```bash
# Required for database operations
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey"

# Optional: Disable testcontainers if Docker unavailable
export DISABLE_TESTCONTAINERS=1
```

## Installation

### 1. Install Python Dependencies
```bash
cd /path/to/project
pip install -r runs/kit/REQ-001/requirements.txt
```

### 2. Database Setup

#### Option A: Using Docker (Recommended)
```bash
# Start PostgreSQL container
docker run -d \
  --name voicesurvey-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey \
  -p 5432:5432 \
  postgres:15-alpine

# Wait for database to be ready
sleep 5
```

#### Option B: Using Local PostgreSQL
```bash
# Create database
createdb voicesurvey

# Or via psql
psql -U postgres -c "CREATE DATABASE voicesurvey;"
```

## Running Migrations

### Apply Migrations (Upgrade)
```bash
# Using the provided script
chmod +x runs/kit/REQ-001/scripts/db_upgrade.sh
./runs/kit/REQ-001/scripts/db_upgrade.sh

# Or manually with psql
psql $DATABASE_URL -f runs/kit/REQ-001/src/storage/sql/V0001.up.sql
```

### Rollback Migrations (Downgrade)
```bash
# Using the provided script
chmod +x runs/kit/REQ-001/scripts/db_downgrade.sh
./runs/kit/REQ-001/scripts/db_downgrade.sh

# Or manually with psql
psql $DATABASE_URL -f runs/kit/REQ-001/src/storage/sql/V0001.down.sql
```

### Apply Seed Data
```bash
# Using the provided script
chmod +x runs/kit/REQ-001/scripts/db_seed.sh
./runs/kit/REQ-001/scripts/db_seed.sh

# Or manually with psql
psql $DATABASE_URL -f runs/kit/REQ-001/src/storage/seed/seed.sql
```

## Running Tests

### With Testcontainers (Docker Required)
```bash
# Tests will automatically spin up a PostgreSQL container
pytest -v runs/kit/REQ-001/test/test_migration_sql.py
```

### With External Database
```bash
# Set DATABASE_URL to your test database
export DATABASE_URL="postgresql://user:pass@host:5432/testdb"
export DISABLE_TESTCONTAINERS=1

pytest -v runs/kit/REQ-001/test/test_migration_sql.py
```

### Generate JUnit Report
```bash
pytest -v runs/kit/REQ-001/test/ \
  --junitxml=reports/junit.xml \
  --tb=short
```

## Verification Commands

### Check Tables Created
```bash
psql $DATABASE_URL -c "\dt"
```

### Check Enum Types
```bash
psql $DATABASE_URL -c "SELECT typname FROM pg_type WHERE typtype = 'e';"
```

### Check Indexes
```bash
psql $DATABASE_URL -c "\di"
```

### Verify Seed Data
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM campaigns;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM contacts;"
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```
psycopg2.OperationalError: could not connect to server
```
**Solution**: Ensure PostgreSQL is running and DATABASE_URL is correct.

#### 2. Database Does Not Exist
```
FATAL: database "voicesurvey" does not exist
```
**Solution**: Create the database first:
```bash
createdb voicesurvey
```

#### 3. Permission Denied
```
ERROR: permission denied for schema public
```
**Solution**: Grant permissions:
```bash
psql -U postgres -c "GRANT ALL ON SCHEMA public TO your_user;"
```

#### 4. Testcontainers Not Working
```
docker.errors.DockerException: Error while fetching server API version
```
**Solution**: Ensure Docker daemon is running, or set `DISABLE_TESTCONTAINERS=1` and use external database.

### Import Path Issues

If running tests from project root:
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest -v runs/kit/REQ-001/test/
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run REQ-001 Tests
  env:
    DATABASE_URL: postgresql://postgres:postgres@localhost:5432/voicesurvey
  run: |
    pip install -r runs/kit/REQ-001/requirements.txt
    pytest -v runs/kit/REQ-001/test/ --junitxml=reports/junit.xml
```

### Jenkins Pipeline
```groovy
stage('REQ-001 Tests') {
    environment {
        DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/voicesurvey'
    }
    steps {
        sh 'pip install -r runs/kit/REQ-001/requirements.txt'
        sh 'pytest -v runs/kit/REQ-001/test/ --junitxml=reports/junit.xml'
    }
}
```

## Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Up Migration | `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` | Creates all tables, enums, indexes |
| Down Migration | `runs/kit/REQ-001/src/storage/sql/V0001.down.sql` | Drops all objects |
| Seed Data | `runs/kit/REQ-001/src/storage/seed/seed.sql` | Idempotent seed data |
| Tests | `runs/kit/REQ-001/test/test_migration_sql.py` | Schema validation tests |
| JUnit Report | `reports/junit.xml` | Test results in JUnit format |