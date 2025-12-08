# KIT Documentation — REQ-001: Database Schema and Migrations

## Overview

This KIT implements the foundational database schema for the Voice Survey Agent system. It includes all entity models defined in the SPEC, Alembic migrations for PostgreSQL, and comprehensive tests.

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| All entities from SPEC data model have corresponding Alembic migrations | ✅ |
| Migrations are idempotent and can be run multiple times without error | ✅ |
| Foreign key columns have appropriate indexes for query performance | ✅ |
| Enum types are created for all status and type fields | ✅ |
| UUID primary keys use PostgreSQL native UUID type | ✅ |

## Entities Implemented

1. **User** - Authenticated users with OIDC integration
2. **Campaign** - Survey campaign configuration
3. **Contact** - Survey target contacts
4. **ExclusionListEntry** - Do-not-call list entries
5. **CallAttempt** - Individual call attempt records
6. **SurveyResponse** - Completed survey answers
7. **Event** - Survey lifecycle events
8. **EmailNotification** - Email delivery tracking
9. **EmailTemplate** - Email templates for notifications
10. **ProviderConfig** - Telephony and LLM provider settings
11. **TranscriptSnippet** - Call transcript storage

## Enum Types

- `user_role`: admin, campaign_manager, viewer
- `campaign_status`: draft, scheduled, running, paused, completed, cancelled
- `language_code`: en, it
- `question_type`: free_text, numeric, scale
- `contact_state`: pending, in_progress, completed, refused, not_reached, excluded
- `contact_language`: en, it, auto
- `call_outcome`: completed, refused, no_answer, busy, failed
- `exclusion_source`: import, api, manual
- `event_type`: survey.completed, survey.refused, survey.not_reached
- `email_status`: pending, sent, failed
- `email_template_type`: completed, refused, not_reached
- `provider_type`: telephony_api, voice_ai_platform
- `llm_provider`: openai, anthropic, azure-openai, google

## Key Design Decisions

1. **UUID Primary Keys**: All entities use PostgreSQL native UUID type for distributed-friendly identifiers
2. **Timezone-aware Timestamps**: All datetime columns use `timezone=True` for UTC storage
3. **Composite Indexes**: Scheduler-optimized index on contacts table for efficient query patterns
4. **Cascade Deletes**: Appropriate ON DELETE actions for referential integrity
5. **Idempotent Migrations**: All migrations use `DO $$ BEGIN ... EXCEPTION ... END $$` pattern for enum creation

## Dependencies

This REQ has no dependencies and serves as the foundation for:
- REQ-002: OIDC authentication integration
- REQ-009: Telephony provider adapter interface
- REQ-011: LLM gateway integration
- REQ-021: Observability instrumentation