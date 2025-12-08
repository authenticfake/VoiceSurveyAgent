# REQ-001: Database Schema and Migrations

## Quick Start

bash
# Install dependencies
pip install -r runs/kit/REQ-001/requirements.txt

# Run tests
pytest runs/kit/REQ-001/test/test_migration_sql.py -v

# Apply migrations manually
./runs/kit/REQ-001/scripts/db_upgrade.sh

## What This Implements

- Complete PostgreSQL schema for Voice Survey Agent
- 11 entity tables matching SPEC data model
- 13 enum types for type-safe status fields
- Alembic migrations for version control
- SQLAlchemy ORM models
- Idempotent seed data (17 records)

## Key Files

| File | Purpose |
|------|---------|
| `src/storage/sql/V0001.up.sql` | Main schema DDL |
| `src/storage/seed/seed.sql` | Test/dev seed data |
| `src/app/shared/models/` | SQLAlchemy models |
| `test/test_migration_sql.py` | Schema validation tests |

## Environment Variables

bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=voicesurveyagent
DB_USER=postgres
DB_PASSWORD=postgres

See [HOWTO.md](ci/HOWTO.md) for detailed instructions.

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-001**: Database schema and migrations

### Rationale
REQ-001 is the foundation for all other requirements. It has no dependencies and must be completed first to enable REQ-002 (authentication), REQ-009 (telephony), REQ-011 (LLM), and REQ-021 (observability).

### In Scope
- All 11 entity tables from SPEC data model
- All 13 enum types
- UUID primary keys with PostgreSQL native type
- Foreign key indexes for query performance
- Timestamp columns with UTC timezone defaults
- Idempotent migrations (CREATE IF NOT EXISTS, DO $$ BEGIN...EXCEPTION)
- Migration rollback scripts
- SQLAlchemy ORM models
- Seed data (10-20 records)
- Shell scripts for manual migration execution
- Comprehensive test suite

### Out of Scope
- Application logic
- API endpoints
- Authentication/authorization
- Business validation rules beyond schema constraints

### How to Run Tests

bash
# Install dependencies
pip install -r runs/kit/REQ-001/requirements.txt

# Run with testcontainers (recommended)
pytest -p no:cacheprovider -q runs/kit/REQ-001/test/test_migration_sql.py -v

# Run without testcontainers
export DISABLE_TESTCONTAINERS=1
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/voicesurveyagent
pytest -p no:cacheprovider -q runs/kit/REQ-001/test/test_migration_sql.py -v

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ (local or via Docker/testcontainers)
- Docker (optional, for testcontainers)

### Dependencies and Mocks
- **psycopg2**: Used for synchronous database operations in tests
- **testcontainers**: Provides ephemeral PostgreSQL containers for isolated testing
- No mocks required; tests use real PostgreSQL instances

### Product Owner Notes
- Schema follows SPEC data model exactly
- Seed data includes realistic test scenarios
- All migrations are idempotent and reversible
- SQLAlchemy models ready for use by dependent REQs

### RAG Citations
- SPEC.md: Data Model section for entity definitions
- PLAN.md: REQ-001 acceptance criteria
- TECH_CONSTRAINTS.yaml: PostgreSQL and SQLAlchemy requirements

json
{
  "index": [
    {
      "req": "REQ-001",
      "src": [
        "runs/kit/REQ-001/src/storage/sql/V0001.up.sql",
        "runs/kit/REQ-001/src/storage/sql/V0001.down.sql",
        "runs/kit/REQ-001/src/storage/seed/seed.sql",
        "runs/kit/REQ-001/src/data/migrations/",
        "runs/kit/REQ-001/src/app/shared/models/"
      ],
      "tests": [
        "runs/kit/REQ-001/test/test_migration_sql.py"
      ]
    }
  ]
}

Human: 
Human: continue