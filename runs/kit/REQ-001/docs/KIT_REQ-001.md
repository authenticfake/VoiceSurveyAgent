# KIT Documentation: REQ-001 - Database Schema and Migrations

## Summary

This KIT implements the foundational database schema for the voicesurveyagent system. It creates all entities defined in the SPEC data model using PostgreSQL-native features including UUID primary keys, enum types, and proper indexing for foreign keys.

## Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All entities from SPEC data model have corresponding Alembic migrations | ✅ | V0001.up.sql contains all 11 entities |
| Migrations are idempotent and can be run multiple times without error | ✅ | `CREATE IF NOT EXISTS` and `DROP IF EXISTS` used throughout |
| Foreign key columns have appropriate indexes for query performance | ✅ | 20+ indexes created for FK columns |
| Enum types are created for all status and type fields | ✅ | 13 enum types created |
| UUID primary keys use PostgreSQL native UUID type | ✅ | All tables use `UUID PRIMARY KEY DEFAULT uuid_generate_v4()` |

## Schema Overview

### Tables Created (11)
1. `users` - System users with OIDC integration
2. `email_templates` - Email templates for notifications
3. `campaigns` - Survey campaign configurations
4. `contacts` - Contact records per campaign
5. `exclusion_list_entries` - Do-not-call list
6. `call_attempts` - Individual call attempt records
7. `survey_responses` - Captured survey answers
8. `events` - Domain events for async processing
9. `email_notifications` - Email delivery tracking
10. `provider_configs` - Telephony/LLM provider settings
11. `transcript_snippets` - Call transcript storage

### Enum Types Created (13)
- `user_role`: admin, campaign_manager, viewer
- `campaign_status`: draft, scheduled, running, paused, completed, cancelled
- `campaign_language`: en, it
- `question_type`: free_text, numeric, scale
- `contact_state`: pending, in_progress, completed, refused, not_reached, excluded
- `contact_language`: en, it, auto
- `contact_outcome`: completed, refused, no_answer, busy, failed
- `exclusion_source`: import, api, manual
- `event_type`: survey.completed, survey.refused, survey.not_reached
- `email_status`: pending, sent, failed
- `email_template_type`: completed, refused, not_reached
- `provider_type`: telephony_api, voice_ai_platform
- `llm_provider`: openai, anthropic, azure-openai, google

### Key Design Decisions

1. **UUID Primary Keys**: All tables use PostgreSQL native UUID type with `uuid_generate_v4()` for distributed-friendly IDs.

2. **Timezone-Aware Timestamps**: All timestamp columns use `TIMESTAMP WITH TIME ZONE` and default to UTC via `NOW()`.

3. **Automatic updated_at**: Trigger function `update_updated_at_column()` automatically updates `updated_at` on row modifications.

4. **Comprehensive Indexing**: Indexes created for:
   - All foreign key columns
   - Frequently queried columns (status, state, phone_number)
   - Composite indexes for scheduler queries

5. **Constraint Enforcement**:
   - `max_attempts` constrained to 1-5
   - Confidence scores constrained to 0-1
   - Unique constraints on phone numbers in exclusion list

## File Structure

```
runs/kit/REQ-001/
├── src/
│   └── storage/
│       ├── sql/
│       │   ├── V0001.up.sql      # Create schema
│       │   └── V0001.down.sql    # Drop schema
│       └── seed/
│           └── seed.sql          # Idempotent seed data
├── scripts/
│   ├── db_upgrade.sh             # Apply migrations
│   ├── db_downgrade.sh           # Rollback migrations
│   └── db_seed.sh                # Apply seed data
├── test/
│   └── test_migration_sql.py     # Schema validation tests
├── ci/
│   ├── LTC.json                  # Test contract
│   └── HOWTO.md                  # Execution guide
├── docs/
│   ├── KIT_REQ-001.md           # This file
│   └── README_REQ-001.md        # Quick reference
└── requirements.txt              # Test dependencies
```

## Dependencies

- **Upstream**: None (foundation REQ)
- **Downstream**: REQ-002, REQ-009, REQ-011, REQ-021 depend on this schema

## Testing

Tests validate:
1. All expected tables are created
2. All enum types exist
3. UUID primary keys are used
4. Timestamps are timezone-aware
5. Foreign key indexes exist
6. Migrations are idempotent
7. Round-trip (upgrade → downgrade → upgrade) works
8. Seed data is idempotent
9. Constraints are enforced

## Notes

- Seed data includes 3 users, 6 email templates, 1 provider config, 1 campaign, and 5 contacts
- The `uuid-ossp` extension is enabled for UUID generation
- All `DROP` statements use `CASCADE` to handle dependencies
- The schema is designed for single-tenant deployment per SPEC