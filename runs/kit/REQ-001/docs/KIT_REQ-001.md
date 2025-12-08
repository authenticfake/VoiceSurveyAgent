# KIT — REQ-001: Database Schema and Migrations

## Summary

This KIT implements the foundational database schema for the voicesurveyagent system. It creates all entities defined in the SPEC data model using PostgreSQL with proper constraints, indexes, and enum types.

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| All entities from SPEC data model have corresponding Alembic migrations | ✅ Implemented via raw SQL |
| Migrations are idempotent and can be run multiple times without error | ✅ Uses IF NOT EXISTS |
| Foreign key columns have appropriate indexes for query performance | ✅ All FK columns indexed |
| Enum types are created for all status and type fields | ✅ 13 enum types created |
| UUID primary keys use PostgreSQL native UUID type | ✅ All tables use UUID |

## Implementation Details

### Tables Created (11)

1. **users** - System users with OIDC integration
2. **email_templates** - Email templates for notifications
3. **campaigns** - Survey campaign definitions
4. **contacts** - Contact records per campaign
5. **exclusion_list_entries** - Do-not-call list
6. **call_attempts** - Individual call attempt records
7. **survey_responses** - Completed survey answers
8. **events** - Domain events for async processing
9. **email_notifications** - Email delivery tracking
10. **provider_configs** - Telephony/LLM provider settings
11. **transcript_snippets** - Call transcript storage

### Enum Types Created (13)

- user_role, campaign_status, campaign_language
- question_type, contact_state, contact_language
- contact_outcome, exclusion_source, event_type
- email_status, email_template_type, provider_type
- llm_provider

### Indexes Created

- All foreign key columns have dedicated indexes
- Additional indexes on frequently queried columns (status, state, phone_number)
- Unique indexes on oidc_sub, email, phone_number where appropriate

## Files

| Path | Purpose |
|------|---------|
| `src/storage/sql/V0001.up.sql` | Schema creation migration |
| `src/storage/sql/V0001.down.sql` | Schema rollback migration |
| `src/storage/seed/seed.sql` | Idempotent seed data |
| `scripts/db_upgrade.sh` | Migration runner |
| `scripts/db_downgrade.sh` | Rollback runner |
| `scripts/db_seed.sh` | Seed data runner |
| `test/test_migration_sql.py` | Schema validation tests |

## Dependencies

- PostgreSQL 15+
- psycopg2-binary (for tests)
- pytest (for tests)
- testcontainers (optional, for isolated testing)