-- V0001.down.sql - Rollback initial schema for voicesurveyagent
-- Idempotent: uses IF EXISTS checks

-- ============================================================================
-- DROP TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_provider_configs_updated_at ON provider_configs;
DROP TRIGGER IF EXISTS update_email_notifications_updated_at ON email_notifications;
DROP TRIGGER IF EXISTS update_email_templates_updated_at ON email_templates;
DROP TRIGGER IF EXISTS update_contacts_updated_at ON contacts;
DROP TRIGGER IF EXISTS update_campaigns_updated_at ON campaigns;
DROP TRIGGER IF EXISTS update_users_updated_at ON users;

-- ============================================================================
-- DROP FUNCTION
-- ============================================================================

DROP FUNCTION IF EXISTS update_updated_at_column();

-- ============================================================================
-- DROP TABLES (reverse order of creation due to FK dependencies)
-- ============================================================================

DROP TABLE IF EXISTS transcript_snippets CASCADE;
DROP TABLE IF EXISTS provider_configs CASCADE;
DROP TABLE IF EXISTS email_notifications CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS survey_responses CASCADE;
DROP TABLE IF EXISTS call_attempts CASCADE;
DROP TABLE IF EXISTS exclusion_list_entries CASCADE;
DROP TABLE IF EXISTS contacts CASCADE;
DROP TABLE IF EXISTS campaigns CASCADE;
DROP TABLE IF EXISTS email_templates CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================================================
-- DROP ENUM TYPES
-- ============================================================================

DROP TYPE IF EXISTS transcript_language CASCADE;
DROP TYPE IF EXISTS llm_provider CASCADE;
DROP TYPE IF EXISTS provider_type CASCADE;
DROP TYPE IF EXISTS email_template_type CASCADE;
DROP TYPE IF EXISTS email_status CASCADE;
DROP TYPE IF EXISTS event_type CASCADE;
DROP TYPE IF EXISTS call_outcome CASCADE;
DROP TYPE IF EXISTS exclusion_source CASCADE;
DROP TYPE IF EXISTS contact_outcome CASCADE;
DROP TYPE IF EXISTS contact_language CASCADE;
DROP TYPE IF EXISTS contact_state CASCADE;
DROP TYPE IF EXISTS question_type CASCADE;
DROP TYPE IF EXISTS campaign_language CASCADE;
DROP TYPE IF EXISTS campaign_status CASCADE;
DROP TYPE IF EXISTS user_role CASCADE;

-- ============================================================================
-- REMOVE MIGRATION RECORD
-- ============================================================================

DELETE FROM schema_migrations WHERE version = 'V0001';

-- Drop migration ledger if this is the only migration
DROP TABLE IF EXISTS schema_migrations CASCADE;

-- Drop UUID extension (optional - may be used by other schemas)
-- DROP EXTENSION IF EXISTS "uuid-ossp";