# REQ-001: Database Schema and Migrations

## Quick Start

```bash
# Set database URL
export DATABASE_URL="postgresql://user:pass@localhost:5432/voicesurvey"

# Apply migrations
./runs/kit/REQ-001/scripts/db_upgrade.sh

# Apply seed data
./runs/kit/REQ-001/scripts/db_seed.sh

# Run tests
pip install -r runs/kit/REQ-001/requirements.txt
pytest runs/kit/REQ-001/test/ -v
```

## Files

| File | Purpose |
|------|---------|
| `src/storage/sql/V0001.up.sql` | Create all tables, indexes, triggers |
| `src/storage/sql/V0001.down.sql` | Drop all objects (rollback) |
| `src/storage/seed/seed.sql` | Sample data for development |
| `scripts/db_upgrade.sh` | Run all up migrations |
| `scripts/db_downgrade.sh` | Run all down migrations |
| `scripts/db_seed.sh` | Apply seed data |
| `test/test_migration_sql.py` | Schema validation tests |

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `DISABLE_TESTCONTAINERS` | Use local DB instead of containers | `1` |

## Testing

Tests validate:
- All expected tables exist
- All enum types exist
- UUID primary keys used
- Foreign key indexes present
- Migrations are idempotent
- Upgrade/downgrade round-trip works
- Seed data applies correctly
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-001**: Database schema and migrations

### Rationale
REQ-001 is the foundation REQ with no dependencies. It must be completed first as all other REQs depend on the database schema being in place.

### In Scope
- All 11 entity tables from SPEC data model
- 13 enum types for status and type fields
- UUID primary keys using PostgreSQL native type
- Indexes on all foreign key columns
- Automatic `updated_at` triggers
- Idempotent migration scripts (up/down)
- Seed data with 10-20 records
- Schema validation tests

### Out of Scope
- Alembic Python integration (pure SQL approach used)
- Application ORM models (separate REQ)
- Data migration between versions
- Partitioning strategies

### How to Run Tests

```bash
# Option 1: With testcontainers (Docker required)
pip install -r runs/kit/REQ-001/requirements.txt
pytest runs/kit/REQ-001/test/test_migration_sql.py -v

# Option 2: With local PostgreSQL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
export DISABLE_TESTCONTAINERS=1
pip install -r runs/kit/REQ-001/requirements.txt
pytest runs/kit/REQ-001/test/test_migration_sql.py -v
```

### Prerequisites
- PostgreSQL 15+ (local or Docker)
- Python 3.12+
- psql client installed
- Docker (optional, for testcontainers)

### Dependencies and Mocks
- **psycopg2-binary**: PostgreSQL driver for Python tests
- **testcontainers**: Optional, for automatic PostgreSQL container management
- No mocks required - tests run against real PostgreSQL

### Product Owner Notes
- Schema follows SPEC data model exactly
- All timestamps use UTC timezone (TIMESTAMP WITH TIME ZONE)
- Seed data includes 3 users, 5 email templates, 1 provider config, 1 campaign, 5 contacts, 3 exclusion entries
- Migration scripts are shell-based for simplicity; Alembic integration can be added later if needed

### RAG Citations
- SPEC.md: Data Model section for entity definitions
- PLAN.md: REQ-001 acceptance criteria and KIT readiness
- TECH_CONSTRAINTS.yaml: PostgreSQL version, migration strategy

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
      ]
    }
  ]
}
```
Human: