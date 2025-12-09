-- seed.sql - Idempotent seed data for REQ-019 admin configuration
-- Extends base seed data with admin-specific records

-- ============================================================================
-- SEED EMAIL CONFIG (linked to existing provider config from REQ-001)
-- ============================================================================

-- First ensure we have a provider config to link to
INSERT INTO provider_configs (id, provider_type, provider_name, outbound_number, max_concurrent_calls, llm_provider, llm_model, recording_retention_days, transcript_retention_days, created_at, updated_at)
VALUES
    ('pc111111-1111-1111-1111-111111111111', 'telephony_api', 'twilio', '+14155550100', 10, 'openai', 'gpt-4.1-mini', 180, 180, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Email config linked to provider config
INSERT INTO email_configs (id, provider_config_id, smtp_host, smtp_port, smtp_username, from_email, from_name, created_at, updated_at)
VALUES
    ('ec111111-1111-1111-1111-111111111111', 'pc111111-1111-1111-1111-111111111111', 'smtp.example.com', 587, 'noreply@example.com', 'noreply@example.com', 'Voice Survey Agent', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED AUDIT LOGS (10 sample entries)
-- ============================================================================

-- Ensure admin user exists (from REQ-001 seed)
INSERT INTO users (id, oidc_sub, email, name, role, created_at, updated_at)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'oidc|admin001', 'admin@example.com', 'System Administrator', 'admin', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, changes, ip_address, user_agent, created_at)
VALUES
    ('al111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'config.read', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{}', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '7 days'),
    ('al222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'config.update', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{"telephony": {"max_concurrent_calls": {"old": "5", "new": "10"}}}', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '6 days'),
    ('al333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 'config.update', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{"llm": {"llm_model": {"old": "gpt-4", "new": "gpt-4.1-mini"}}}', '192.168.1.100', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', NOW() - INTERVAL '5 days'),
    ('al444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', 'config.read', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{}', '10.0.0.50', 'curl/7.79.1', NOW() - INTERVAL '4 days'),
    ('al555555-5555-5555-5555-555555555555', '11111111-1111-1111-1111-111111111111', 'config.update', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{"retention": {"recording_retention_days": {"old": 90, "new": 180}}}', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '3 days'),
    ('al666666-6666-6666-6666-666666666666', '11111111-1111-1111-1111-111111111111', 'config.update', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{"email": {"smtp_host": {"old": null, "new": "smtp.example.com"}}}', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '2 days'),
    ('al777777-7777-7777-7777-777777777777', '11111111-1111-1111-1111-111111111111', 'config.read', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{}', '192.168.1.101', 'Mozilla/5.0 (X11; Linux x86_64)', NOW() - INTERVAL '1 day'),
    ('al888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'config.update', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{"telephony": {"api_key": "***REDACTED***"}}', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '12 hours'),
    ('al999999-9999-9999-9999-999999999999', '11111111-1111-1111-1111-111111111111', 'config.read', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{}', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '6 hours'),
    ('alaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'config.update', 'admin_config', 'pc111111-1111-1111-1111-111111111111', '{"llm": {"api_key": "***REDACTED***"}}', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '1 hour')
ON CONFLICT (id) DO NOTHING;