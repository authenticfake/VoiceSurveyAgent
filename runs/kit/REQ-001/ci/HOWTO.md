# REQ-001: Database Schema and Migrations - Execution Guide

## Prerequisites

- Docker installed and running (for PostgreSQL container)
- Python 3.12+ installed
- `psql` CLI available (for running SQL scripts)
- pip for installing Python dependencies

## Environment Setup

### Environment Variables

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
```

### Install Dependencies

```bash
pip install -r runs/kit/REQ-001/requirements.txt
```

## Running Locally

### 1. Start PostgreSQL Container

```bash
docker run -d \
  --name voicesurvey-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey_test \
  -p 5432:5432 \
  postgres:15-alpine
```

Wait for PostgreSQL to be ready:
```bash
sleep 5
# Or check with:
docker logs voicesurvey-postgres
```

### 2. Run Migrations

```bash
# Make scripts executable
chmod +x runs/kit/REQ-001/scripts/*.sh

# Run upgrade (apply schema)
./runs/kit/REQ-001/scripts/db_upgrade.sh

# Run seed data
./runs/kit/REQ-001/scripts/db_seed.sh
```

### 3. Run Tests

```bash
pytest runs/kit/REQ-001/test/ -v --tb=short
```

### 4. Cleanup

```bash
# Run downgrade (remove schema)
./runs/kit/REQ-001/scripts/db_downgrade.sh

# Stop and remove container
docker stop voicesurvey-postgres
docker rm voicesurvey-postgres
```

## Running via LTC

The LTC.json file defines the complete test sequence:

```bash
# Using a CI runner that understands LTC format
# Each case runs in sequence with the specified cwd and environment
```

## Troubleshooting

### Connection Refused

If you get "connection refused" errors:
1. Ensure Docker is running
2. Wait longer for PostgreSQL to start (increase sleep time)
3. Check if port 5432 is already in use: `lsof -i :5432`

### Permission Denied on Scripts

```bash
chmod +x runs/kit/REQ-001/scripts/*.sh
```

### psql Not Found

Install PostgreSQL client:
- macOS: `brew install postgresql`
- Ubuntu: `apt-get install postgresql-client`
- Or use Docker: `docker exec -it voicesurvey-postgres psql -U postgres -d voicesurvey_test`

### Tests Skip with "DATABASE_URL not set"

Ensure the environment variable is exported:
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
```

## Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Up Migration | `src/storage/sql/V0001.up.sql` | Creates all tables, indexes, triggers |
| Down Migration | `src/storage/sql/V0001.down.sql` | Drops all objects in reverse order |
| Seed Data | `src/storage/seed/seed.sql` | Idempotent seed with 10-20 records |
| Tests | `test/test_migration_sql.py` | Shape, idempotency, round-trip tests |

## Enterprise Runner (Jenkins)

```groovy
pipeline {
    agent { label 'docker' }
    
    environment {
        DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/voicesurvey_test'
    }
    
    stages {
        stage('Start DB') {
            steps {
                sh 'docker run -d --name voicesurvey-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=voicesurvey_test -p 5432:5432 postgres:15-alpine'
                sh 'sleep 10'
            }
        }
        
        stage('Install') {
            steps {
                sh 'pip install -r runs/kit/REQ-001/requirements.txt'
            }
        }
        
        stage('Migrate') {
            steps {
                sh 'chmod +x runs/kit/REQ-001/scripts/*.sh'
                sh './runs/kit/REQ-001/scripts/db_upgrade.sh'
                sh './runs/kit/REQ-001/scripts/db_seed.sh'
            }
        }
        
        stage('Test') {
            steps {
                sh 'pytest runs/kit/REQ-001/test/ -v --junitxml=reports/junit.xml'
            }
            post {
                always {
                    junit 'reports/junit.xml'
                }
            }
        }
    }
    
    post {
        always {
            sh 'docker stop voicesurvey-postgres || true'
            sh 'docker rm voicesurvey-postgres || true'
        }
    }
}