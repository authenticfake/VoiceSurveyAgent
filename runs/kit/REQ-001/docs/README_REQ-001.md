# REQ-001: Database Schema and Migrations

## Quick Start

```bash
# Install dependencies
pip install -r runs/kit/REQ-001/requirements.txt

# Set database URL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey"

# Apply migrations
./runs/kit/REQ-001/scripts/db_upgrade.sh

# Apply seed data
./runs/kit/REQ-001/scripts/db_seed.sh

# Run tests
pytest -v runs/kit/REQ-001/test/
```

## What This Implements

- Complete database schema for voicesurveyagent
- 11 tables matching SPEC data model
- 13 PostgreSQL enum types
- Comprehensive indexing for query performance
- Idempotent migrations with rollback support
- Seed data for development/testing

## Key Files

| File | Purpose |
|------|---------|
| `src/storage/sql/V0001.up.sql` | Create all tables and types |
| `src/storage/sql/V0001.down.sql` | Drop all objects |
| `src/storage/seed/seed.sql` | Development seed data |
| `test/test_migration_sql.py` | Schema validation tests |

## See Also

- [Full Documentation](./KIT_REQ-001.md)
- [Execution Guide](../ci/HOWTO.md)
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-001**: Database schema and migrations

### Rationale
REQ-001 is the foundation requirement with no dependencies. It must be completed first as REQ-002, REQ-009, REQ-011, and REQ-021 all depend on it.

### In Scope
- All 11 entities from SPEC data model
- PostgreSQL enum types for all status/type fields
- UUID primary keys using native PostgreSQL type
- Timezone-aware timestamp columns
- Foreign key indexes for query performance
- Idempotent up/down migrations
- Seed data (10-20 records)
- Shape tests, idempotency tests, round-trip tests

### Out of Scope
- Alembic Python configuration (pure SQL migrations per system prompt)
- ORM models (will be created in dependent REQs)
- Application code

### How to Run Tests

```bash
# Option 1: With Docker (testcontainers)
pip install -r runs/kit/REQ-001/requirements.txt
pytest -v runs/kit/REQ-001/test/test_migration_sql.py

# Option 2: With external database
export DATABASE_URL="postgresql://user:pass@localhost:5432/testdb"
export DISABLE_TESTCONTAINERS=1
pytest -v runs/kit/REQ-001/test/test_migration_sql.py
```

### Prerequisites
- PostgreSQL 15+ (local or Docker)
- Python 3.12+
- psql CLI for manual operations
- Docker (optional, for testcontainers)

### Dependencies and Mocks
- **psycopg2-binary**: PostgreSQL driver for tests
- **testcontainers**: Spins up ephemeral PostgreSQL container for isolated testing
- No mocks required - tests run against real PostgreSQL

### Product Owner Notes
- Schema follows SPEC data model exactly
- All enum values match SPEC definitions
- Seed data includes realistic sample campaign with 5 contacts
- Migrations are pure SQL for portability and auditability

### RAG Citations
- SPEC.md: Data Model section for entity definitions
- PLAN.md: REQ-001 acceptance criteria
- plan.json: Lane (python), track (Infra), dependencies (none)
- TECH_CONSTRAINTS.yaml: PostgreSQL as database, Alembic-compatible migrations

```json
{
  "index": [
    {
      "req": "REQ-001",
      "src": [
        "runs/kit/REQ-001/src/storage/sql/V0001.up.sql",
        "runs/kit/REQ-001/src/storage/sql/V0001.down.sql",
        "runs/kit/REQ-001/src/storage/seed/seed.sql"
      ],
      "tests": [
        "runs/kit/REQ-001/test/test_migration_sql.py"
      ],
      "scripts": [
        "runs/kit/REQ-001/scripts/db_upgrade.sh",
        "runs/kit/REQ-001/scripts/db_downgrade.sh",
        "runs/kit/REQ-001/scripts/db_seed.sh"
      ],
      "docs": [
        "runs/kit/REQ-001/docs/KIT_REQ-001.md",
        "runs/kit/REQ-001/docs/README_REQ-001.md",
        "runs/kit/REQ-001/ci/HOWTO.md"
      ],
      "ci": [
        "runs/kit/REQ-001/ci/LTC.json"
      ]
    }
  ]
}