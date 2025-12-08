-- V0001.down.sql - Rollback initial schema for voicesurveyagent

-- Drop triggers first
DROP TRIGGER IF EXISTS update_provider_configs_updated_at ON provider_configs;
DROP TRIGGER IF EXISTS update_email_notifications_updated_at ON email_notifications;
DROP TRIGGER IF EXISTS update_email_templates_updated_at ON email_templates;
DROP TRIGGER IF EXISTS update_contacts_updated_at ON contacts;
DROP TRIGGER IF EXISTS update_campaigns_updated_at ON campaigns;
DROP TRIGGER IF EXISTS update_users_updated_at ON users;

-- Drop trigger function
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop tables in reverse dependency order
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

-- Drop enum types
DROP TYPE IF EXISTS llm_provider;
DROP TYPE IF EXISTS provider_type;
DROP TYPE IF EXISTS email_template_type;
DROP TYPE IF EXISTS email_status;
DROP TYPE IF EXISTS event_type;
DROP TYPE IF EXISTS exclusion_source;
DROP TYPE IF EXISTS contact_outcome;
DROP TYPE IF EXISTS contact_language;
DROP TYPE IF EXISTS contact_state;
DROP TYPE IF EXISTS question_type;
DROP TYPE IF EXISTS campaign_language;
DROP TYPE IF EXISTS campaign_status;
DROP TYPE IF EXISTS user_role;