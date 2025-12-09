# REQ-001: Database Schema and Migrations - Execution Guide

## Overview

This KIT implements the database schema and migrations for the voicesurveyagent system. It creates all entities from the SPEC data model using versioned SQL files with idempotent operations.

## Prerequisites

### Required Tools
- **PostgreSQL 15+** - Database server
- **psql** - PostgreSQL command-line client
- **Docker** (optional) - For containerized testing
- **Python 3.12+** - For running tests
- **pip** - Python package manager

### Environment Variables
```bash
# Required for database connection
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurveyagent"

# Optional: Disable testcontainers (use local DB instead)
export DISABLE_TESTCONTAINERS=1
```

## Local Development Setup

### 1. Start PostgreSQL

**Option A: Using Docker (Recommended)**
```bash
docker run -d \
  --name voicesurvey-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurveyagent \
  -p 5432:5432 \
  postgres:15-alpine
```

**Option B: Local PostgreSQL**
```bash
# Create database
createdb voicesurveyagent

# Or via psql
psql -U postgres -c "CREATE DATABASE voicesurveyagent;"
```

### 2. Install Test Dependencies
```bash
cd runs/kit/REQ-001
pip install -r requirements.txt
```

### 3. Run Migrations

**Apply Schema (Upgrade)**
```bash
# Using script
chmod +x scripts/db_upgrade.sh
./scripts/db_upgrade.sh

# Or directly with psql
psql $DATABASE_URL -f src/storage/sql/V0001.up.sql
```

**Apply Seed Data**
```bash
# Using script
chmod +x scripts/db_seed.sh
./scripts/db_seed.sh

# Or directly with psql
psql $DATABASE_URL -f src/storage/seed/seed.sql
```

**Rollback Schema (Downgrade)**
```bash
# Using script
chmod +x scripts/db_downgrade.sh
./scripts/db_downgrade.sh

# Or directly with psql
psql $DATABASE_URL -f src/storage/sql/V0001.down.sql
```

### 4. Run Tests
```bash
cd runs/kit/REQ-001

# With testcontainers (auto-creates isolated DB)
pytest test/test_migration_sql.py -v

# With local database
DISABLE_TESTCONTAINERS=1 \
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/voicesurveyagent_test \
pytest test/test_migration_sql.py -v
```

## CI/CD Integration

### GitHub Actions
```yaml
name: REQ-001 Migration Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: voicesurveyagent_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -r runs/kit/REQ-001/requirements.txt
      
      - name: Run migrations
        run: |
          PGPASSWORD=postgres psql -h localhost -U postgres -d voicesurveyagent_test \
            -f runs/kit/REQ-001/src/storage/sql/V0001.up.sql
      
      - name: Run seed
        run: |
          PGPASSWORD=postgres psql -h localhost -U postgres -d voicesurveyagent_test \
            -f runs/kit/REQ-001/src/storage/seed/seed.sql
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/voicesurveyagent_test
          DISABLE_TESTCONTAINERS: "1"
        run: |
          cd runs/kit/REQ-001
          pytest test/test_migration_sql.py -v --junitxml=reports/junit.xml
```

### Jenkins Pipeline
```groovy
pipeline {
    agent { label 'docker' }
    
    environment {
        DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/voicesurveyagent_test'
        DISABLE_TESTCONTAINERS = '1'
    }
    
    stages {
        stage('Start Database') {
            steps {
                sh '''
                    docker run -d --name pg_test \
                        -e POSTGRES_PASSWORD=postgres \
                        -e POSTGRES_DB=voicesurveyagent_test \
                        -p 5432:5432 \
                        postgres:15-alpine
                    sleep 10
                '''
            }
        }
        
        stage('Install Dependencies') {
            steps {
                sh 'pip install -r runs/kit/REQ-001/requirements.txt'
            }
        }
        
        stage('Run Migrations') {
            steps {
                sh '''
                    PGPASSWORD=postgres psql -h localhost -U postgres \
                        -d voicesurveyagent_test \
                        -f runs/kit/REQ-001/src/storage/sql/V0001.up.sql
                '''
            }
        }
        
        stage('Run Tests') {
            steps {
                dir('runs/kit/REQ-001') {
                    sh 'pytest test/test_migration_sql.py -v --junitxml=reports/junit.xml'
                }
            }
            post {
                always {
                    junit 'runs/kit/REQ-001/reports/junit.xml'
                }
            }
        }
    }
    
    post {
        always {
            sh 'docker stop pg_test && docker rm pg_test || true'
        }
    }
}
```

## Troubleshooting

### Common Issues

**1. psql: command not found**
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql-client

# Or use Docker
docker run --rm -it postgres:15-alpine psql --help
```

**2. Connection refused**
- Ensure PostgreSQL is running
- Check port 5432 is not blocked
- Verify DATABASE_URL is correct

**3. Permission denied**
```bash
# Make scripts executable
chmod +x runs/kit/REQ-001/scripts/*.sh
```

**4. Import errors in tests**
```bash
# Ensure psycopg is installed
pip install "psycopg[binary]>=3.1.0"
```

**5. Testcontainers not working**
```bash
# Disable testcontainers and use local DB
export DISABLE_TESTCONTAINERS=1
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/voicesurveyagent_test
```

## Schema Overview

### Tables Created
| Table | Description |
|-------|-------------|
| users | System users with OIDC integration |
| email_templates | Email templates for notifications |
| campaigns | Survey campaign configurations |
| contacts | Contact records per campaign |
| exclusion_list_entries | Do-not-call list |
| call_attempts | Individual call attempt records |
| survey_responses | Captured survey answers |
| events | Domain events for async processing |
| email_notifications | Email delivery tracking |
| provider_configs | Telephony/LLM provider settings |
| transcript_snippets | Call transcript storage |
| schema_migrations | Migration version tracking |

### Enum Types
- user_role, campaign_status, campaign_language
- question_type, contact_state, contact_language
- contact_outcome, exclusion_source, call_outcome
- event_type, email_status, email_template_type
- provider_type, llm_provider, transcript_language

## Verification Commands

```bash
# Check tables exist
psql $DATABASE_URL -c "\dt"

# Check enum types
psql $DATABASE_URL -c "SELECT typname FROM pg_type WHERE typtype = 'e';"

# Check indexes
psql $DATABASE_URL -c "SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public';"

# Check seed data counts
psql $DATABASE_URL -c "SELECT 'users' as tbl, COUNT(*) FROM users UNION ALL SELECT 'campaigns', COUNT(*) FROM campaigns UNION ALL SELECT 'contacts', COUNT(*) FROM contacts;"