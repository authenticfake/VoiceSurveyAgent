# REQ-001: Database Schema and Migrations

## Quick Start

```bash
# Start PostgreSQL
docker run -d --name voicesurvey-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey_test \
  -p 5432:5432 postgres:15-alpine

# Set environment
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"

# Run migrations
./runs/kit/REQ-001/scripts/db_upgrade.sh
./runs/kit/REQ-001/scripts/db_seed.sh

# Run tests
pip install -r runs/kit/REQ-001/requirements.txt
pytest runs/kit/REQ-001/test/ -v
```

## What This Implements

- Complete database schema for voicesurveyagent
- All 11 tables from SPEC data model
- 13 PostgreSQL enum types for type safety
- Idempotent migrations (safe to re-run)
- Seed data with 10-20 sample records
- Comprehensive test suite

## Key Design Decisions

1. **UUID Primary Keys**: All tables use PostgreSQL native UUID type with uuid_generate_v4()
2. **Enum Types**: All status and type fields use PostgreSQL enums for type safety
3. **Indexes**: All foreign key columns and frequently queried columns are indexed
4. **Triggers**: Automatic updated_at timestamp management
5. **Idempotency**: All DDL uses IF NOT EXISTS / IF EXISTS for safe re-runs

## Next Steps

This schema is the foundation for:
- REQ-002: OIDC authentication (uses `users` table)
- REQ-009: Telephony adapter (uses `provider_configs` table)
- REQ-011: LLM gateway (uses `provider_configs` table)
- REQ-021: Observability (uses all tables for metrics)
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-001**: Database schema and migrations

### Rationale
REQ-001 is the foundation requirement with no dependencies. All other REQs depend on this schema being in place.

### In Scope
- All 11 tables from SPEC data model
- 13 PostgreSQL enum types
- Indexes on foreign keys and frequently queried columns
- Idempotent up/down migrations
- Seed data (10-20 records)
- Shell scripts for migration management
- Comprehensive test suite

### Out of Scope
- Alembic integration (using raw SQL for portability)
- ORM models (will be added in dependent REQs)
- Application code

### How to Run Tests

```bash
# Prerequisites
docker run -d --name voicesurvey-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voicesurvey_test \
  -p 5432:5432 postgres:15-alpine

sleep 5

# Install and run
pip install -r runs/kit/REQ-001/requirements.txt
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
chmod +x runs/kit/REQ-001/scripts/*.sh
./runs/kit/REQ-001/scripts/db_upgrade.sh
./runs/kit/REQ-001/scripts/db_seed.sh
pytest runs/kit/REQ-001/test/ -v

# Cleanup
docker stop voicesurvey-postgres && docker rm voicesurvey-postgres
```

### Prerequisites
- Docker for PostgreSQL container
- Python 3.12+
- psql CLI (for shell scripts)
- pip for dependencies

### Dependencies and Mocks
- No mocks required - tests run against real PostgreSQL
- psycopg2-binary for database connectivity
- pytest for test framework

### Product Owner Notes
- Schema follows SPEC data model exactly
- All enum values match SPEC definitions
- Seed data includes realistic sample campaign with 5 contacts
- Exclusion list seeded with 2 entries for testing DNC functionality

### RAG Citations
- SPEC.md: Data Model section for entity definitions
- PLAN.md: REQ-001 acceptance criteria
- plan.json: Lane (python) and track (Infra) information

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
```
Human: continue