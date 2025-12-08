# KIT Documentation: REQ-001 - Database Schema and Migrations

## Overview

This KIT implements the foundational database schema for the voicesurveyagent system, including all entities defined in the SPEC data model.

## Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All entities from SPEC data model have corresponding migrations | ✅ | V0001.up.sql contains all 11 tables |
| Migrations are idempotent | ✅ | Uses IF NOT EXISTS, tested in TestIdempotency |
| Foreign key columns have indexes | ✅ | Verified in test_foreign_key_indexes |
| Enum types created for all status/type fields | ✅ | 13 enum types created |
| UUID primary keys use PostgreSQL native type | ✅ | Verified in test_uuid_primary_keys |

## Schema Summary

### Tables (11)
1. `users` - System users with OIDC integration
2. `email_templates` - Email templates for notifications
3. `campaigns` - Survey campaign configurations
4. `contacts` - Campaign contact lists
5. `exclusion_list_entries` - Do-not-call list
6. `call_attempts` - Individual call attempt records
7. `survey_responses` - Completed survey answers
8. `events` - Domain events for async processing
9. `email_notifications` - Email delivery tracking
10. `provider_configs` - Telephony/LLM provider settings
11. `transcript_snippets` - Call transcript storage

### Enum Types (13)
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

1. **UUID Primary Keys**: All tables use PostgreSQL native UUID type with uuid-ossp extension for generation.

2. **Timestamp Handling**: All timestamps use `TIMESTAMP WITH TIME ZONE` for proper timezone support.

3. **Automatic updated_at**: Trigger function `update_updated_at_column()` automatically updates `updated_at` on row changes.

4. **Cascade Deletes**: Child records cascade delete with parent (e.g., contacts deleted when campaign deleted).

5. **Index Strategy**: Indexes on all foreign keys plus commonly queried columns (status, state, phone_number).

## Dependencies

- PostgreSQL 15+ with uuid-ossp extension
- No application code dependencies (pure SQL)

## Future Considerations

- Add partitioning for `call_attempts` and `events` tables if volume grows
- Consider adding `deleted_at` for soft deletes on campaigns
- May need composite indexes for scheduler queries