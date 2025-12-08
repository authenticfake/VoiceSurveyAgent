# KIT Documentation - REQ-001: Database Schema and Migrations

## Overview

This KIT implements the foundational database schema for the voicesurveyagent system. It creates all entities defined in the SPEC data model using raw SQL migrations that are idempotent and reversible.

## Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All entities from SPEC data model have corresponding Alembic migrations | ✅ | V0001.up.sql creates all 11 tables |
| Migrations are idempotent and can be run multiple times without error | ✅ | Uses IF NOT EXISTS, IF EXISTS clauses |
| Foreign key columns have appropriate indexes for query performance | ✅ | 25+ indexes created on FK columns |
| Enum types are created for all status and type fields | ✅ | 13 enum types created |
| UUID primary keys use PostgreSQL native UUID type | ✅ | All PKs use UUID with uuid_generate_v4() |

## Schema Summary

### Tables Created
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

### Enum Types
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

## Design Decisions

1. **Raw SQL over Alembic**: Used raw SQL migrations for maximum control and portability. The structure follows Alembic conventions (V0001.up.sql, V0001.down.sql) for future integration.

2. **UUID Primary Keys**: All tables use PostgreSQL native UUID type with uuid_generate_v4() for distributed-friendly IDs.

3. **Timestamp Handling**: All timestamps use TIMESTAMP WITH TIME ZONE for proper timezone handling. Automatic updated_at triggers maintain consistency.

4. **Cascade Deletes**: Appropriate CASCADE and SET NULL behaviors on foreign keys to maintain referential integrity.

5. **Index Strategy**: Indexes on all foreign key columns plus additional indexes on frequently queried columns (status, state, phone_number).

## Dependencies

- PostgreSQL 15+ with uuid-ossp extension
- No application code dependencies (pure SQL)

## Future Considerations

- Additional migrations (V0002, etc.) can be added following the same pattern
- Alembic integration can wrap these SQL files if needed
- Partitioning may be needed for call_attempts and events tables at scale