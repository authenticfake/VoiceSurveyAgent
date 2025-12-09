-- V0002.up.sql - Add export_jobs table for REQ-018
-- Idempotent: uses IF NOT EXISTS checks

-- ============================================================================
-- ENUM TYPE FOR EXPORT JOB STATUS
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE export_job_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- EXPORT JOBS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS export_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    requested_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status export_job_status NOT NULL DEFAULT 'pending',
    s3_key VARCHAR(500),
    download_url TEXT,
    url_expires_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    total_records INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_export_jobs_campaign_id ON export_jobs(campaign_id);
CREATE INDEX IF NOT EXISTS ix_export_jobs_status ON export_jobs(status);
CREATE INDEX IF NOT EXISTS ix_export_jobs_created_at ON export_jobs(created_at DESC);