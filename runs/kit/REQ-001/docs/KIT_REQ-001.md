# KIT Documentation - REQ-001: Database Schema and Migrations

## Overview

This KIT implements the foundational database schema for the voicesurveyagent system, including all entities defined in the SPEC data model.

## Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All entities from SPEC data model have corresponding migrations | ✅ | V0001.up.sql contains all 11 tables |
| Migrations are idempotent | ✅ | Uses IF NOT EXISTS, IF EXISTS clauses |
| Foreign key columns have appropriate indexes | ✅ | All FK columns indexed |
| Enum types created for all status/type fields | ✅ | 13 enum types created |
| UUID primary keys use PostgreSQL native UUID type | ✅ | All PKs use uuid_generate_v4() |

## Schema Summary

### Tables (11)
1. `users` - System users with OIDC integration
2. `email_templates` - Email templates for notifications
3. `campaigns` - Survey campaigns with configuration
4. `contacts` - Campaign contacts with state tracking
5. `exclusion_list_entries` - Do-not-call list
6. `call_attempts` - Individual call attempt records
7. `survey_responses` - Captured survey answers
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

## Dependencies

- PostgreSQL 15+ with uuid-ossp extension
- psycopg2-binary for Python tests

## Files

| File | Purpose |
|------|---------|
| `src/storage/sql/V0001.up.sql` | Schema creation |
| `src/storage/sql/V0001.down.sql` | Schema rollback |
| `src/storage/seed/seed.sql` | Idempotent seed data |
| `scripts/db_upgrade.sh` | Apply migrations |
| `scripts/db_downgrade.sh` | Rollback migrations |
| `scripts/db_seed.sh` | Apply seed data |
| `test/test_migration_sql.py` | Schema validation tests |