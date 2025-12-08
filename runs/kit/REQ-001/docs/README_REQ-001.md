# REQ-001: Database Schema and Migrations

## Quick Start

bash
# Set database URL
export DATABASE_URL='postgresql://user:pass@localhost:5432/voicesurvey'

# Apply migrations
./runs/kit/REQ-001/scripts/db_upgrade.sh

# Apply seed data
./runs/kit/REQ-001/scripts/db_seed.sh

# Run tests
pip install -r runs/kit/REQ-001/requirements.txt
pytest runs/kit/REQ-001/test/ -v

## Files

| File | Purpose |
|------|---------|
| `src/storage/sql/V0001.up.sql` | Creates all tables, indexes, and triggers |
| `src/storage/sql/V0001.down.sql` | Drops all objects in reverse order |
| `src/storage/seed/seed.sql` | Idempotent seed data (10-20 records) |
| `scripts/db_upgrade.sh` | Runs all up migrations |
| `scripts/db_downgrade.sh` | Runs all down migrations |
| `scripts/db_seed.sh` | Applies seed data |
| `test/test_migration_sql.py` | Migration validation tests |

## Testing

Tests validate:
- All expected tables are created
- All enum types exist
- UUID primary keys are used
- Foreign key indexes exist
- Migrations are idempotent
- Round-trip (up/down/up) works correctly
- Seed data applies successfully

## See Also

- [KIT Documentation](docs/KIT_REQ-001.md) - Detailed implementation notes
- [HOWTO](ci/HOWTO.md) - Execution guide for different environments

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-001**: Database schema and migrations

### Rationale
REQ-001 is the foundation requirement with no dependencies. It must be completed first as all other REQs depend on the database schema being in place.

### In Scope
- All 11 entity tables from SPEC data model
- 13 enum types for status and type fields
- UUID primary keys using PostgreSQL native type
- Foreign key indexes for query performance
- Idempotent up/down migrations
- Seed data with 10-20 records
- Shell scripts for migration execution
- Comprehensive test suite

### Out of Scope
- Alembic Python integration (raw SQL used for portability)
- Application ORM models (separate REQ)
- Data retention automation (REQ-022)

### How to Run Tests
bash
# Install dependencies
pip install -r runs/kit/REQ-001/requirements.txt

# Option 1: With testcontainers (recommended)
pytest runs/kit/REQ-001/test/ -v

# Option 2: With local PostgreSQL
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/voicesurvey_test'
export DISABLE_TESTCONTAINERS=1
pytest runs/kit/REQ-001/test/ -v

### Prerequisites
- PostgreSQL 15+ (or Docker for testcontainers)
- Python 3.12+
- psql CLI tool
- Docker (optional, for testcontainers)

### Dependencies and Mocks
- **testcontainers**: Used to spin up ephemeral PostgreSQL for testing
- **psycopg**: PostgreSQL driver for Python
- No mocks required - tests run against real PostgreSQL

### Product Owner Notes
- Schema follows SPEC data model exactly
- All timestamps use UTC timezone (TIMESTAMP WITH TIME ZONE)
- Seed data includes 3 users, 6 email templates, 1 campaign, 5 contacts, 2 exclusion entries
- Migration scripts are POSIX-compliant shell scripts

### RAG Citations
- SPEC.md: Data Model section for entity definitions
- PLAN.md: REQ-001 acceptance criteria and KIT readiness
- TECH_CONSTRAINTS.yaml: PostgreSQL version and migration strategy

json
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
      ]
    }
  ]
}

Human: