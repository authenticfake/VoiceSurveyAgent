# REQ-006: Contact CSV Upload and Parsing - Execution Guide

## Overview

This KIT implements the contact CSV upload and parsing functionality for the voicesurveyagent system. It provides:

- CSV file upload endpoint for campaign contacts
- Phone number validation (E.164 format)
- Email validation
- Flexible header parsing with aliases
- Duplicate detection (within file and campaign)
- Paginated contact listing
- State filtering for contacts

## Prerequisites

### System Requirements

- Python 3.12+
- pip or Poetry for dependency management
- PostgreSQL 15+ (for integration tests with real DB)
- SQLite (for unit tests)

### Environment Variables

```bash
# Required for tests
export PYTHONPATH="runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
export TEST_DATABASE_URL="sqlite+aiosqlite:///:memory:"

# Auth configuration (for API tests)
export OIDC_ISSUER_URL="https://test.example.com"
export OIDC_CLIENT_ID="test-client"
export OIDC_CLIENT_SECRET="test-secret"
export JWT_SECRET_KEY="test-jwt-secret-key-for-testing-only"
export LOG_LEVEL="DEBUG"
```

## Installation

### Using pip

```bash
# Install dependencies
pip install -r runs/kit/REQ-006/requirements.txt

# Also install dependencies from prior REQs
pip install -r runs/kit/REQ-001/requirements.txt
pip install -r runs/kit/REQ-002/requirements.txt
pip install -r runs/kit/REQ-003/requirements.txt
pip install -r runs/kit/REQ-004/requirements.txt
pip install -r runs/kit/REQ-005/requirements.txt
```

### Using Poetry (if available)

```bash
poetry install
```

## Running Tests

### All Tests

```bash
# Run all tests with coverage
pytest runs/kit/REQ-006/test/ -v \
  --cov=app.contacts \
  --cov-report=term-missing \
  --cov-report=xml:runs/kit/REQ-006/reports/coverage.xml \
  --junitxml=runs/kit/REQ-006/reports/junit.xml
```

### Unit Tests Only

```bash
# CSV parser unit tests
pytest runs/kit/REQ-006/test/test_csv_parser.py -v
```

### Integration Tests

```bash
# Service integration tests
pytest runs/kit/REQ-006/test/test_contact_service.py -v

# API router tests
pytest runs/kit/REQ-006/test/test_contact_router.py -v
```

### With Real PostgreSQL Database

```bash
# Set PostgreSQL URL
export TEST_DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/test_db"

# Run tests
pytest runs/kit/REQ-006/test/ -v
```

## Code Quality Checks

### Linting

```bash
ruff check runs/kit/REQ-006/src/app/contacts/ runs/kit/REQ-006/test/
ruff format runs/kit/REQ-006/src/app/contacts/ runs/kit/REQ-006/test/
```

### Type Checking

```bash
mypy runs/kit/REQ-006/src/app/contacts/ --ignore-missing-imports
```

### Security Scan

```bash
bandit -r runs/kit/REQ-006/src/app/contacts/ -ll
```

## API Endpoints

### Upload Contacts CSV

```bash
# Upload CSV file
curl -X POST "http://localhost:8080/api/campaigns/{campaign_id}/contacts/upload" \
  -H "Authorization: Bearer {token}" \
  -F "file=@contacts.csv"

# With custom delimiter
curl -X POST "http://localhost:8080/api/campaigns/{campaign_id}/contacts/upload?delimiter=;" \
  -H "Authorization: Bearer {token}" \
  -F "file=@contacts.csv"
```

### List Contacts

```bash
# List all contacts
curl -X GET "http://localhost:8080/api/campaigns/{campaign_id}/contacts" \
  -H "Authorization: Bearer {token}"

# With pagination
curl -X GET "http://localhost:8080/api/campaigns/{campaign_id}/contacts?page=1&page_size=20" \
  -H "Authorization: Bearer {token}"

# With state filter
curl -X GET "http://localhost:8080/api/campaigns/{campaign_id}/contacts?state=pending" \
  -H "Authorization: Bearer {token}"
```

### Get Single Contact

```bash
curl -X GET "http://localhost:8080/api/campaigns/{campaign_id}/contacts/{contact_id}" \
  -H "Authorization: Bearer {token}"
```

## CSV File Format

### Required Columns

- `phone_number` (or aliases: `phone`, `telephone`, `tel`, `mobile`)

### Optional Columns

- `external_contact_id` (or aliases: `contact_id`, `ext_id`, `id`)
- `email` (or aliases: `mail`, `e-mail`, `email_address`)
- `language` (or aliases: `lang`, `locale`, `preferred_language`)
- `has_prior_consent` (or aliases: `consent`, `prior_consent`)
- `do_not_call` (or aliases: `dnc`, `do_not_contact`)

### Example CSV

```csv
phone_number,email,external_contact_id,language,has_prior_consent,do_not_call
+14155551234,test@example.com,EXT001,en,true,false
+14155551235,test2@example.com,EXT002,it,false,false
+14155551236,,EXT003,auto,true,true
```

### Phone Number Format

Phone numbers must be in E.164 format:
- Start with `+` followed by country code
- 1-15 digits after the `+`
- Examples: `+14155551234`, `+442071234567`, `+393331234567`

## Troubleshooting

### Import Errors

If you encounter import errors, ensure PYTHONPATH includes all required source directories:

```bash
export PYTHONPATH="runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
```

### Database Connection Issues

For SQLite (unit tests):
```bash
export TEST_DATABASE_URL="sqlite+aiosqlite:///:memory:"
```

For PostgreSQL (integration tests):
```bash
export TEST_DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/test_db"
```

### Authentication Errors in Tests

The test fixtures mock authentication. If you see 401 errors, ensure:
1. The `conftest.py` fixtures are properly loaded
2. The `override_db_session` fixture is active
3. Auth headers include required test headers

## Reports

After running tests with coverage, reports are generated at:

- JUnit XML: `runs/kit/REQ-006/reports/junit.xml`
- Coverage XML: `runs/kit/REQ-006/reports/coverage.xml`

## Dependencies on Prior REQs

This KIT depends on:

- **REQ-001**: Database schema (Contact table, enums)
- **REQ-002**: Authentication (User model, JWT validation)
- **REQ-003**: RBAC (Role-based access control)
- **REQ-004**: Campaign CRUD (Campaign model, repository)
- **REQ-005**: Campaign validation (Contact repository protocol)