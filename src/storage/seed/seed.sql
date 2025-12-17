-- seed.sql - Idempotent seed data for voicesurveyagent
-- Contains 10-20 seed records for development and testing

-- ============================================================================
-- SEED USERS (10 records)
-- ============================================================================

INSERT INTO users (id, oidc_sub, email, name, role, created_at, updated_at)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'oidc|admin001', 'admin@example.com', 'System Administrator', 'admin', NOW(), NOW()),
    ('22222222-2222-2222-2222-222222222222', 'oidc|manager001', 'manager1@example.com', 'Campaign Manager One', 'campaign_manager', NOW(), NOW()),
    ('33333333-3333-3333-3333-333333333333', 'oidc|manager002', 'manager2@example.com', 'Campaign Manager Two', 'campaign_manager', NOW(), NOW()),
    ('44444444-4444-4444-4444-444444444444', 'oidc|viewer001', 'viewer1@example.com', 'Viewer One', 'viewer', NOW(), NOW()),
    ('55555555-5555-5555-5555-555555555555', 'oidc|viewer002', 'viewer2@example.com', 'Viewer Two', 'viewer', NOW(), NOW()),
    ('66666666-6666-6666-6666-666666666666', 'oidc|manager003', 'manager3@example.com', 'Campaign Manager Three', 'campaign_manager', NOW(), NOW()),
    ('77777777-7777-7777-7777-777777777777', 'oidc|viewer003', 'viewer3@example.com', 'Viewer Three', 'viewer', NOW(), NOW()),
    ('88888888-8888-8888-8888-888888888888', 'oidc|admin002', 'admin2@example.com', 'Backup Administrator', 'admin', NOW(), NOW()),
    ('99999999-9999-9999-9999-999999999999', 'oidc|manager004', 'manager4@example.com', 'Campaign Manager Four', 'campaign_manager', NOW(), NOW()),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'oidc|viewer004', 'viewer4@example.com', 'Viewer Four', 'viewer', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED EMAIL TEMPLATES (6 records - 2 per type, EN and IT)
-- ============================================================================

INSERT INTO email_templates (id, name, type, subject, body_html, body_text, locale, created_at, updated_at)
VALUES
    ('e1111111-1111-1111-1111-111111111111', 'Survey Completed - EN', 'completed', 'Thank you for completing our survey', '<html><body><h1>Thank you!</h1><p>We appreciate your time completing our survey.</p></body></html>', 'Thank you! We appreciate your time completing our survey.', 'en', NOW(), NOW()),
    ('e2222222-2222-2222-2222-222222222222', 'Survey Completed - IT', 'completed', 'Grazie per aver completato il nostro sondaggio', '<html><body><h1>Grazie!</h1><p>Apprezziamo il tempo dedicato al nostro sondaggio.</p></body></html>', 'Grazie! Apprezziamo il tempo dedicato al nostro sondaggio.', 'it', NOW(), NOW()),
    ('e3333333-3333-3333-3333-333333333333', 'Survey Refused - EN', 'refused', 'We respect your decision', '<html><body><h1>Thank you</h1><p>We respect your decision not to participate.</p></body></html>', 'Thank you. We respect your decision not to participate.', 'en', NOW(), NOW()),
    ('e4444444-4444-4444-4444-444444444444', 'Survey Refused - IT', 'refused', 'Rispettiamo la tua decisione', '<html><body><h1>Grazie</h1><p>Rispettiamo la tua decisione di non partecipare.</p></body></html>', 'Grazie. Rispettiamo la tua decisione di non partecipare.', 'it', NOW(), NOW()),
    ('e5555555-5555-5555-5555-555555555555', 'Could Not Reach - EN', 'not_reached', 'We tried to reach you', '<html><body><h1>We missed you</h1><p>We tried to reach you for our survey but were unable to connect.</p></body></html>', 'We missed you. We tried to reach you for our survey but were unable to connect.', 'en', NOW(), NOW()),
    ('e6666666-6666-6666-6666-666666666666', 'Could Not Reach - IT', 'not_reached', 'Abbiamo provato a contattarti', '<html><body><h1>Non siamo riusciti a raggiungerti</h1><p>Abbiamo provato a contattarti per il nostro sondaggio ma non siamo riusciti a connetterci.</p></body></html>', 'Non siamo riusciti a raggiungerti. Abbiamo provato a contattarti per il nostro sondaggio.', 'it', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED CAMPAIGNS (4 records)
-- ============================================================================

INSERT INTO campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at)
VALUES
    ('c1111111-1111-1111-1111-111111111111', 'Customer Satisfaction Q1 2024', 'Quarterly customer satisfaction survey for Q1 2024', 'draft', 'en', 'Hello, this is a call from Example Corp. We are conducting a brief 3-question survey about your recent experience. This will take approximately 2 minutes. Do you consent to participate?', 'On a scale of 1 to 10, how satisfied are you with our service?', 'scale', 'What could we improve about our service?', 'free_text', 'How likely are you to recommend us to a friend? Please answer from 1 to 10.', 'numeric', 3, 60, '09:00:00', '20:00:00', 'e1111111-1111-1111-1111-111111111111', 'e3333333-3333-3333-3333-333333333333', 'e5555555-5555-5555-5555-555555555555', '22222222-2222-2222-2222-222222222222', NOW(), NOW()),
    ('c2222222-2222-2222-2222-222222222222', 'Product Feedback Survey', 'Survey to gather feedback on new product features', 'running', 'en', 'Hi there! This is Example Corp calling about our new product. We have 3 quick questions that will take about 2 minutes. May we proceed?', 'How would you rate the ease of use of our new feature? 1 being difficult, 10 being very easy.', 'scale', 'What feature would you most like to see added?', 'free_text', 'How many times per week do you use our product?', 'numeric', 5, 120, '10:00:00', '18:00:00', 'e1111111-1111-1111-1111-111111111111', 'e3333333-3333-3333-3333-333333333333', 'e5555555-5555-5555-5555-555555555555', '33333333-3333-3333-3333-333333333333', NOW(), NOW()),
    ('c3333333-3333-3333-3333-333333333333', 'Sondaggio Soddisfazione Clienti', 'Sondaggio trimestrale sulla soddisfazione dei clienti', 'scheduled', 'it', 'Buongiorno, la chiamo da Example Corp. Stiamo conducendo un breve sondaggio di 3 domande sulla sua esperienza recente. Ci vorranno circa 2 minuti. Acconsente a partecipare?', 'Su una scala da 1 a 10, quanto è soddisfatto del nostro servizio?', 'scale', 'Cosa potremmo migliorare del nostro servizio?', 'free_text', 'Quanto è probabile che ci raccomandi a un amico? Risponda da 1 a 10.', 'numeric', 3, 90, '09:30:00', '19:30:00', 'e2222222-2222-2222-2222-222222222222', 'e4444444-4444-4444-4444-444444444444', 'e6666666-6666-6666-6666-666666666666', '22222222-2222-2222-2222-222222222222', NOW(), NOW()),
    ('c4444444-4444-4444-4444-444444444444', 'Service Quality Assessment', 'Annual service quality assessment survey', 'completed', 'en', 'Good day! This is Example Corp. We are conducting our annual service quality survey. It consists of 3 questions and takes about 2 minutes. Would you like to participate?', 'Overall, how would you rate our service quality from 1 to 10?', 'scale', 'Please describe any issues you have experienced.', 'free_text', 'How many years have you been our customer?', 'numeric', 4, 60, '08:00:00', '21:00:00', 'e1111111-1111-1111-1111-111111111111', 'e3333333-3333-3333-3333-333333333333', 'e5555555-5555-5555-5555-555555555555', '66666666-6666-6666-6666-666666666666', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED CONTACTS (12 records across campaigns)
-- ============================================================================

INSERT INTO contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at)
VALUES
    ('d1111111-1111-1111-1111-111111111111', 'c1111111-1111-1111-1111-111111111111', 'EXT001', '+14155551001', 'contact1@example.com', 'auto', TRUE, FALSE, 'pending', 0, NULL, NULL, NOW(), NOW()),
    ('d2222222-2222-2222-2222-222222222222', 'c1111111-1111-1111-1111-111111111111', 'EXT002', '+14155551002', 'contact2@example.com', 'en', TRUE, FALSE, 'pending', 0, NULL, NULL, NOW(), NOW()),
    ('d3333333-3333-3333-3333-333333333333', 'c1111111-1111-1111-1111-111111111111', 'EXT003', '+14155551003', 'contact3@example.com', 'auto', FALSE, FALSE, 'pending', 0, NULL, NULL, NOW(), NOW()),
    ('d4444444-4444-4444-4444-444444444444', 'c2222222-2222-2222-2222-222222222222', 'EXT004', '+14155551004', 'contact4@example.com', 'en', TRUE, FALSE, 'completed', 1, NOW() - INTERVAL '1 day', 'completed', NOW(), NOW()),
    ('d5555555-5555-5555-5555-555555555555', 'c2222222-2222-2222-2222-222222222222', 'EXT005', '+14155551005', 'contact5@example.com', 'auto', TRUE, FALSE, 'refused', 1, NOW() - INTERVAL '2 days', 'refused', NOW(), NOW()),
    ('d6666666-6666-6666-6666-666666666666', 'c2222222-2222-2222-2222-222222222222', 'EXT006', '+14155551006', 'contact6@example.com', 'en', TRUE, FALSE, 'not_reached', 5, NOW() - INTERVAL '1 day', 'no_answer', NOW(), NOW()),
    ('d7777777-7777-7777-7777-777777777777', 'c2222222-2222-2222-2222-222222222222', NULL, '+14155551007', NULL, 'auto', FALSE, FALSE, 'in_progress', 2, NOW() - INTERVAL '1 hour', 'busy', NOW(), NOW()),
    ('d8888888-8888-8888-8888-888888888888', 'c3333333-3333-3333-3333-333333333333', 'EXT008', '+393331234567', 'contact8@example.it', 'it', TRUE, FALSE, 'pending', 0, NULL, NULL, NOW(), NOW()),
    ('d9999999-9999-9999-9999-999999999999', 'c3333333-3333-3333-3333-333333333333', 'EXT009', '+393331234568', 'contact9@example.it', 'it', TRUE, FALSE, 'pending', 0, NULL, NULL, NOW(), NOW()),
    ('daaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'c4444444-4444-4444-4444-444444444444', 'EXT010', '+14155551010', 'contact10@example.com', 'en', TRUE, FALSE, 'completed', 1, NOW() - INTERVAL '30 days', 'completed', NOW(), NOW()),
    ('dbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'c4444444-4444-4444-4444-444444444444', 'EXT011', '+14155551011', 'contact11@example.com', 'auto', TRUE, FALSE, 'completed', 2, NOW() - INTERVAL '29 days', 'completed', NOW(), NOW()),
    ('dccccccc-cccc-cccc-cccc-cccccccccccc', 'c1111111-1111-1111-1111-111111111111', 'EXT012', '+14155551012', NULL, 'auto', FALSE, TRUE, 'excluded', 0, NULL, NULL, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED EXCLUSION LIST ENTRIES (4 records)
-- ============================================================================

INSERT INTO exclusion_list_entries (id, phone_number, reason, source, created_at)
VALUES
    ('f1111111-1111-1111-1111-111111111111', '+14155559999', 'Customer requested removal from all lists', 'api', NOW()),
    ('f2222222-2222-2222-2222-222222222222', '+14155559998', 'Legal do-not-call request', 'manual', NOW()),
    ('f3333333-3333-3333-3333-333333333333', '+393339999999', 'GDPR deletion request', 'api', NOW()),
    ('f4444444-4444-4444-4444-444444444444', '+14155551012', 'Customer opt-out via import', 'import', NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED PROVIDER CONFIG (1 record)
-- ============================================================================

INSERT INTO provider_configs (id, provider_type, provider_name, outbound_number, max_concurrent_calls, llm_provider, llm_model, recording_retention_days, transcript_retention_days, created_at, updated_at)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'telephony_api', 'twilio', '+14155550000', 10, 'openai', 'gpt-4.1-mini', 180, 180, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED CALL ATTEMPTS (4 records for completed/running campaigns)
-- ============================================================================

INSERT INTO call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, answered_at, ended_at, outcome, provider_raw_status, error_code, metadata)
VALUES
    ('a1111111-1111-1111-1111-111111111111', 'd4444444-4444-4444-4444-444444444444', 'c2222222-2222-2222-2222-222222222222', 1, 'call-001-uuid', 'CA001twilio', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day' + INTERVAL '10 seconds', NOW() - INTERVAL '1 day' + INTERVAL '3 minutes', 'completed', 'completed', NULL, '{"duration_seconds": 170}'),
    ('a2222222-2222-2222-2222-222222222222', 'd5555555-5555-5555-5555-555555555555', 'c2222222-2222-2222-2222-222222222222', 1, 'call-002-uuid', 'CA002twilio', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '8 seconds', NOW() - INTERVAL '2 days' + INTERVAL '30 seconds', 'refused', 'completed', NULL, '{"duration_seconds": 22}'),
    ('a3333333-3333-3333-3333-333333333333', 'd6666666-6666-6666-6666-666666666666', 'c2222222-2222-2222-2222-222222222222', 5, 'call-003-uuid', 'CA003twilio', NOW() - INTERVAL '1 day', NULL, NOW() - INTERVAL '1 day' + INTERVAL '30 seconds', 'no_answer', 'no-answer', NULL, '{}'),
    ('a4444444-4444-4444-4444-444444444444', 'daaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'c4444444-4444-4444-4444-444444444444', 1, 'call-004-uuid', 'CA004twilio', NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days' + INTERVAL '12 seconds', NOW() - INTERVAL '30 days' + INTERVAL '4 minutes', 'completed', 'completed', NULL, '{"duration_seconds": 228}')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED SURVEY RESPONSES (2 records for completed surveys)
-- ============================================================================

INSERT INTO survey_responses (id, contact_id, campaign_id, call_attempt_id, q1_answer, q2_answer, q3_answer, q1_confidence, q2_confidence, q3_confidence, completed_at)
VALUES
    ('b1111111-1111-1111-1111-111111111111', 'd4444444-4444-4444-4444-444444444444', 'c2222222-2222-2222-2222-222222222222', 'a1111111-1111-1111-1111-111111111111', '8', 'The mobile app could be faster', '7', 0.95, 0.88, 0.92, NOW() - INTERVAL '1 day' + INTERVAL '3 minutes'),
    ('b2222222-2222-2222-2222-222222222222', 'daaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'c4444444-4444-4444-4444-444444444444', 'a4444444-4444-4444-4444-444444444444', '9', 'Everything works great, no complaints', '5', 0.97, 0.91, 0.89, NOW() - INTERVAL '30 days' + INTERVAL '4 minutes')
ON CONFLICT (contact_id, campaign_id) DO NOTHING;

-- ============================================================================
-- SEED EVENTS (3 records)
-- ============================================================================

INSERT INTO events (id, event_type, campaign_id, contact_id, call_attempt_id, payload, created_at)
VALUES
    ('ee111111-1111-1111-1111-111111111111', 'survey.completed', 'c2222222-2222-2222-2222-222222222222', 'd4444444-4444-4444-4444-444444444444', 'a1111111-1111-1111-1111-111111111111', '{"answers": ["8", "The mobile app could be faster", "7"], "attempts": 1}', NOW() - INTERVAL '1 day' + INTERVAL '3 minutes'),
    ('ee222222-2222-2222-2222-222222222222', 'survey.refused', 'c2222222-2222-2222-2222-222222222222', 'd5555555-5555-5555-5555-555555555555', 'a2222222-2222-2222-2222-222222222222', '{"attempts": 1, "reason": "explicit_refusal"}', NOW() - INTERVAL '2 days' + INTERVAL '30 seconds'),
    ('ee333333-3333-3333-3333-333333333333', 'survey.not_reached', 'c2222222-2222-2222-2222-222222222222', 'd6666666-6666-6666-6666-666666666666', 'a3333333-3333-3333-3333-333333333333', '{"attempts": 5, "last_outcome": "no_answer"}', NOW() - INTERVAL '1 day' + INTERVAL '30 seconds')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED EMAIL NOTIFICATIONS (2 records)
-- ============================================================================

INSERT INTO email_notifications (id, event_id, contact_id, campaign_id, template_id, to_email, status, provider_message_id, error_message, created_at, updated_at)
VALUES
    ('ea111111-1111-1111-1111-111111111111', 'ee111111-1111-1111-1111-111111111111', 'd4444444-4444-4444-4444-444444444444', 'c2222222-2222-2222-2222-222222222222', 'e1111111-1111-1111-1111-111111111111', 'contact4@example.com', 'sent', 'ses-msg-001', NULL, NOW() - INTERVAL '1 day' + INTERVAL '4 minutes', NOW() - INTERVAL '1 day' + INTERVAL '4 minutes'),
    ('ea222222-2222-2222-2222-222222222222', 'ee222222-2222-2222-2222-222222222222', 'd5555555-5555-5555-5555-555555555555', 'c2222222-2222-2222-2222-222222222222', 'e3333333-3333-3333-3333-333333333333', 'contact5@example.com', 'sent', 'ses-msg-002', NULL, NOW() - INTERVAL '2 days' + INTERVAL '1 minute', NOW() - INTERVAL '2 days' + INTERVAL '1 minute')
ON CONFLICT (id) DO NOTHING;