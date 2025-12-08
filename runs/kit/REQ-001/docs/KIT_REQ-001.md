# KIT Documentation — REQ-001: Database Schema and Migrations

## Overview

This KIT implements the foundational database schema for the Voice Survey Agent system, including all entity tables, enum types, indexes, and constraints as specified in the SPEC data model.

## Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All entities from SPEC data model have corresponding Alembic migrations | ✅ | 13 migration files in `migrations/versions/` |
| Migrations are idempotent and can be run multiple times without error | ✅ | `TestIdempotency` test class |
| Foreign key columns have appropriate indexes for query performance | ✅ | `test_foreign_key_indexes` test |
| Enum types are created for all status and type fields | ✅ | `test_all_enums_created` test |
| UUID primary keys use PostgreSQL native UUID type | ✅ | `test_uuid_primary_keys` test |

## Architecture

### Schema Design

The schema follows the SPEC data model with these key design decisions:

1. **UUID Primary Keys**: All tables use PostgreSQL native UUID type with `uuid_generate_v4()` default
2. **Enum Types**: All status and type fields use PostgreSQL ENUM types for type safety
3. **Timestamps**: All tables with mutable data have `created_at` and `updated_at` with automatic triggers
4. **Indexes**: Foreign keys and frequently queried columns are indexed
5. **Constraints**: Check constraints enforce business rules (e.g., `max_attempts` between 1-5)

### Entity Relationships

users
  └── campaigns (created_by_user_id)
        ├── contacts (campaign_id)
        │     ├── call_attempts (contact_id)
        │     │     ├── survey_responses (call_attempt_id)
        │     │     ├── events (call_attempt_id)
        │     │     └── transcript_snippets (call_attempt_id)
        │     └── email_notifications (contact_id)
        └── email_templates (email_*_template_id)

exclusion_list_entries (standalone)
provider_configs (standalone, single row)

## Files Produced

### SQL Migrations
- `src/storage/sql/V0001.up.sql` — Complete schema creation
- `src/storage/sql/V0001.down.sql` — Complete schema teardown

### Alembic Migrations
- `src/data/migrations/migrations/versions/V0001_create_enums.py`
- `src/data/migrations/migrations/versions/V0002_create_users_table.py`
- `src/data/migrations/migrations/versions/V0003_create_email_templates_table.py`
- `src/data/migrations/migrations/versions/V0004_create_campaigns_table.py`
- `src/data/migrations/migrations/versions/V0005_create_contacts_table.py`
- `src/data/migrations/migrations/versions/V0006_create_exclusion_list_entries_table.py`
- `src/data/migrations/migrations/versions/V0007_create_call_attempts_table.py`
- `src/data/migrations/migrations/versions/V0008_create_survey_responses_table.py`
- `src/data/migrations/migrations/versions/V0009_create_events_table.py`
- `src/data/migrations/migrations/versions/V0010_create_email_notifications_table.py`
- `src/data/migrations/migrations/versions/V0011_create_provider_configs_table.py`
- `src/data/migrations/migrations/versions/V0012_create_transcript_snippets_table.py`
- `src/data/migrations/migrations/versions/V0013_create_triggers.py`

### SQLAlchemy Models
- `src/app/shared/models/` — All entity models with relationships

### Seed Data
- `src/storage/seed/seed.sql` — 17 seed records (3 users, 4 templates, 1 config, 1 campaign, 5 contacts, 3 exclusions)

## Testing

### Test Coverage

| Test Class | Purpose | Tests |
|------------|---------|-------|
| `TestSchemaShape` | Verify schema matches SPEC | 4 tests |
| `TestIdempotency` | Verify migrations are repeatable | 2 tests |
| `TestRoundTrip` | Verify upgrade/downgrade cycle | 2 tests |
| `TestSeedData` | Verify seed data validity | 3 tests |

### Running Tests

bash
# With testcontainers (recommended)
pytest runs/kit/REQ-001/test/test_migration_sql.py -v

# Without testcontainers
DISABLE_TESTCONTAINERS=1 DATABASE_URL=postgresql://... pytest runs/kit/REQ-001/test/test_migration_sql.py -v

## Dependencies

### Runtime
- `sqlalchemy>=2.0.0`
- `asyncpg>=0.29.0`
- `alembic>=1.13.0`

### Testing
- `pytest>=8.0.0`
- `psycopg2-binary>=2.9.0`
- `testcontainers>=4.0.0`

## Notes

1. The `provider_configs` table is designed for single-row configuration but supports multiple rows for future multi-tenant scenarios
2. Transcript snippets are optional for slice-1 but the table is created for future use
3. All timestamps use `TIMESTAMP WITH TIME ZONE` for proper timezone handling
4. The `updated_at` trigger function is shared across all tables with mutable data