-- V0004.up.sql - Add GDPR deletion requests table for REQ-022
-- Idempotent: uses IF NOT EXISTS checks

-- ============================================================================
-- ENUM TYPE FOR GDPR REQUEST STATUS
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE gdpr_request_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- GDPR DELETION REQUESTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS gdpr_deletion_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID NOT NULL,
    contact_phone VARCHAR(20),
    contact_email VARCHAR(255),
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    status gdpr_request_status NOT NULL DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE,
    items_deleted INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for pending requests lookup
CREATE INDEX IF NOT EXISTS idx_gdpr_requests_status 
    ON gdpr_deletion_requests(status);

-- Index for deadline monitoring
CREATE INDEX IF NOT EXISTS idx_gdpr_requests_deadline 
    ON gdpr_deletion_requests(deadline);

-- Index for contact lookup
CREATE INDEX IF NOT EXISTS idx_gdpr_requests_contact_id 
    ON gdpr_deletion_requests(contact_id);

-- ============================================================================
-- RETENTION JOB HISTORY TABLE (for tracking job executions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS retention_job_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    recordings_deleted INTEGER DEFAULT 0,
    recordings_failed INTEGER DEFAULT 0,
    transcripts_deleted INTEGER DEFAULT 0,
    transcripts_failed INTEGER DEFAULT 0,
    total_deleted INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for status queries
CREATE INDEX IF NOT EXISTS idx_retention_job_history_status 
    ON retention_job_history(status);

-- Index for date range queries
CREATE INDEX IF NOT EXISTS idx_retention_job_history_started_at 
    ON retention_job_history(started_at);