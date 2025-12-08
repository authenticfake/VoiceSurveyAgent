-- V0001.up.sql - Initial schema for voicesurveyagent
-- All entities from SPEC data model with proper indexes and constraints

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types for all status and type fields
CREATE TYPE user_role AS ENUM ('admin', 'campaign_manager', 'viewer');
CREATE TYPE campaign_status AS ENUM ('draft', 'scheduled', 'running', 'paused', 'completed', 'cancelled');
CREATE TYPE campaign_language AS ENUM ('en', 'it');
CREATE TYPE question_type AS ENUM ('free_text', 'numeric', 'scale');
CREATE TYPE contact_state AS ENUM ('pending', 'in_progress', 'completed', 'refused', 'not_reached', 'excluded');
CREATE TYPE contact_language AS ENUM ('en', 'it', 'auto');
CREATE TYPE contact_outcome AS ENUM ('completed', 'refused', 'no_answer', 'busy', 'failed');
CREATE TYPE exclusion_source AS ENUM ('import', 'api', 'manual');
CREATE TYPE event_type AS ENUM ('survey.completed', 'survey.refused', 'survey.not_reached');
CREATE TYPE email_status AS ENUM ('pending', 'sent', 'failed');
CREATE TYPE email_template_type AS ENUM ('completed', 'refused', 'not_reached');
CREATE TYPE provider_type AS ENUM ('telephony_api', 'voice_ai_platform');
CREATE TYPE llm_provider AS ENUM ('openai', 'anthropic', 'azure-openai', 'google');

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    oidc_sub VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_oidc_sub ON users(oidc_sub);

-- Email templates table (must be created before campaigns due to FK)
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type email_template_type NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,
    locale campaign_language NOT NULL DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_templates_type ON email_templates(type);
CREATE INDEX IF NOT EXISTS idx_email_templates_locale ON email_templates(locale);

-- Campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status campaign_status NOT NULL DEFAULT 'draft',
    language campaign_language NOT NULL DEFAULT 'en',
    intro_script TEXT NOT NULL,
    question_1_text TEXT NOT NULL,
    question_1_type question_type NOT NULL,
    question_2_text TEXT NOT NULL,
    question_2_type question_type NOT NULL,
    question_3_text TEXT NOT NULL,
    question_3_type question_type NOT NULL,
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1 AND max_attempts <= 5),
    retry_interval_minutes INTEGER NOT NULL DEFAULT 60,
    allowed_call_start_local TIME NOT NULL DEFAULT '09:00:00',
    allowed_call_end_local TIME NOT NULL DEFAULT '20:00:00',
    email_completed_template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    email_refused_template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    email_not_reached_template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_name ON campaigns(name);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_created_by ON campaigns(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_email_completed ON campaigns(email_completed_template_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_email_refused ON campaigns(email_refused_template_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_email_not_reached ON campaigns(email_not_reached_template_id);

-- Contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    external_contact_id VARCHAR(255),
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    preferred_language contact_language NOT NULL DEFAULT 'auto',
    has_prior_consent BOOLEAN NOT NULL DEFAULT false,
    do_not_call BOOLEAN NOT NULL DEFAULT false,
    state contact_state NOT NULL DEFAULT 'pending',
    attempts_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    last_outcome contact_outcome,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contacts_campaign_id ON contacts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_contacts_phone_number ON contacts(phone_number);
CREATE INDEX IF NOT EXISTS idx_contacts_state ON contacts(state);
CREATE INDEX IF NOT EXISTS idx_contacts_do_not_call ON contacts(do_not_call);
CREATE INDEX IF NOT EXISTS idx_contacts_attempts ON contacts(attempts_count);

-- Exclusion list entries table
CREATE TABLE IF NOT EXISTS exclusion_list_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    reason TEXT,
    source exclusion_source NOT NULL DEFAULT 'manual',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exclusion_phone ON exclusion_list_entries(phone_number);

-- Call attempts table
CREATE TABLE IF NOT EXISTS call_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    call_id VARCHAR(255) NOT NULL UNIQUE,
    provider_call_id VARCHAR(255),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    answered_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    outcome contact_outcome,
    provider_raw_status VARCHAR(255),
    error_code VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_call_attempts_contact_id ON call_attempts(contact_id);
CREATE INDEX IF NOT EXISTS idx_call_attempts_campaign_id ON call_attempts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_call_attempts_call_id ON call_attempts(call_id);
CREATE INDEX IF NOT EXISTS idx_call_attempts_outcome ON call_attempts(outcome);
CREATE INDEX IF NOT EXISTS idx_call_attempts_started_at ON call_attempts(started_at);

-- Survey responses table
CREATE TABLE IF NOT EXISTS survey_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    call_attempt_id UUID NOT NULL REFERENCES call_attempts(id) ON DELETE CASCADE,
    q1_answer TEXT,
    q2_answer TEXT,
    q3_answer TEXT,
    q1_confidence NUMERIC(3,2) CHECK (q1_confidence >= 0 AND q1_confidence <= 1),
    q2_confidence NUMERIC(3,2) CHECK (q2_confidence >= 0 AND q2_confidence <= 1),
    q3_confidence NUMERIC(3,2) CHECK (q3_confidence >= 0 AND q3_confidence <= 1),
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(contact_id, campaign_id)
);

CREATE INDEX IF NOT EXISTS idx_survey_responses_contact_id ON survey_responses(contact_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_campaign_id ON survey_responses(campaign_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_call_attempt_id ON survey_responses(call_attempt_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_completed_at ON survey_responses(completed_at);

-- Events table
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type event_type NOT NULL,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    call_attempt_id UUID REFERENCES call_attempts(id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_campaign_id ON events(campaign_id);
CREATE INDEX IF NOT EXISTS idx_events_contact_id ON events(contact_id);
CREATE INDEX IF NOT EXISTS idx_events_call_attempt_id ON events(call_attempt_id);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

-- Email notifications table
CREATE TABLE IF NOT EXISTS email_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    template_id UUID NOT NULL REFERENCES email_templates(id) ON DELETE RESTRICT,
    to_email VARCHAR(255) NOT NULL,
    status email_status NOT NULL DEFAULT 'pending',
    provider_message_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_notifications_event_id ON email_notifications(event_id);
CREATE INDEX IF NOT EXISTS idx_email_notifications_contact_id ON email_notifications(contact_id);
CREATE INDEX IF NOT EXISTS idx_email_notifications_campaign_id ON email_notifications(campaign_id);
CREATE INDEX IF NOT EXISTS idx_email_notifications_template_id ON email_notifications(template_id);
CREATE INDEX IF NOT EXISTS idx_email_notifications_status ON email_notifications(status);

-- Provider configs table (single row or per-env)
CREATE TABLE IF NOT EXISTS provider_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_type provider_type NOT NULL DEFAULT 'telephony_api',
    provider_name VARCHAR(100) NOT NULL,
    outbound_number VARCHAR(20) NOT NULL,
    max_concurrent_calls INTEGER NOT NULL DEFAULT 5,
    llm_provider llm_provider NOT NULL DEFAULT 'openai',
    llm_model VARCHAR(100) NOT NULL DEFAULT 'gpt-4.1-mini',
    recording_retention_days INTEGER NOT NULL DEFAULT 180,
    transcript_retention_days INTEGER NOT NULL DEFAULT 180,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Transcript snippets table (optional for slice-1)
CREATE TABLE IF NOT EXISTS transcript_snippets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    call_attempt_id UUID NOT NULL REFERENCES call_attempts(id) ON DELETE CASCADE,
    transcript_text TEXT NOT NULL,
    language campaign_language NOT NULL DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transcript_snippets_call_attempt_id ON transcript_snippets(call_attempt_id);

-- Trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_templates_updated_at
    BEFORE UPDATE ON email_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_notifications_updated_at
    BEFORE UPDATE ON email_notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provider_configs_updated_at
    BEFORE UPDATE ON provider_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();