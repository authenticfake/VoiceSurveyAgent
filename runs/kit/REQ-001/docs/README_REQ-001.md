# REQ-001: Database Schema and Migrations

## Overview

This module provides the foundational database schema for the voicesurveyagent system. It implements all entities from the SPEC data model using PostgreSQL with proper constraints, indexes, and enum types.

## Quick Start

bash
# Set database URL
export DATABASE_URL='postgresql://user:password@localhost:5432/voicesurvey'

# Apply migrations
./runs/kit/REQ-001/scripts/db_upgrade.sh

# Apply seed data
./runs/kit/REQ-001/scripts/db_seed.sh

# Run tests
pytest runs/kit/REQ-001/test/ -v

## Schema Overview

The schema includes 11 tables covering:

- **Authentication**: users
- **Campaigns**: campaigns, email_templates
- **Contacts**: contacts, exclusion_list_entries
- **Calls**: call_attempts, survey_responses, transcript_snippets
- **Events**: events, email_notifications
- **Configuration**: provider_configs

## Migration Strategy

Migrations use raw SQL files with versioned naming:
- `V0001.up.sql` - Apply changes
- `V0001.down.sql` - Rollback changes

All migrations are idempotent using `IF NOT EXISTS` and `IF EXISTS` clauses.

## Seed Data

The seed file includes:
- 3 users (admin, campaign_manager, viewer)
- 6 email templates (EN/IT for each type)
- 1 provider config
- 1 sample campaign
- 5 sample contacts
- 2 exclusion list entries

## Testing

Tests validate:
- Schema shape (tables, enums, indexes)
- Migration idempotency
- Round-trip migrations (up → down → up)
- Constraint enforcement

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-001**: Database schema and migrations

### Rationale
REQ-001 is the foundation requirement with no dependencies. All other REQs depend on it for database models and schema.

### In Scope
- All 11 entities from SPEC data model
- 13 enum types for status/type fields
- UUID primary keys using PostgreSQL native type
- Indexes on all foreign key columns
- Idempotent migrations (IF NOT EXISTS/IF EXISTS)
- Seed data with 10-20 records
- Migration scripts (upgrade/downgrade/seed)
- Shape validation tests

### Out of Scope
- Alembic integration (using raw SQL per PLAN guidance)
- ORM models (will be added in dependent REQs)
- Application code

### How to Run Tests

bash
# Option 1: With testcontainers (requires Docker)
pip install -r runs/kit/REQ-001/requirements.txt
pytest runs/kit/REQ-001/test/ -v

# Option 2: With local PostgreSQL
export DATABASE_URL='postgresql://user:password@localhost:5432/voicesurvey_test'
pip install -r runs/kit/REQ-001/requirements.txt
pytest runs/kit/REQ-001/test/ -v

### Prerequisites
- PostgreSQL 15+ (local or Docker)
- Python 3.12+
- psql CLI in PATH
- Docker (optional, for testcontainers)

### Dependencies and Mocks
- **psycopg2-binary**: PostgreSQL driver for tests
- **testcontainers**: Optional, provides isolated PostgreSQL container for testing
- No mocks required - tests run against real PostgreSQL

### Product Owner Notes
- Schema follows SPEC data model exactly
- All timestamp columns use UTC timezone (TIMESTAMP WITH TIME ZONE)
- Trigger function auto-updates `updated_at` columns
- Seed data includes realistic sample campaign with contacts

### RAG Citations
- Used SPEC.md Data Model section for entity definitions
- Used PLAN.md REQ-001 acceptance criteria for validation requirements
- Used TECH_CONSTRAINTS.yaml for PostgreSQL version and migration strategy

### Index

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