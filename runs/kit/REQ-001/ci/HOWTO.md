# REQ-001: Database Schema and Migrations - Execution Guide

## Prerequisites

### Required Tools
- PostgreSQL 15+ (local or Docker)
- Python 3.12+
- psql CLI tool
- Docker (optional, for testcontainers)

### Environment Setup

bash
# Set database connection URL
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/voicesurvey'

# For testing with testcontainers (recommended)
export DISABLE_TESTCONTAINERS=0

# For testing with local database
export DISABLE_TESTCONTAINERS=1

## Running Migrations

### Upgrade (Apply Schema)
bash
# Make script executable
chmod +x runs/kit/REQ-001/scripts/db_upgrade.sh

# Run upgrade
./runs/kit/REQ-001/scripts/db_upgrade.sh

### Downgrade (Revert Schema)
bash
# Make script executable
chmod +x runs/kit/REQ-001/scripts/db_downgrade.sh

# Run downgrade
./runs/kit/REQ-001/scripts/db_downgrade.sh

### Apply Seed Data
bash
# Make script executable
chmod +x runs/kit/REQ-001/scripts/db_seed.sh

# Run seed
./runs/kit/REQ-001/scripts/db_seed.sh

## Running Tests

### With Testcontainers (Recommended)
bash
# Install dependencies
pip install -r runs/kit/REQ-001/requirements.txt

# Run tests (testcontainers will spin up PostgreSQL automatically)
pytest runs/kit/REQ-001/test/ -v

### With Local PostgreSQL
bash
# Create test database
createdb voicesurvey_test

# Set environment
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/voicesurvey_test'
export DISABLE_TESTCONTAINERS=1

# Run tests
pytest runs/kit/REQ-001/test/ -v

### With Docker PostgreSQL
bash
# Start PostgreSQL container
docker run -d \
  --name voicesurvey-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey_test \
  -p 5432:5432 \
  postgres:15-alpine

# Set environment
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/voicesurvey_test'
export DISABLE_TESTCONTAINERS=1

# Run tests
pytest runs/kit/REQ-001/test/ -v

# Cleanup
docker stop voicesurvey-postgres && docker rm voicesurvey-postgres

## CI/CD Integration

### GitHub Actions
yaml
- name: Run REQ-001 Tests
  env:
    DISABLE_TESTCONTAINERS: "0"
  run: |
    pip install -r runs/kit/REQ-001/requirements.txt
    pytest runs/kit/REQ-001/test/ -v --junitxml=reports/junit.xml

### Jenkins
groovy
stage('REQ-001 Tests') {
    steps {
        sh 'pip install -r runs/kit/REQ-001/requirements.txt'
        sh 'pytest runs/kit/REQ-001/test/ -v --junitxml=reports/junit.xml'
    }
}

## Troubleshooting

### Common Issues

1. **psql: command not found**
   - Install PostgreSQL client tools
   - macOS: `brew install postgresql`
   - Ubuntu: `apt-get install postgresql-client`

2. **Connection refused**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL is correct
   - Verify port 5432 is accessible

3. **Permission denied on scripts**
   - Run `chmod +x runs/kit/REQ-001/scripts/*.sh`

4. **Testcontainers not starting**
   - Ensure Docker daemon is running
   - Check Docker permissions
   - Set `DISABLE_TESTCONTAINERS=1` to use local DB instead

## Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Up Migration | `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` | Creates all tables and indexes |
| Down Migration | `runs/kit/REQ-001/src/storage/sql/V0001.down.sql` | Drops all tables and types |
| Seed Data | `runs/kit/REQ-001/src/storage/seed/seed.sql` | Initial test data |
| Tests | `runs/kit/REQ-001/test/test_migration_sql.py` | Migration validation tests |