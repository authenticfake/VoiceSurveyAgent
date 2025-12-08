# HOWTO — REQ-001: Database Schema and Migrations

## Prerequisites

- PostgreSQL 15+ installed and running
- Python 3.12+ with pip
- `psql` CLI available in PATH
- Docker (optional, for testcontainers)

## Environment Setup

### Option 1: Local PostgreSQL

bash
# Set database URL
export DATABASE_URL='postgresql://user:password@localhost:5432/voicesurvey'

# Create database if needed
createdb voicesurvey

### Option 2: Docker PostgreSQL

bash
# Start PostgreSQL container
docker run -d \
  --name voicesurvey-db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=voicesurvey \
  -p 5432:5432 \
  postgres:15

export DATABASE_URL='postgresql://user:password@localhost:5432/voicesurvey'

## Install Dependencies

bash
pip install -r runs/kit/REQ-001/requirements.txt

## Running Migrations

### Apply Migrations (Upgrade)

bash
chmod +x runs/kit/REQ-001/scripts/db_upgrade.sh
./runs/kit/REQ-001/scripts/db_upgrade.sh

### Apply Seed Data

bash
chmod +x runs/kit/REQ-001/scripts/db_seed.sh
./runs/kit/REQ-001/scripts/db_seed.sh

### Rollback Migrations (Downgrade)

bash
chmod +x runs/kit/REQ-001/scripts/db_downgrade.sh
./runs/kit/REQ-001/scripts/db_downgrade.sh

## Running Tests

### With Testcontainers (Recommended)

bash
# Testcontainers will automatically start a PostgreSQL container
unset DATABASE_URL
pytest runs/kit/REQ-001/test/ -v

### With Local Database

bash
export DATABASE_URL='postgresql://user:password@localhost:5432/voicesurvey_test'
pytest runs/kit/REQ-001/test/ -v

## Troubleshooting

### psql: command not found

Install PostgreSQL client tools:
- macOS: `brew install postgresql`
- Ubuntu: `apt-get install postgresql-client`
- Windows: Install PostgreSQL and add to PATH

### Connection refused

Ensure PostgreSQL is running:
bash
pg_isready -h localhost -p 5432

### Permission denied on scripts

bash
chmod +x runs/kit/REQ-001/scripts/*.sh

### Testcontainers not working

Ensure Docker is running:
bash
docker info

Or use a local database instead:
bash
export DATABASE_URL='postgresql://user:password@localhost:5432/voicesurvey_test'
export DISABLE_TESTCONTAINERS=1

## CI/CD Integration

### GitHub Actions

yaml
- name: Run migrations
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
  run: |
    pip install -r runs/kit/REQ-001/requirements.txt
    ./runs/kit/REQ-001/scripts/db_upgrade.sh
    pytest runs/kit/REQ-001/test/ -v

### Jenkins

groovy
stage('Database') {
    steps {
        sh 'pip install -r runs/kit/REQ-001/requirements.txt'
        sh './runs/kit/REQ-001/scripts/db_upgrade.sh'
        sh 'pytest runs/kit/REQ-001/test/ -v'
    }
}

## Artifacts

- **SQL Migrations**: `runs/kit/REQ-001/src/storage/sql/`
- **Seed Data**: `runs/kit/REQ-001/src/storage/seed/`
- **Test Results**: `reports/junit.xml`