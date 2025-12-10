-- V0004.down.sql - Rollback GDPR deletion requests table for REQ-022
-- Idempotent: uses IF EXISTS checks

-- ============================================================================
-- DROP INDEXES
-- ============================================================================

DROP INDEX IF EXISTS idx_retention_job_history_started_at;
DROP INDEX IF EXISTS idx_retention_job_history_status;
DROP INDEX IF EXISTS idx_gdpr_requests_contact_id;
DROP INDEX IF EXISTS idx_gdpr_requests_deadline;
DROP INDEX IF EXISTS idx_gdpr_requests_status;

-- ============================================================================
-- DROP TABLES
-- ============================================================================

DROP TABLE IF EXISTS retention_job_history;
DROP TABLE IF EXISTS gdpr_deletion_requests;

-- ============================================================================
-- DROP ENUM TYPES
-- ============================================================================

DROP TYPE IF EXISTS gdpr_request_status;