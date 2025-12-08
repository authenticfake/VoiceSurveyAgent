# REQ-001: Database Schema and Migrations — Execution Guide

## Prerequisites

### Required Tools
- Python 3.12+
- PostgreSQL 15+ (local or Docker)
- Docker (optional, for testcontainers)

### Environment Variables
bash
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=voicesurveyagent
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/voicesurveyagent

## Installation

### Option 1: Using pip
bash
cd /path/to/project
pip install -r runs/kit/REQ-001/requirements.txt

### Option 2: Using Poetry (if available)
bash
poetry install

## Running Tests

### With Testcontainers (Recommended)
Testcontainers will automatically spin up a PostgreSQL container:
bash
pytest -p no:cacheprovider -q runs/kit/REQ-001/test/test_migration_sql.py -v

### Without Testcontainers
If Docker is not available, set `DISABLE_TESTCONTAINERS=1` and provide a `DATABASE_URL`:
bash
export DISABLE_TESTCONTAINERS=1
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/voicesurveyagent
pytest -p no:cacheprovider -q runs/kit/REQ-001/test/test_migration_sql.py -v

### Running Specific Test Classes
bash
# Schema shape tests
pytest runs/kit/REQ-001/test/test_migration_sql.py::TestSchemaShape -v

# Idempotency tests
pytest runs/kit/REQ-001/test/test_migration_sql.py::TestIdempotency -v

# Round-trip tests
pytest runs/kit/REQ-001/test/test_migration_sql.py::TestRoundTrip -v

# Seed data tests
pytest runs/kit/REQ-001/test/test_migration_sql.py::TestSeedData -v

## Manual Database Operations

### Apply Migrations (Upgrade)
bash
chmod +x runs/kit/REQ-001/scripts/db_upgrade.sh
./runs/kit/REQ-001/scripts/db_upgrade.sh

### Revert Migrations (Downgrade)
bash
chmod +x runs/kit/REQ-001/scripts/db_downgrade.sh
./runs/kit/REQ-001/scripts/db_downgrade.sh

### Apply Seed Data
bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f runs/kit/REQ-001/src/storage/seed/seed.sql

## Using Alembic (Alternative)

### Setup
bash
cd runs/kit/REQ-001/src/data/migrations
export DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5432 DB_NAME=voicesurveyagent

### Run Migrations
bash
alembic upgrade head

### Downgrade
bash
alembic downgrade -1  # One step back
alembic downgrade base  # All the way back

## Troubleshooting

### Import Errors
If you encounter import errors, ensure PYTHONPATH includes the project root:
bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

### Database Connection Issues
1. Verify PostgreSQL is running:
   bash
   pg_isready -h localhost -p 5432
   
2. Check credentials match environment variables
3. Ensure database exists:
   bash
   createdb -h localhost -U postgres voicesurveyagent
   

### Testcontainers Issues
- Ensure Docker daemon is running
- Check Docker permissions for current user
- Try with `DISABLE_TESTCONTAINERS=1` as fallback

## CI/CD Integration

### GitHub Actions
yaml
- name: Run REQ-001 Tests
  env:
    DISABLE_TESTCONTAINERS: "0"
  run: |
    pip install -r runs/kit/REQ-001/requirements.txt
    pytest -p no:cacheprovider -q runs/kit/REQ-001/test/test_migration_sql.py -v

### Jenkins
groovy
stage('REQ-001 Tests') {
    steps {
        sh 'pip install -r runs/kit/REQ-001/requirements.txt'
        sh 'pytest -p no:cacheprovider -q runs/kit/REQ-001/test/test_migration_sql.py -v --junitxml=reports/junit-req001.xml'
    }
}

## Artifacts

| Artifact | Path |
|----------|------|
| Up Migration | `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` |
| Down Migration | `runs/kit/REQ-001/src/storage/sql/V0001.down.sql` |
| Seed Data | `runs/kit/REQ-001/src/storage/seed/seed.sql` |
| Alembic Migrations | `runs/kit/REQ-001/src/data/migrations/migrations/versions/` |
| SQLAlchemy Models | `runs/kit/REQ-001/src/app/shared/models/` |
| Tests | `runs/kit/REQ-001/test/test_migration_sql.py` |