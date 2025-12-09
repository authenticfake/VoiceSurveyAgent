-- V0003.down.sql - Rollback admin configuration tables for REQ-019
-- Idempotent: uses IF EXISTS checks

-- ============================================================================
-- DROP TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_email_configs_updated_at ON email_configs;

-- ============================================================================
-- DROP INDEXES
-- ============================================================================

DROP INDEX IF EXISTS idx_audit_logs_action;
DROP INDEX IF EXISTS idx_audit_logs_created_at;
DROP INDEX IF EXISTS idx_audit_logs_resource_type;
DROP INDEX IF EXISTS idx_audit_logs_user_id;
DROP INDEX IF EXISTS idx_email_configs_provider_config_id;

-- ============================================================================
-- DROP TABLES
-- ============================================================================

DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS email_configs;