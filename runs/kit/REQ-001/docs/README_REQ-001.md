# REQ-001: Database Schema and Migrations

## Quick Start

```bash
# Install dependencies
pip install -r runs/kit/REQ-001/requirements.txt

# Set environment variables
export DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5432 DB_NAME=voicesurveyagent

# Run migrations
cd runs/kit/REQ-001/src/data/migrations
alembic upgrade head

# Run tests
pytest runs/kit/REQ-001/test -v
```

## Structure

```
runs/kit/REQ-001/
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   └── shared/
│   │       ├── __init__.py
│   │       ├── database.py          # DB session management
│   │       └── models/
│   │           ├── __init__.py
│   │           ├── enums.py          # All enum definitions
│   │           ├── user.py
│   │           ├── campaign.py
│   │           ├── contact.py
│   │           ├── exclusion.py
│   │           ├── call_attempt.py
│   │           ├── survey_response.py
│   │           ├── event.py
│   │           ├── email_notification.py
│   │           ├── email_template.py
│   │           ├── provider_config.py
│   │           └── transcript_snippet.py
│   └── data/
│       └── migrations/
│           ├── alembic.ini
│           └── migrations/
│               ├── env.py
│               ├── script.py.mako
│               └── versions/
│                   ├── V0001_create_enums.py
│                   ├── V0002_create_users_table.py
│                   ├── V0003_create_email_templates_table.py
│                   ├── V0004_create_campaigns_table.py
│                   ├── V0005_create_contacts_table.py
│                   ├── V0006_create_exclusion_list_entries_table.py
│                   ├── V0007_create_call_attempts_table.py
│                   ├── V0008_create_survey_responses_table.py
│                   ├── V0009_create_events_table.py
│                   ├── V0010_create_email_notifications_table.py
│                   ├── V0011_create_provider_config_table.py
│                   └── V0012_create_transcript_snippets_table.py
├── test/
│   ├── test_migrations.py
│   └── test_models.py
├── ci/
│   ├── LTC.json
│   └── HOWTO.md
├── docs/
│   ├── KIT_REQ-001.md
│   └── README_REQ-001.md
└── requirements.txt
```

## Migration Commands

```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one step
alembic downgrade -1

# Downgrade to base (remove all)
alembic downgrade base

# Show current version
alembic current

# Show history
alembic history
```
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-001**: Database schema and migrations

### Rationale
REQ-001 is the foundation layer with no dependencies. All other REQs depend on this schema being in place.

### In Scope
- All 11 entity models from SPEC data model
- 13 PostgreSQL enum types
- 12 Alembic migration scripts (one per entity + enums)
- SQLAlchemy ORM models with relationships
- Database session management utilities
- Comprehensive unit tests for models
- Integration tests for migrations (idempotency, rollback)
- LTC.json for CI execution
- HOWTO.md for operational guidance

### Out of Scope
- Seed data (separate concern)
- API endpoints (REQ-002+)
- Business logic services

### How to Run Tests

```bash
# Install dependencies
pip install -r runs/kit/REQ-001/requirements.txt

# Set environment
export DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5432 DB_NAME=voicesurveyagent_test
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-001/src"

# Create test database
createdb voicesurveyagent_test

# Run all tests
pytest runs/kit/REQ-001/test -v

# Run with coverage
pytest runs/kit/REQ-001/test --cov=runs/kit/REQ-001/src --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- pip or Poetry

### Dependencies and Mocks
- No external service mocks required
- Tests use real PostgreSQL database
- Alembic migrations tested against actual database

### Product Owner Notes
- All entities from SPEC implemented
- Enum types match SPEC exactly
- Indexes optimized for scheduler queries (composite index on contacts)
- Unique constraints enforce business rules (one survey response per contact per campaign)

### RAG Citations
- SPEC.md: Data Model section for entity definitions
- PLAN.md: REQ-001 acceptance criteria and KIT readiness
- TECH_CONSTRAINTS.yaml: PostgreSQL as primary database, SQLAlchemy ORM

```json
{
  "index": [
    {
      "req": "REQ-001",
      "src": [
        "runs/kit/REQ-001/src/data/migrations/alembic.ini",
        "runs/kit/REQ-001/src/data/migrations/migrations/env.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/script.py.mako",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0001_create_enums.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0002_create_users_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0003_create_email_templates_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0004_create_campaigns_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0005_create_contacts_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0006_create_exclusion_list_entries_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0007_create_call_attempts_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0008_create_survey_responses_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0009_create_events_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0010_create_email_notifications_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0011_create_provider_config_table.py",
        "runs/kit/REQ-001/src/data/migrations/migrations/versions/V0012_create_transcript_snippets_table.py",
        "runs/kit/REQ-001/src/app/__init__.py",
        "runs/kit/REQ-001/src/app/shared/__init__.py",
        "runs/kit/REQ-001/src/app/shared/database.py",
        "runs/kit/REQ-001/src/app/shared/models/__init__.py",
        "runs/kit/REQ-001/src/app/shared/models/enums.py",
        "runs/kit/REQ-001/src/app/shared/models/user.py",
        "runs/kit/REQ-001/src/app/shared/models/email_template.py",
        "runs/kit/REQ-001/src/app/shared/models/campaign.py",
        "runs/kit/REQ-001/src/app/shared/models/contact.py",
        "runs/kit/REQ-001/src/app/shared/models/exclusion.py",
        "runs/kit/REQ-001/src/app/shared/models/call_attempt.py",
        "runs/kit/REQ-001/src/app/shared/models/survey_response.py",
        "runs/kit/REQ-001/src/app/shared/models/event.py",
        "runs/kit/REQ-001/src/app/shared/models/email_notification.py",
        "runs/kit/REQ-001/src/app/shared/models/provider_config.py",
        "runs/kit/REQ-001/src/app/shared/models/transcript_snippet.py"
      ],
      "tests": [
        "runs/kit/REQ-001/test/test_migrations.py",
        "runs/kit/REQ-001/test/test_models.py"
      ]
    }
  ]
}
```
Human: 
Human: continue with the next open REQ-ID