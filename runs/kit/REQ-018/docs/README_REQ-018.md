# REQ-018: Campaign CSV Export

## Overview

This module implements CSV export functionality for campaign results in the VoiceSurveyAgent system. Campaign managers and administrators can export contact outcomes and survey responses to CSV files stored in AWS S3.

## Features

- **Async Export Processing**: Exports run in the background without blocking API responses
- **S3 Storage**: CSV files stored in S3 with presigned download URLs
- **RBAC Protected**: Only campaign_manager and admin roles can export
- **Comprehensive Data**: Includes contact info, outcomes, and survey answers

## Quick Start

### Installation

```bash
pip install -r runs/kit/REQ-018/requirements.txt
```

### Configuration

Set environment variables:

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"
export S3_BUCKET_NAME="your-bucket"
export AWS_REGION="eu-central-1"
```

### Run Tests

```bash
PYTHONPATH=runs/kit/REQ-018/src pytest runs/kit/REQ-018/test -v
```

## Usage

### Initiate Export

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://api/api/campaigns/{campaign_id}/export",
        headers={"Authorization": f"Bearer {token}"}
    )
    job_id = response.json()["job_id"]
```

### Check Status

```python
response = await client.get(
    f"http://api/api/exports/{job_id}",
    headers={"Authorization": f"Bearer {token}"}
)
if response.json()["status"] == "completed":
    download_url = response.json()["download_url"]
```

## CSV Format

| Column | Description |
|--------|-------------|
| campaign_id | Campaign UUID |
| contact_id | Contact UUID |
| external_contact_id | External reference ID |
| phone_number | E.164 phone number |
| outcome | completed/refused/not_reached/excluded |
| attempt_count | Number of call attempts |
| last_attempt_at | Timestamp of last attempt |
| completed_at | Survey completion timestamp |
| q1_answer | Answer to question 1 |
| q2_answer | Answer to question 2 |
| q3_answer | Answer to question 3 |

## Architecture

See [KIT_REQ-018.md](./KIT_REQ-018.md) for detailed architecture documentation.

## Related REQs

- REQ-017: Campaign dashboard stats API
- REQ-004: Campaign CRUD API
- REQ-014: Survey response persistence
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-018**: Campaign CSV export

### Rationale
REQ-018 depends on REQ-017 (Campaign dashboard stats API) which is marked as `in_progress`. This REQ implements the CSV export functionality that allows campaign managers to download campaign results.

### In Scope
- Export job creation and async processing
- CSV generation with contact outcomes and survey answers
- S3 storage integration with presigned URLs
- RBAC enforcement (campaign_manager and admin only)
- Database migration for export_jobs table
- Unit and integration tests

### Out of Scope
- Real S3 integration testing (uses mock storage in tests)
- Frontend UI for export (REQ-024)
- Export scheduling/automation

### How to Run Tests

```bash
# Install dependencies
pip install -r runs/kit/REQ-018/requirements.txt

# Set PYTHONPATH
export PYTHONPATH=runs/kit/REQ-018/src:$PYTHONPATH

# Run all tests (requires PostgreSQL)
pytest runs/kit/REQ-018/test -v

# Run unit tests only (no database required)
SKIP_DB_TESTS=1 pytest runs/kit/REQ-018/test -v \
  --ignore=runs/kit/REQ-018/test/test_migration_sql.py \
  --ignore=runs/kit/REQ-018/test/test_router.py
```

### Prerequisites
- Python 3.12+
- PostgreSQL 14+ (for integration tests)
- pip for dependency installation

### Dependencies and Mocks
- **InMemoryStorageProvider**: Mock S3 storage for testing
- **Database fixtures**: Test users, campaigns, contacts with various states
- **JWT tokens**: Generated for authentication testing

### Product Owner Notes
- Export only includes contacts in terminal states (completed, refused, not_reached, excluded)
- Pending and in_progress contacts are excluded from exports
- Download URLs expire after configurable duration (default 1 hour)
- URL refresh endpoint available for completed exports

### RAG Citations
- `runs/kit/REQ-017/src/app/shared/__init__.py`: Module structure pattern
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql`: Migration pattern for enum types and tables
- `runs/kit/REQ-015/src/app/__init__.py`: Package initialization pattern

```json
{
  "index": [
    {
      "req": "REQ-018",
      "src": [
        "runs/kit/REQ-018/src/app/__init__.py",
        "runs/kit/REQ-018/src/app/shared/__init__.py",
        "runs/kit/REQ-018/src/app/shared/config.py",
        "runs/kit/REQ-018/src/app/shared/database.py",
        "runs/kit/REQ-018/src/app/shared/models.py",
        "runs/kit/REQ-018/src/app/shared/exceptions.py",
        "runs/kit/REQ-018/src/app/shared/auth.py",
        "runs/kit/REQ-018/src/app/dashboard/__init__.py",
        "runs/kit/REQ-018/src/app/dashboard/schemas.py",
        "runs/kit/REQ-018/src/app/dashboard/storage.py",
        "runs/kit/REQ-018/src/app/dashboard/export_service.py",
        "runs/kit/REQ-018/src/app/dashboard/router.py",
        "runs/kit/REQ-018/src/app/main.py",
        "runs/kit/REQ-018/src/storage/sql/V0002.up.sql",
        "runs/kit/REQ-018/src/storage/sql/V0002.down.sql"
      ],
      "tests": [
        "runs/kit/REQ-018/test/__init__.py",
        "runs/kit/REQ-018/test/conftest.py",
        "runs/kit/REQ-018/test/test_export_service.py",
        "runs/kit/REQ-018/test/test_storage.py",
        "runs/kit/REQ-018/test/test_router.py",
        "runs/kit/REQ-018/test/test_migration_sql.py"
      ]
    }
  ]
}