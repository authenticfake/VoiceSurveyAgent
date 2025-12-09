# REQ-019: Admin Configuration API

## Quick Start

```bash
# Setup
cd runs/kit/REQ-019
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
PYTHONPATH=src pytest test/ -v

# Run with coverage
PYTHONPATH=src pytest test/ -v --cov=src --cov-report=html
```

## What This Implements

- `GET /api/admin/config` - Retrieve current system configuration
- `PUT /api/admin/config` - Update system configuration
- `GET /api/admin/audit-logs` - View configuration change history

## Key Features

1. **Secure Credential Storage**: API keys and passwords stored in AWS Secrets Manager
2. **Audit Trail**: All configuration changes logged with user, timestamp, and details
3. **RBAC Enforcement**: Admin role required for all endpoints
4. **Partial Updates**: Only update the fields you need

## Configuration Sections

- **Telephony**: Provider type, name, outbound number, concurrency limits
- **LLM**: Provider selection, model configuration
- **Email**: SMTP settings, sender information
- **Retention**: Recording and transcript retention periods

## Files

| Path | Purpose |
|------|---------|
| `src/app/admin/router.py` | API endpoints |
| `src/app/admin/service.py` | Business logic |
| `src/app/admin/secrets.py` | AWS Secrets Manager |
| `src/storage/sql/V0003.up.sql` | Database migration |
| `test/test_admin_api.py` | API tests |

## Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/db
APP_ENV=development
AWS_REGION=eu-central-1
AWS_SECRETS_MANAGER_PREFIX=voicesurvey
```

## See Also

- [KIT_REQ-019.md](./KIT_REQ-019.md) - Detailed implementation documentation
- [HOWTO.md](../ci/HOWTO.md) - Execution guide
- [LTC.json](../ci/LTC.json) - Test contract
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-019**: Admin configuration API

### Rationale
REQ-019 depends on REQ-003 (RBAC authorization middleware) which is in_progress. This REQ implements the admin configuration endpoints that allow system administrators to manage telephony, LLM, email, and retention settings. All credentials are stored securely in AWS Secrets Manager, and all changes are logged in an audit trail.

### In Scope
- GET /api/admin/config endpoint returning current configuration
- PUT /api/admin/config endpoint for updating configuration
- GET /api/admin/audit-logs endpoint for viewing change history
- AWS Secrets Manager integration for credential storage
- Audit logging for all configuration changes
- Admin role enforcement on all endpoints
- Database migrations for email_configs and audit_logs tables
- Comprehensive test coverage

### Out of Scope
- Full OIDC integration (handled by REQ-002)
- Full RBAC middleware (handled by REQ-003)
- Actual AWS Secrets Manager calls in tests (mocked)
- Frontend UI for admin configuration (REQ-023/REQ-024)

### How to Run Tests

```bash
# Navigate to REQ-019 directory
cd runs/kit/REQ-019

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
export APP_ENV="test"
export PYTHONPATH="src"

# Run all tests
pytest test/ -v

# Run with coverage
pytest test/ -v --cov=src --cov-report=html
```

### Prerequisites
- Python 3.12+
- PostgreSQL 14+ (for integration tests)
- Base migrations from REQ-001 must be applied first
- pip for package management

### Dependencies and Mocks
- **MockSecretsManager**: Used in tests instead of real AWS Secrets Manager to avoid AWS dependencies in CI
- **Test database**: Uses separate test database (voicesurvey_test) to avoid affecting development data
- **User authentication**: Simplified header-based auth for testing; real auth comes from REQ-002/REQ-003

### Product Owner Notes
- Credentials are never returned in API responses for security
- Audit logs include redacted credential changes (shows "***REDACTED***")
- Default configuration is created automatically if none exists
- Email validation uses simple @ check; could be enhanced with full RFC validation

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Referenced for provider_configs table structure
- `runs/kit/REQ-001/src/storage/seed/seed.sql` - Referenced for seed data patterns
- `runs/kit/REQ-018/src/storage/sql/V0002.up.sql` - Referenced for migration patterns
- `runs/kit/REQ-015/src/app/shared/__init__.py` - Referenced for shared module structure

```json
{
  "index": [
    {
      "req": "REQ-019",
      "src": [
        "runs/kit/REQ-019/src/app/__init__.py",
        "runs/kit/REQ-019/src/app/shared/__init__.py",
        "runs/kit/REQ-019/src/app/shared/config.py",
        "runs/kit/REQ-019/src/app/shared/database.py",
        "runs/kit/REQ-019/src/app/shared/exceptions.py",
        "runs/kit/REQ-019/src/app/admin/__init__.py",
        "runs/kit/REQ-019/src/app/admin/schemas.py",
        "runs/kit/REQ-019/src/app/admin/models.py",
        "runs/kit/REQ-019/src/app/admin/secrets.py",
        "runs/kit/REQ-019/src/app/admin/repository.py",
        "runs/kit/REQ-019/src/app/admin/service.py",
        "runs/kit/REQ-019/src/app/admin/router.py",
        "runs/kit/REQ-019/src/app/auth/__init__.py",
        "runs/kit/REQ-019/src/app/auth/models.py",
        "runs/kit/REQ-019/src/storage/sql/V0003.up.sql",
        "runs/kit/REQ-019/src/storage/sql/V0003.down.sql",
        "runs/kit/REQ-019/src/storage/seed/seed.sql"
      ],
      "tests": [
        "runs/kit/REQ-019/test/__init__.py",
        "runs/kit/REQ-019/test/conftest.py",
        "runs/kit/REQ-019/test/test_admin_api.py",
        "runs/kit/REQ-019/test/test_admin_service.py",
        "runs/kit/REQ-019/test/test_secrets_manager.py",
        "runs/kit/REQ-019/test/test_migration_sql.py",
        "runs/kit/REQ-019/test/api/admin.json"
      ]
    }
  ]
}