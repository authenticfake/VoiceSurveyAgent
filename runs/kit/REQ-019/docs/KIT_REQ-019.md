# KIT Documentation: REQ-019 - Admin Configuration API

## Summary

REQ-019 implements the Admin Configuration API for the VoiceSurveyAgent platform. This module provides endpoints for managing system configuration including telephony provider settings, LLM configuration, email settings, and data retention policies. All configuration changes are logged in an audit trail for compliance purposes.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| GET /api/admin/config returns current configuration | ✅ | `router.py:get_config()` |
| PUT /api/admin/config updates provider settings | ✅ | `router.py:update_config()` |
| Telephony provider credentials stored in Secrets Manager | ✅ | `secrets.py:AWSSecretsManager` |
| Config changes logged in audit trail | ✅ | `service.py:update_config()` |
| Admin role required for all config endpoints | ✅ | `router.py:get_current_user_id()` |

## Architecture

### Module Structure

```
runs/kit/REQ-019/
├── src/
│   └── app/
│       ├── admin/
│       │   ├── __init__.py      # Module exports
│       │   ├── models.py        # SQLAlchemy models
│       │   ├── schemas.py       # Pydantic schemas
│       │   ├── repository.py    # Data access layer
│       │   ├── service.py       # Business logic
│       │   ├── router.py        # FastAPI endpoints
│       │   └── secrets.py       # AWS Secrets Manager integration
│       ├── auth/
│       │   ├── __init__.py
│       │   └── models.py        # User model (minimal for audit logs)
│       └── shared/
│           ├── __init__.py
│           ├── config.py        # Application settings
│           ├── database.py      # Database connection
│           └── exceptions.py    # Custom exceptions
├── test/
│   ├── conftest.py              # Test fixtures
│   ├── test_admin_api.py        # API endpoint tests
│   ├── test_admin_service.py    # Service layer tests
│   ├── test_secrets_manager.py  # Secrets Manager tests
│   └── test_migration_sql.py    # Migration tests
└── storage/
    ├── sql/
    │   ├── V0003.up.sql         # Create tables
    │   └── V0003.down.sql       # Drop tables
    └── seed/
        └── seed.sql             # Sample data
```

### Key Components

1. **AdminConfigService**: Core business logic for configuration management
2. **AdminConfigRepository**: Data access layer for database operations
3. **SecretsManagerInterface**: Abstract interface for secrets storage
4. **AWSSecretsManager**: Production implementation using AWS Secrets Manager
5. **MockSecretsManager**: Test implementation for unit testing

### Data Flow

```
Client Request
     │
     ▼
┌─────────────┐
│   Router    │ ◄── RBAC check (admin only)
└─────────────┘
     │
     ▼
┌─────────────┐
│   Service   │ ◄── Business logic, audit logging
└─────────────┘
     │
     ├──────────────────┐
     ▼                  ▼
┌─────────────┐  ┌─────────────────┐
│ Repository  │  │ Secrets Manager │
└─────────────┘  └─────────────────┘
     │                  │
     ▼                  ▼
┌─────────────┐  ┌─────────────────┐
│  PostgreSQL │  │ AWS Secrets Mgr │
└─────────────┘  └─────────────────┘
```

## API Endpoints

### GET /api/admin/config

Returns the current system configuration.

**Headers:**
- `X-User-ID`: UUID of the requesting user
- `X-User-Role`: Must be "admin"

**Response:**
```json
{
  "id": "uuid",
  "telephony": {
    "provider_type": "telephony_api",
    "provider_name": "twilio",
    "outbound_number": "+14155550100",
    "max_concurrent_calls": 10
  },
  "llm": {
    "llm_provider": "openai",
    "llm_model": "gpt-4.1-mini"
  },
  "email": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_username": "user@example.com",
    "from_email": "noreply@example.com",
    "from_name": "Voice Survey"
  },
  "retention": {
    "recording_retention_days": 180,
    "transcript_retention_days": 180
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### PUT /api/admin/config

Updates system configuration. Only provided fields are updated.

**Request Body:**
```json
{
  "telephony": {
    "provider_name": "telnyx",
    "max_concurrent_calls": 20,
    "api_key": "secret-key"
  },
  "llm": {
    "llm_provider": "anthropic",
    "llm_model": "claude-4.5-sonnet",
    "api_key": "secret-key"
  },
  "email": {
    "smtp_host": "smtp.newhost.com",
    "smtp_password": "secret-password"
  },
  "retention": {
    "recording_retention_days": 365
  }
}
```

### GET /api/admin/audit-logs

Returns paginated audit log entries.

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50, max: 100)
- `resource_type`: Filter by resource type
- `user_id`: Filter by user ID

## Security Considerations

1. **Credentials Storage**: All sensitive credentials (API keys, passwords) are stored in AWS Secrets Manager, never in the database.

2. **Audit Logging**: Every configuration read and update is logged with:
   - User ID
   - Action performed
   - Changes made (credentials redacted)
   - IP address
   - User agent
   - Timestamp

3. **RBAC**: All endpoints require admin role. Non-admin users receive 403 Forbidden.

4. **Response Sanitization**: Credentials are never returned in API responses.

## Database Schema

### email_configs Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| provider_config_id | UUID | FK to provider_configs |
| smtp_host | VARCHAR(255) | SMTP server hostname |
| smtp_port | INTEGER | SMTP server port |
| smtp_username | VARCHAR(255) | SMTP username |
| from_email | VARCHAR(255) | Sender email address |
| from_name | VARCHAR(255) | Sender display name |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### audit_logs Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK to users |
| action | VARCHAR(50) | Action performed |
| resource_type | VARCHAR(50) | Type of resource |
| resource_id | UUID | ID of affected resource |
| changes | JSONB | Change details |
| ip_address | VARCHAR(45) | Client IP address |
| user_agent | TEXT | Client user agent |
| created_at | TIMESTAMP | Action timestamp |

## Dependencies

This module depends on:
- REQ-001: Database schema (provider_configs, users tables)
- REQ-002: OIDC authentication (User model)
- REQ-003: RBAC authorization (role checking)

## Testing

### Unit Tests
- Service layer logic
- Repository operations
- Secrets Manager interface

### Integration Tests
- API endpoint behavior
- Database operations
- Audit log creation

### Test Coverage Target: 80%

Run tests:
```bash
cd runs/kit/REQ-019
PYTHONPATH=src pytest test/ -v --cov=src