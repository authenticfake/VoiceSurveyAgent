-- seed.sql - Idempotent seed data for voicesurveyagent
-- Contains 10-20 seed records as per requirements

-- Seed admin user (idempotent via ON CONFLICT)
INSERT INTO users (id, oidc_sub, email, name, role)
VALUES 
    ('00000000-0000-0000-0000-000000000001', 'admin-oidc-sub-001', 'admin@voicesurvey.local', 'System Admin', 'admin'),
    ('00000000-0000-0000-0000-000000000002', 'manager-oidc-sub-001', 'manager@voicesurvey.local', 'Campaign Manager', 'campaign_manager'),
    ('00000000-0000-0000-0000-000000000003', 'viewer-oidc-sub-001', 'viewer@voicesurvey.local', 'Report Viewer', 'viewer')
ON CONFLICT (oidc_sub) DO UPDATE SET
    email = EXCLUDED.email,
    name = EXCLUDED.name,
    role = EXCLUDED.role,
    updated_at = NOW();

-- Seed email templates (idempotent via ON CONFLICT on id)
INSERT INTO email_templates (id, name, type, subject, body_html, body_text, locale)
VALUES 
    ('00000000-0000-0000-0001-000000000001', 'Survey Completed - EN', 'completed', 
     'Thank you for completing our survey', 
     '<html><body><h1>Thank you!</h1><p>Dear {{contact_name}},</p><p>Thank you for taking the time to complete our survey for {{campaign_name}}.</p></body></html>',
     'Thank you for completing our survey for {{campaign_name}}.',
     'en'),
    ('00000000-0000-0000-0001-000000000002', 'Survey Completed - IT', 'completed', 
     'Grazie per aver completato il nostro sondaggio', 
     '<html><body><h1>Grazie!</h1><p>Gentile {{contact_name}},</p><p>Grazie per aver dedicato del tempo a completare il nostro sondaggio per {{campaign_name}}.</p></body></html>',
     'Grazie per aver completato il nostro sondaggio per {{campaign_name}}.',
     'it'),
    ('00000000-0000-0000-0001-000000000003', 'Survey Refused - EN', 'refused', 
     'We respect your decision', 
     '<html><body><h1>Thank you</h1><p>Dear {{contact_name}},</p><p>We respect your decision not to participate in our survey.</p></body></html>',
     'We respect your decision not to participate in our survey.',
     'en'),
    ('00000000-0000-0000-0001-000000000004', 'Not Reached - EN', 'not_reached', 
     'We tried to reach you', 
     '<html><body><h1>We tried to reach you</h1><p>Dear {{contact_name}},</p><p>We attempted to contact you for our survey but were unable to reach you.</p></body></html>',
     'We attempted to contact you for our survey but were unable to reach you.',
     'en'),
    ('00000000-0000-0000-0001-000000000005', 'Not Reached - IT', 'not_reached', 
     'Abbiamo provato a contattarti', 
     '<html><body><h1>Abbiamo provato a raggiungerti</h1><p>Gentile {{contact_name}},</p><p>Abbiamo provato a contattarti per il nostro sondaggio ma non siamo riusciti a raggiungerti.</p></body></html>',
     'Abbiamo provato a contattarti per il nostro sondaggio ma non siamo riusciti a raggiungerti.',
     'it')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    type = EXCLUDED.type,
    subject = EXCLUDED.subject,
    body_html = EXCLUDED.body_html,
    body_text = EXCLUDED.body_text,
    locale = EXCLUDED.locale,
    updated_at = NOW();

-- Seed provider config (single row, idempotent)
INSERT INTO provider_configs (id, provider_type, provider_name, outbound_number, max_concurrent_calls, llm_provider, llm_model, recording_retention_days, transcript_retention_days)
VALUES 
    ('00000000-0000-0000-0002-000000000001', 'telephony_api', 'twilio', '+14155551234', 5, 'openai', 'gpt-4.1-mini', 180, 180)
ON CONFLICT (id) DO UPDATE SET
    provider_type = EXCLUDED.provider_type,
    provider_name = EXCLUDED.provider_name,
    outbound_number = EXCLUDED.outbound_number,
    max_concurrent_calls = EXCLUDED.max_concurrent_calls,
    llm_provider = EXCLUDED.llm_provider,
    llm_model = EXCLUDED.llm_model,
    recording_retention_days = EXCLUDED.recording_retention_days,
    transcript_retention_days = EXCLUDED.transcript_retention_days,
    updated_at = NOW();

-- Seed a sample campaign (idempotent via ON CONFLICT on id)
INSERT INTO campaigns (id, name, description, status, language, intro_script, 
    question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type,
    max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local,
    email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id)
VALUES 
    ('00000000-0000-0000-0003-000000000001', 'Customer Satisfaction Survey Q1', 
     'Quarterly customer satisfaction survey for Q1 2024',
     'draft', 'en',
     'Hello, this is VoiceSurvey calling on behalf of Acme Corp. We are conducting a brief 3-question survey about your recent experience. This will take approximately 2 minutes. Do you consent to participate?',
     'On a scale of 1 to 10, how satisfied are you with our service?', 'scale',
     'What aspect of our service do you value most?', 'free_text',
     'How likely are you to recommend us to a friend or colleague, on a scale of 1 to 10?', 'scale',
     3, 60, '09:00:00', '20:00:00',
     '00000000-0000-0000-0001-000000000001', '00000000-0000-0000-0001-000000000003', '00000000-0000-0000-0001-000000000004',
     '00000000-0000-0000-0000-000000000002')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    updated_at = NOW();

-- Seed contacts for the campaign (idempotent via unique constraint workaround)
INSERT INTO contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state)
VALUES 
    ('00000000-0000-0000-0004-000000000001', '00000000-0000-0000-0003-000000000001', 'EXT-001', '+14155550101', 'contact1@example.com', 'en', true, false, 'pending'),
    ('00000000-0000-0000-0004-000000000002', '00000000-0000-0000-0003-000000000001', 'EXT-002', '+14155550102', 'contact2@example.com', 'en', true, false, 'pending'),
    ('00000000-0000-0000-0004-000000000003', '00000000-0000-0000-0003-000000000001', 'EXT-003', '+14155550103', 'contact3@example.com', 'en', false, false, 'pending'),
    ('00000000-0000-0000-0004-000000000004', '00000000-0000-0000-0003-000000000001', 'EXT-004', '+14155550104', NULL, 'auto', true, false, 'pending'),
    ('00000000-0000-0000-0004-000000000005', '00000000-0000-0000-0003-000000000001', 'EXT-005', '+14155550105', 'contact5@example.com', 'en', true, true, 'excluded')
ON CONFLICT (id) DO UPDATE SET
    phone_number = EXCLUDED.phone_number,
    email = EXCLUDED.email,
    updated_at = NOW();

-- Seed exclusion list entries
INSERT INTO exclusion_list_entries (id, phone_number, reason, source)
VALUES 
    ('00000000-0000-0000-0005-000000000001', '+14155550199', 'Customer requested removal', 'api'),
    ('00000000-0000-0000-0005-000000000002', '+14155550198', 'Legal hold', 'manual'),
    ('00000000-0000-0000-0005-000000000003', '+14155550197', 'Imported from DNC list', 'import')
ON CONFLICT (phone_number) DO UPDATE SET
    reason = EXCLUDED.reason,
    source = EXCLUDED.source;