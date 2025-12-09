# KIT Documentation — REQ-018: Campaign CSV Export

## Summary

REQ-018 implements the Campaign CSV Export functionality for the VoiceSurveyAgent system. This feature allows campaign managers and administrators to export campaign results to CSV files, which are stored in AWS S3 with time-limited presigned download URLs.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| GET /api/campaigns/{id}/export initiates export job | ✅ | `router.py:initiate_export()` |
| Export includes campaign_id, contact_id, external_contact_id | ✅ | `export_service.py:_generate_csv()` |
| Async job stores CSV in S3 with signed URL | ✅ | `export_service.py:process_export_job()` |
| Download URL returned with expiration | ✅ | `storage.py:generate_presigned_url()` |
| Export respects RBAC (campaign_manager or admin only) | ✅ | `router.py` with `require_campaign_manager` |

## Architecture

### Components

```
app/
├── dashboard/
│   ├── __init__.py          # Module init
│   ├── schemas.py           # Pydantic schemas for export
│   ├── storage.py           # Storage provider interface (S3)
│   ├── export_service.py    # Export business logic
│   └── router.py            # FastAPI endpoints
├── shared/
│   ├── config.py            # Application configuration
│   ├── database.py          # Database session management
│   ├── models.py            # SQLAlchemy models (ExportJob)
│   ├── exceptions.py        # Custom exceptions
│   └── auth.py              # Authentication/authorization
└── main.py                  # FastAPI application
```

### Data Flow

1. User requests export via `GET /api/campaigns/{id}/export`
2. System creates `ExportJob` record with `pending` status
3. Background task processes the export:
   - Queries contacts with terminal states
   - Generates CSV content
   - Uploads to S3
   - Generates presigned URL
   - Updates job status to `completed`
4. User polls `GET /api/exports/{job_id}` for status
5. When complete, user downloads via presigned URL

### Database Schema

New table `export_jobs` (V0002 migration):

```sql
CREATE TABLE export_jobs (
    id UUID PRIMARY KEY,
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    requested_by_user_id UUID REFERENCES users(id),
    status export_job_status NOT NULL DEFAULT 'pending',
    s3_key VARCHAR(500),
    download_url TEXT,
    url_expires_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    total_records INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
```

## Key Design Decisions

### 1. Async Export Processing

Exports are processed asynchronously via FastAPI BackgroundTasks to avoid blocking the API response. This allows:
- Immediate response to user (202 Accepted)
- Processing of large datasets without timeout
- Status polling for progress tracking

### 2. Storage Provider Interface

The `StorageProvider` abstract class allows:
- Production use with S3
- Testing with `InMemoryStorageProvider`
- Future extensibility (GCS, Azure Blob, etc.)

### 3. CSV Content Filtering

Only contacts in terminal states are exported:
- `completed`
- `refused`
- `not_reached`
- `excluded`

This ensures consistent, meaningful export data.

### 4. RBAC Enforcement

All export endpoints require `campaign_manager` or `admin` role:
- Viewers cannot export (may contain PII)
- Consistent with SPEC security requirements

## Dependencies

### From Previous REQs
- REQ-001: Database schema (Campaign, Contact, SurveyResponse models)
- REQ-002: OIDC authentication
- REQ-003: RBAC authorization
- REQ-017: Dashboard stats API (shared router prefix)

### External
- `aioboto3`: Async S3 client
- `pyjwt`: JWT token handling
- `sqlalchemy[asyncio]`: Async database operations

## Testing Strategy

### Unit Tests
- `test_export_service.py`: Export service logic
- `test_storage.py`: Storage provider operations

### Integration Tests
- `test_router.py`: API endpoint behavior
- `test_migration_sql.py`: Database migration verification

### Test Coverage
- Export job creation and processing
- CSV generation with correct headers
- RBAC enforcement
- Error handling

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+asyncpg://...` |
| `S3_BUCKET_NAME` | S3 bucket for exports | `voicesurvey-exports` |
| `S3_EXPORT_PREFIX` | S3 key prefix | `exports/` |
| `EXPORT_URL_EXPIRATION_SECONDS` | Presigned URL TTL | `3600` |
| `AWS_REGION` | AWS region | `eu-central-1` |

## API Reference

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/campaigns/{id}/export` | Initiate export | campaign_manager+ |
| GET | `/api/campaigns/{id}/exports` | List exports | campaign_manager+ |
| GET | `/api/exports/{job_id}` | Get job status | campaign_manager+ |
| POST | `/api/exports/{job_id}/refresh-url` | Refresh URL | campaign_manager+ |

### Response Schemas

See `schemas.py` for Pydantic models:
- `ExportJobCreateResponse`
- `ExportJobResponse`
- `ContactExportRow`