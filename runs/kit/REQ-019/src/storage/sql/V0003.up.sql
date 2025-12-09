-- V0003.up.sql - Add admin configuration tables for REQ-019
-- Idempotent: uses IF NOT EXISTS checks

-- ============================================================================
-- EMAIL CONFIGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_config_id UUID NOT NULL REFERENCES provider_configs(id) ON DELETE CASCADE,
    smtp_host VARCHAR(255),
    smtp_port INTEGER,
    smtp_username VARCHAR(255),
    from_email VARCHAR(255),
    from_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for provider config lookup
CREATE INDEX IF NOT EXISTS idx_email_configs_provider_config_id 
    ON email_configs(provider_config_id);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_email_configs_updated_at ON email_configs;
CREATE TRIGGER update_email_configs_updated_at
    BEFORE UPDATE ON email_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- AUDIT LOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    changes JSONB NOT NULL DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);