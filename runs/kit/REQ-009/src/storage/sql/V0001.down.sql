SET client_min_messages TO WARNING;
SET search_path TO public;

DROP TABLE IF EXISTS transcript_snippets;
DROP TABLE IF EXISTS provider_configurations;
DROP TABLE IF EXISTS email_notifications;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS survey_responses;
DROP TABLE IF EXISTS call_attempts;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS exclusion_list_entries;
DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS email_templates;
DROP TABLE IF EXISTS users;

DO $$
BEGIN
    DROP TYPE IF EXISTS llm_provider_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS provider_type_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS email_notification_status_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS email_template_type_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS event_type_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS call_outcome_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS contact_language_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS contact_state_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS question_type_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS campaign_language_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS campaign_status_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$
BEGIN
    DROP TYPE IF EXISTS user_role_enum;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;