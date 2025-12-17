# REQ-001: Database Schema and Migrations

## Quick Start

```bash
# 1. Start PostgreSQL
docker run -d --name pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=voicesurveyagent -p 5432:5432 postgres:15-alpine

# 2. Set connection string
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurveyagent"

# 3. Apply schema
psql $DATABASE_URL -f runs/kit/REQ-001/src/storage/sql/V0001.up.sql

# 4. Apply seed data
psql $DATABASE_URL -f runs/kit/REQ-001/src/storage/seed/seed.sql

# 5. Run tests
cd runs/kit/REQ-001
pip install -r requirements.txt
DISABLE_TESTCONTAINERS=1 pytest test/test_migration_sql.py -v
```

## What This Implements

- **12 database tables** matching SPEC data model
- **15 enum types** for type-safe status fields
- **UUID primary keys** using PostgreSQL native type
- **25+ indexes** on foreign keys for query performance
- **Automatic updated_at** via database triggers
- **Idempotent migrations** safe to re-run
- **Seed data** with 10-20 records per table

## Files

```
runs/kit/REQ-001/
├── src/storage/
│   ├── sql/
│   │   ├── V0001.up.sql      # Schema creation
│   │   └── V0001.down.sql    # Schema rollback
│   └── seed/
│       └── seed.sql          # Test data
├── scripts/
│   ├── db_upgrade.sh         # Apply migrations
│   ├── db_downgrade.sh       # Rollback migrations
│   └── db_seed.sh            # Apply seed data
├── test/
│   └── test_migration_sql.py # Migration tests
├── ci/
│   ├── LTC.json              # Test contract
│   └── HOWTO.md              # Execution guide
└── docs/
    ├── KIT_REQ-001.md        # Technical docs
    └── README_REQ-001.md     # This file
```

## Next Steps

This schema is the foundation for:
- REQ-002: OIDC authentication (uses `users` table)
- REQ-009: Telephony adapter (uses `provider_configs`)
- REQ-011: LLM gateway (uses `provider_configs`)
- REQ-021: Observability (uses all tables for metrics)
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-001**: Database schema and migrations

### Rationale
REQ-001 is the foundation for the entire voicesurveyagent system. It has no dependencies and is required by REQ-002, REQ-009, REQ-011, and REQ-021. All other REQs depend on the database schema being in place.

### In Scope
- All 12 entities from SPEC data model (users, campaigns, contacts, call_attempts, survey_responses, events, email_notifications, email_templates, exclusion_list_entries, provider_configs, transcript_snippets, schema_migrations)
- 15 enum types for all status and type fields
- UUID primary keys using PostgreSQL native type
- Foreign key indexes for query performance
- Idempotent migration scripts (up/down)
- Seed data with 10-20 records
- Comprehensive test suite for schema validation

### Out of Scope
- Alembic Python integration (using pure SQL migrations per PLAN guidance)
- ORM models (will be derived in subsequent REQs)
- Application-level database access code

### How to Run Tests

```bash
# Option 1: With Docker (recommended)
cd runs/kit/REQ-001
pip install -r requirements.txt
pytest test/test_migration_sql.py -v

# Option 2: With local PostgreSQL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurveyagent_test"
export DISABLE_TESTCONTAINERS=1
cd runs/kit/REQ-001
pip install -r requirements.txt
pytest test/test_migration_sql.py -v
```

### Prerequisites
- PostgreSQL 15+ (or Docker for containerized testing)
- Python 3.12+
- psql command-line client
- pip for installing test dependencies

### Dependencies and Mocks
- **psycopg**: PostgreSQL driver for Python tests
- **testcontainers**: Optional, for isolated database testing (auto-creates PostgreSQL container)
- No mocks required - tests run against real PostgreSQL

### Product Owner Notes
- Schema follows SPEC data model exactly
- All timestamps use UTC timezone
- Seed data includes realistic test scenarios (completed surveys, refused contacts, etc.)
- Migration versioning uses simple V0001 format for clarity

### RAG Citations
- SPEC.md: Data Model section for entity definitions
- PLAN.md: REQ-001 KIT Readiness section for path structure
- TECH_CONSTRAINTS.yaml: PostgreSQL 15+, migration strategy guidance
- docs/harper/lane-guides/python.md: Testing tools and patterns

```json
{
  "index": [
    {
      "req": "REQ-001",
      "src": [
        "runs/kit/REQ-001/src/storage/sql/V0001.up.sql",
        "runs/kit/REQ-001/src/storage/sql/V0001.down.sql",
        "runs/kit/REQ-001/src/storage/seed/seed.sql",
        "runs/kit/REQ-001/scripts/db_upgrade.sh",
        "runs/kit/REQ-001/scripts/db_downgrade.sh",
        "runs/kit/REQ-001/scripts/db_seed.sh"
      ],
      "tests": [
        "runs/kit/REQ-001/test/test_migration_sql.py"
      ]
    }
  ]
}