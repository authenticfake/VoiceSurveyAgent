# REQ-018: Campaign CSV Export - Execution Guide

## Overview

This REQ implements the Campaign CSV Export functionality, allowing campaign managers and admins to export campaign results to CSV files stored in S3 with presigned download URLs.

## Prerequisites

### Required Software
- Python 3.12+
- PostgreSQL 14+ (for integration tests)
- pip (Python package manager)

### Optional
- Docker (for containerized PostgreSQL)
- AWS CLI (for S3 testing with real bucket)

## Environment Setup

### 1. Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r runs/kit/REQ-018/requirements.txt
```

### 2. Environment Variables

Create a `.env` file or export these variables:

```bash
# Database
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test"

# AWS S3 (optional - uses mock storage in tests)
export AWS_REGION="eu-central-1"
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export S3_BUCKET_NAME="voicesurvey-exports"

# Testing
export SKIP_DB_TESTS="0"  # Set to "1" to skip database tests
```

### 3. Database Setup

#### Option A: Docker PostgreSQL

```bash
docker run -d \
  --name voicesurvey-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey_test \
  -p 5432:5432 \
  postgres:14
```

#### Option B: Local PostgreSQL

```bash
createdb voicesurvey_test
```

### 4. Run Migrations

```bash
# Apply migrations
chmod +x runs/kit/REQ-018/scripts/db_upgrade.sh
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test" \
  ./runs/kit/REQ-018/scripts/db_upgrade.sh
```

## Running Tests

### All Tests

```bash
PYTHONPATH=runs/kit/REQ-018/src:$PYTHONPATH \
  pytest runs/kit/REQ-018/test -v
```

### Unit Tests Only (No Database)

```bash
PYTHONPATH=runs/kit/REQ-018/src:$PYTHONPATH \
  SKIP_DB_TESTS=1 \
  pytest runs/kit/REQ-018/test -v \
    --ignore=runs/kit/REQ-018/test/test_migration_sql.py \
    --ignore=runs/kit/REQ-018/test/test_router.py
```

### With Coverage

```bash
PYTHONPATH=runs/kit/REQ-018/src:$PYTHONPATH \
  pytest runs/kit/REQ-018/test -v \
    --cov=runs/kit/REQ-018/src \
    --cov-report=xml:reports/coverage.xml \
    --cov-report=html:reports/htmlcov \
    --junitxml=reports/junit.xml
```

## Linting and Type Checking

### Lint

```bash
pip install ruff
ruff check runs/kit/REQ-018/src runs/kit/REQ-018/test
```

### Type Check

```bash
pip install mypy
mypy runs/kit/REQ-018/src --ignore-missing-imports
```

## API Endpoints

### Initiate Export
```
GET /api/campaigns/{campaign_id}/export
Authorization: Bearer <token>
Response: 202 Accepted
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Export job created..."
}
```

### Get Export Job Status
```
GET /api/exports/{job_id}
Authorization: Bearer <token>
Response: 200 OK
{
  "id": "uuid",
  "campaign_id": "uuid",
  "status": "completed",
  "download_url": "https://...",
  "url_expires_at": "2024-...",
  "total_records": 100
}
```

### List Campaign Exports
```
GET /api/campaigns/{campaign_id}/exports?limit=10
Authorization: Bearer <token>
Response: 200 OK
[...]
```

### Refresh Download URL
```
POST /api/exports/{job_id}/refresh-url
Authorization: Bearer <token>
Response: 200 OK
{...}
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

```bash
# Ensure PYTHONPATH includes the src directory
export PYTHONPATH=runs/kit/REQ-018/src:$PYTHONPATH
```

### Database Connection Errors

1. Verify PostgreSQL is running
2. Check DATABASE_URL format
3. Ensure database exists

### S3 Errors in Production

1. Verify AWS credentials
2. Check bucket exists and has correct permissions
3. Verify region matches bucket location

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run REQ-018 Tests
  env:
    DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test
    PYTHONPATH: runs/kit/REQ-018/src
  run: |
    pip install -r runs/kit/REQ-018/requirements.txt
    pytest runs/kit/REQ-018/test -v --junitxml=reports/junit.xml
```

### Jenkins Pipeline

```groovy
stage('REQ-018 Tests') {
    environment {
        DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test'
        PYTHONPATH = 'runs/kit/REQ-018/src'
    }
    steps {
        sh 'pip install -r runs/kit/REQ-018/requirements.txt'
        sh 'pytest runs/kit/REQ-018/test -v --junitxml=reports/junit.xml'
    }
}
```

## Artifacts

- **Source Code**: `runs/kit/REQ-018/src/`
- **Tests**: `runs/kit/REQ-018/test/`
- **Migrations**: `runs/kit/REQ-018/src/storage/sql/`
- **Reports**: `reports/` (generated)