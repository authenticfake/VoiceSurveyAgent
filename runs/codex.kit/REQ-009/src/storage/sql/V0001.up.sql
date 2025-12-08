SET client_min_messages TO WARNING;
SET search_path TO public;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DO $$
BEGIN
    CREATE TYPE user_role_enum AS ENUM ('admin', 'campaign_manager', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE campaign_status_enum AS ENUM ('draft', 'scheduled', 'running', 'paused', 'completed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE campaign_language_enum AS ENUM ('en', 'it');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE question_type_enum AS ENUM ('free_text', 'numeric', 'scale');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE contact_state_enum AS ENUM ('pending', 'in_progress', 'completed', 'refused', 'not_reached', 'excluded');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE contact_language_enum AS ENUM ('auto', 'en', 'it');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE call_outcome_enum AS ENUM ('completed', 'refused', 'no_answer', 'busy', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE event_type_enum AS ENUM ('survey.completed', 'survey.refused', 'survey.not_reached');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE email_template_type_enum AS ENUM ('completed', 'refused', 'not_reached');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE email_notification_status_enum AS ENUM ('pending', 'sent', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE provider_type_enum AS ENUM ('telephony_api', 'voice_ai_platform');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE llm_provider_enum AS ENUM ('openai', 'anthropic', 'azure-openai', 'google');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(32) PRIMARY KEY,
    checksum VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'applied',
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    oidc_sub TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role user_role_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    type email_template_type_enum NOT NULL,
    locale campaign_language_enum NOT NULL,
    subject TEXT NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_email_templates_type_locale UNIQUE (type, locale)
);

CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT NULL,
    status campaign_status_enum NOT NULL DEFAULT 'draft',
    language campaign_language_enum NOT NULL DEFAULT 'en',
    intro_script TEXT NOT NULL,
    question_1_text TEXT NOT NULL,
    question_1_type question_type_enum NOT NULL,
    question_2_text TEXT NOT NULL,
    question_2_type question_type_enum NOT NULL,
    question_3_text TEXT NOT NULL,
    question_3_type question_type_enum NOT NULL,
    max_attempts SMALLINT NOT NULL CHECK (max_attempts BETWEEN 1 AND 5),
    retry_interval_minutes SMALLINT NOT NULL CHECK (retry_interval_minutes > 0),
    allowed_call_start_local TIME NOT NULL,
    allowed_call_end_local TIME NOT NULL,
    email_completed_template_id UUID NULL REFERENCES email_templates(id) ON DELETE SET NULL,
    email_refused_template_id UUID NULL REFERENCES email_templates(id) ON DELETE SET NULL,
    email_not_reached_template_id UUID NULL REFERENCES email_templates(id) ON DELETE SET NULL,
    created_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS ix_campaigns_language ON campaigns(language);

CREATE TABLE IF NOT EXISTS exclusion_list_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number TEXT NOT NULL UNIQUE,
    reason TEXT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    external_contact_id TEXT NULL,
    phone_number TEXT NOT NULL,
    email TEXT NULL,
    preferred_language contact_language_enum NOT NULL DEFAULT 'auto',
    has_prior_consent BOOLEAN NOT NULL DEFAULT FALSE,
    do_not_call BOOLEAN NOT NULL DEFAULT FALSE,
    state contact_state_enum NOT NULL DEFAULT 'pending',
    attempts_count INTEGER NOT NULL DEFAULT 0 CHECK (attempts_count >= 0),
    last_attempt_at TIMESTAMPTZ NULL,
    last_outcome call_outcome_enum NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_contacts_campaign_external UNIQUE (campaign_id, external_contact_id),
    CONSTRAINT uq_contacts_campaign_phone UNIQUE (campaign_id, phone_number)
);

CREATE INDEX IF NOT EXISTS ix_contacts_campaign_state ON contacts(campaign_id, state);
CREATE INDEX IF NOT EXISTS ix_contacts_phone_number ON contacts(phone_number);

CREATE TABLE IF NOT EXISTS call_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    attempt_number SMALLINT NOT NULL,
    call_id TEXT NOT NULL,
    provider_call_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    answered_at TIMESTAMPTZ NULL,
    ended_at TIMESTAMPTZ NULL,
    outcome call_outcome_enum NULL,
    provider_raw_status TEXT NULL,
    error_code TEXT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_call_attempts_call_id UNIQUE (call_id),
    CONSTRAINT uq_call_attempts_provider_call_id UNIQUE (provider_call_id)
);

CREATE INDEX IF NOT EXISTS ix_call_attempts_contact_id ON call_attempts(contact_id);
CREATE INDEX IF NOT EXISTS ix_call_attempts_campaign_id ON call_attempts(campaign_id);

CREATE TABLE IF NOT EXISTS survey_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    call_attempt_id UUID NOT NULL REFERENCES call_attempts(id) ON DELETE CASCADE,
    q1_answer TEXT NOT NULL,
    q2_answer TEXT NOT NULL,
    q3_answer TEXT NOT NULL,
    q1_confidence NUMERIC(3,2) NULL,
    q2_confidence NUMERIC(3,2) NULL,
    q3_confidence NUMERIC(3,2) NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_survey_responses_contact UNIQUE (contact_id)
);

CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type event_type_enum NOT NULL,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    call_attempt_id UUID NULL REFERENCES call_attempts(id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_events_campaign_event ON events(campaign_id, event_type);

CREATE TABLE IF NOT EXISTS email_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    template_id UUID NULL REFERENCES email_templates(id) ON DELETE SET NULL,
    to_email TEXT NOT NULL,
    status email_notification_status_enum NOT NULL DEFAULT 'pending',
    provider_message_id TEXT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_email_notifications_status ON email_notifications(status);

CREATE TABLE IF NOT EXISTS provider_configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_type provider_type_enum NOT NULL,
    provider_name TEXT NOT NULL,
    outbound_number TEXT NOT NULL,
    max_concurrent_calls SMALLINT NOT NULL CHECK (max_concurrent_calls > 0),
    llm_provider llm_provider_enum NOT NULL,
    llm_model TEXT NOT NULL,
    recording_retention_days INTEGER NOT NULL CHECK (recording_retention_days > 0),
    transcript_retention_days INTEGER NOT NULL CHECK (transcript_retention_days > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_provider_configurations_type UNIQUE (provider_type)
);

CREATE TABLE IF NOT EXISTS transcript_snippets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    call_attempt_id UUID NOT NULL REFERENCES call_attempts(id) ON DELETE CASCADE,
    transcript_text TEXT NOT NULL,
    language campaign_language_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);