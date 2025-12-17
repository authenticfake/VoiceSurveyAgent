# KIT Documentation: REQ-001 - Database Schema and Migrations

## Summary

REQ-001 implements the foundational database schema for the voicesurveyagent system. This includes all entities defined in the SPEC data model, with proper enum types, UUID primary keys, foreign key indexes, and idempotent migration scripts.

## Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All entities from SPEC data model have corresponding Alembic migrations | ✅ PASS | V0001.up.sql creates all 12 tables |
| Migrations are idempotent and can be run multiple times without error | ✅ PASS | Uses IF NOT EXISTS / IF EXISTS checks |
| Foreign key columns have appropriate indexes for query performance | ✅ PASS | 25+ indexes created on FK columns |
| Enum types are created for all status and type fields | ✅ PASS | 15 enum types created |
| UUID primary keys use PostgreSQL native UUID type | ✅ PASS | All id columns use UUID type |

## Implementation Details

### Files Created

| Path | Purpose |
|------|---------|
| `src/storage/sql/V0001.up.sql` | Initial schema migration (upgrade) |
| `src/storage/sql/V0001.down.sql` | Schema rollback (downgrade) |
| `src/storage/seed/seed.sql` | Idempotent seed data (10-20 records) |
| `scripts/db_upgrade.sh` | Shell script to run upgrades |
| `scripts/db_downgrade.sh` | Shell script to run downgrades |
| `scripts/db_seed.sh` | Shell script to run seed |
| `test/test_migration_sql.py` | Comprehensive migration tests |

### Schema Design Decisions

1. **UUID Primary Keys**: All tables use PostgreSQL native UUID type via `uuid-ossp` extension for globally unique identifiers.

2. **Enum Types**: 15 enum types created for type safety:
   - User roles: `admin`, `campaign_manager`, `viewer`
   - Campaign status: `draft`, `scheduled`, `running`, `paused`, `completed`, `cancelled`
   - Contact states: `pending`, `in_progress`, `completed`, `refused`, `not_reached`, `excluded`

3. **Timestamp Handling**: All timestamp columns use `TIMESTAMP WITH TIME ZONE` and default to `NOW()` for UTC consistency.

4. **Automatic updated_at**: Trigger function `update_updated_at_column()` automatically updates `updated_at` on row modifications.

5. **Foreign Key Indexes**: All foreign key columns have dedicated indexes for query performance.

6. **Idempotency**: All DDL statements use `IF NOT EXISTS` / `IF EXISTS` checks for safe re-runs.

### Entity Relationships

```
users ─────────────────┐
                       │
email_templates ───────┼──► campaigns ◄──── contacts
                       │         │              │
                       │         │              │
                       │         ▼              ▼
                       │    call_attempts ◄─────┘
                       │         │
                       │         ▼
                       │    survey_responses
                       │         │
                       │         ▼
                       └───► events ──► email_notifications

provider_configs (standalone)
exclusion_list_entries (standalone)
transcript_snippets ──► call_attempts
```

## Test Coverage

### Test Classes

1. **TestMigrationShape**: Validates schema structure
   - All expected tables created
   - UUID primary keys
   - Enum types exist
   - Foreign key indexes present
   - Timestamp columns have timezone

2. **TestMigrationIdempotency**: Validates safe re-runs
   - Upgrade can run multiple times
   - Downgrade can run multiple times

3. **TestMigrationRoundTrip**: Validates reversibility
   - Upgrade then downgrade works correctly

4. **TestSeedData**: Validates seed script
   - Seed runs successfully
   - Seed is idempotent
   - Expected record counts created

5. **TestConstraints**: Validates data integrity
   - max_attempts constraint (1-5)
   - confidence score constraint (0-1)

6. **TestTriggers**: Validates automation
   - updated_at trigger works

## Dependencies

- PostgreSQL 15+
- psycopg[binary] >= 3.1.0
- pytest >= 8.0.0
- testcontainers >= 4.0.0 (optional)

## Usage

```bash
# Apply migrations
./scripts/db_upgrade.sh

# Apply seed data
./scripts/db_seed.sh

# Run tests
pytest test/test_migration_sql.py -v

# Rollback
./scripts/db_downgrade.sh