# REQ-022: Data Retention Jobs

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL database
- AWS credentials (for S3 storage)

### Installation

```bash
cd runs/kit/REQ-022
pip install -r requirements.txt
```

### Database Setup

```bash
# Set database URL
export DATABASE_URL=postgresql://user:pass@localhost:5432/voicesurvey

# Run migrations
./scripts/db_upgrade.sh

# Seed test data (optional)
psql $DATABASE_URL -f src/storage/seed/seed.sql
```

### Running Tests

```bash
# Unit tests (no database required)
pytest test/ -v -k "not migration"

# All tests (requires database)
DATABASE_URL=postgresql://... pytest test/ -v
```

### API Usage

```python
from infra.retention import (
    RetentionService,
    GDPRDeletionService,
    RetentionScheduler,
)
from infra.retention.repository import PostgresRetentionRepository
from infra.retention.storage import S3StorageBackend
from infra.retention.audit import PostgresAuditLogger

# Initialize services
repository = PostgresRetentionRepository(session)
storage = S3StorageBackend(bucket_name="recordings")
audit_logger = PostgresAuditLogger(session)

retention_service = RetentionService(repository, storage, audit_logger)
gdpr_service = GDPRDeletionService(repository, storage, audit_logger)

# Run retention job
result = await retention_service.run_retention_job()
print(f"Deleted {result.total_deleted} items")

# Create GDPR request
request = await gdpr_service.create_deletion_request(
    contact_id=uuid4(),
    contact_phone="+14155551234"
)
print(f"Request deadline: {request.deadline}")
```

### Scheduler Integration

```python
from infra.retention import RetentionScheduler

scheduler = RetentionScheduler(
    retention_service=retention_service,
    gdpr_service=gdpr_service,
    daily_run_time=time(2, 0),  # 2 AM UTC
)

# Start scheduler (runs in background)
await scheduler.start()

# Manual trigger
result = await scheduler.run_now()

# Stop scheduler
await scheduler.stop()
```

## File Structure

```
runs/kit/REQ-022/
├── src/
│   ├── app/
│   │   └── shared/
│   │       └── __init__.py
│   ├── infra/
│   │   ├── __init__.py
│   │   └── retention/
│   │       ├── __init__.py
│   │       ├── models.py
│   │       ├── interfaces.py
│   │       ├── service.py
│   │       ├── gdpr.py
│   │       ├── scheduler.py
│   │       ├── repository.py
│   │       ├── storage.py
│   │       ├── audit.py
│   │       └── api.py
│   └── storage/
│       ├── sql/
│       │   ├── V0004.up.sql
│       │   └── V0004.down.sql
│       └── seed/
│           └── seed.sql
├── scripts/
│   ├── db_upgrade.sh
│   └── db_downgrade.sh
├── test/
│   ├── __init__.py
│   ├── test_retention_models.py
│   ├── test_retention_service.py
│   ├── test_gdpr_service.py
│   ├── test_retention_scheduler.py
│   ├── test_retention_api.py
│   ├── test_migration_sql.py
│   └── test_storage_backends.py
├── docs/
│   ├── KIT_REQ-022.md
│   └── README_REQ-022.md
├── ci/
│   ├── LTC.json
│   └── HOWTO.md
└── requirements.txt