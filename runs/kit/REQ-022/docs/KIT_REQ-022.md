# KIT Documentation — REQ-022: Data Retention Jobs

## Overview

REQ-022 implements the data retention job system for the voicesurveyagent platform. This includes:

- **Scheduled retention jobs** that run daily to delete expired recordings and transcripts
- **GDPR deletion request processing** with 72-hour deadline compliance
- **Audit logging** for all deletion operations
- **Admin API endpoints** for manual triggering and monitoring

## Architecture

### Components

```
infra/retention/
├── __init__.py          # Module exports
├── models.py            # Data models (RetentionConfig, DeletionRecord, etc.)
├── interfaces.py        # Abstract interfaces (StorageBackend, RetentionRepository)
├── service.py           # Core retention service
├── gdpr.py              # GDPR deletion service
├── scheduler.py         # Background job scheduler
├── repository.py        # PostgreSQL repository implementation
├── storage.py           # Storage backends (S3, local)
├── audit.py             # Audit logging implementations
└── api.py               # FastAPI endpoints
```

### Data Flow

1. **Scheduled Retention Job**:
   - Scheduler triggers daily at configured time (default 2 AM UTC)
   - Service queries for expired recordings/transcripts based on retention config
   - Storage backend deletes files from S3/local storage
   - Repository marks records as deleted in database
   - Audit logger records all operations

2. **GDPR Deletion Request**:
   - Admin creates request via API
   - Request stored with 72-hour deadline
   - Scheduler processes pending requests hourly
   - All contact data deleted/anonymized
   - Audit trail maintained for compliance

## Database Schema

### New Tables (V0004)

```sql
-- GDPR deletion requests
CREATE TABLE gdpr_deletion_requests (
    id UUID PRIMARY KEY,
    contact_id UUID NOT NULL,
    contact_phone VARCHAR(20),
    contact_email VARCHAR(255),
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    status gdpr_request_status NOT NULL DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE,
    items_deleted INTEGER DEFAULT 0,
    error_message TEXT
);

-- Retention job history
CREATE TABLE retention_job_history (
    id UUID PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL,
    recordings_deleted INTEGER DEFAULT 0,
    recordings_failed INTEGER DEFAULT 0,
    transcripts_deleted INTEGER DEFAULT 0,
    transcripts_failed INTEGER DEFAULT 0,
    total_deleted INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    error_message TEXT
);
```

## API Endpoints

### POST /api/admin/retention/trigger

Trigger a manual retention job.

**Request:**
```json
{
  "recording_retention_days": 30,
  "transcript_retention_days": 60,
  "dry_run": false
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "recordings_deleted": 45,
  "transcripts_deleted": 38,
  "total_deleted": 83
}
```

### POST /api/admin/retention/gdpr

Create a GDPR deletion request.

**Request:**
```json
{
  "contact_id": "uuid",
  "contact_phone": "+14155551234",
  "contact_email": "user@example.com"
}
```

**Response:**
```json
{
  "id": "uuid",
  "contact_id": "uuid",
  "status": "pending",
  "deadline": "2024-06-18T12:00:00Z"
}
```

### GET /api/admin/retention/status

Get current retention system status.

**Response:**
```json
{
  "scheduler_running": true,
  "pending_gdpr_requests": 3,
  "overdue_gdpr_requests": 0
}
```

## Configuration

Retention settings are read from `provider_configs` table:

- `recording_retention_days`: Days to keep recordings (default: 180)
- `transcript_retention_days`: Days to keep transcripts (default: 180)

Environment variables:
- `S3_BUCKET_NAME`: S3 bucket for recordings
- `AWS_REGION`: AWS region (default: eu-central-1)

## Acceptance Criteria Mapping

| Criterion | Implementation |
|-----------|----------------|
| Retention job runs daily | `RetentionScheduler._run_retention_loop()` |
| Recordings deleted after retention_days | `RetentionService._process_recordings()` |
| Deletion logged with count/timestamp | `PostgresAuditLogger.log_retention_job()` |
| Partial failures handled gracefully | `DeletionStatus.PARTIAL` in `RetentionResult` |
| GDPR requests processed within 72h | `GDPRDeletionRequest.deadline` + scheduler |

## Testing

```bash
# Run all tests
pytest runs/kit/REQ-022/test/ -v

# Run with database (requires DATABASE_URL)
DATABASE_URL=postgresql://... pytest runs/kit/REQ-022/test/ -v

# Run specific test file
pytest runs/kit/REQ-022/test/test_retention_service.py -v
```

## Dependencies

- REQ-019: Admin configuration API (provides ProviderConfig with retention settings)
- REQ-001: Database schema (provides base tables and audit_logs)