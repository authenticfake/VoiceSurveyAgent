-- Idempotent reference data (10 statements between inserts).
INSERT INTO users (id, oidc_sub, email, name, role)
VALUES ('00000000-0000-0000-0000-000000000001', 'admin-oidc', 'admin@example.com', 'System Admin', 'admin')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, email = EXCLUDED.email, updated_at = NOW();

INSERT INTO provider_configurations (
    id, provider_type, provider_name, outbound_number, max_concurrent_calls,
    llm_provider, llm_model, recording_retention_days, transcript_retention_days
) VALUES (
    '00000000-0000-0000-0000-000000000010', 'telephony_api', 'twilio', '+12065550100',
    10, 'openai', 'gpt-4.1-mini', 180, 180
) ON CONFLICT (provider_type) DO UPDATE SET
    provider_name = EXCLUDED.provider_name,
    outbound_number = EXCLUDED.outbound_number,
    max_concurrent_calls = EXCLUDED.max_concurrent_calls,
    llm_provider = EXCLUDED.llm_provider,
    llm_model = EXCLUDED.llm_model,
    recording_retention_days = EXCLUDED.recording_retention_days,
    transcript_retention_days = EXCLUDED.transcript_retention_days,
    updated_at = NOW();

INSERT INTO email_templates (id, name, type, locale, subject, body_html)
VALUES (
    '10000000-0000-0000-0000-000000000001', 'Completed EN', 'completed', 'en',
    'Thank you for your time', '<p>Thank you for completing our survey.</p>'
) ON CONFLICT (type, locale) DO UPDATE SET subject = EXCLUDED.subject, body_html = EXCLUDED.body_html, updated_at = NOW();

INSERT INTO email_templates (id, name, type, locale, subject, body_html)
VALUES (
    '10000000-0000-0000-0000-000000000002', 'Completed IT', 'completed', 'it',
    'Grazie per il tuo tempo', '<p>Grazie per aver completato il nostro sondaggio.</p>'
) ON CONFLICT (type, locale) DO UPDATE SET subject = EXCLUDED.subject, body_html = EXCLUDED.body_html, updated_at = NOW();

INSERT INTO email_templates (id, name, type, locale, subject, body_html)
VALUES (
    '10000000-0000-0000-0000-000000000003', 'Refused EN', 'refused', 'en',
    'We have recorded your preference', '<p>We will not contact you again regarding this survey.</p>'
) ON CONFLICT (type, locale) DO UPDATE SET subject = EXCLUDED.subject, body_html = EXCLUDED.body_html, updated_at = NOW();

INSERT INTO email_templates (id, name, type, locale, subject, body_html)
VALUES (
    '10000000-0000-0000-0000-000000000004', 'Refused IT', 'refused', 'it',
    'Abbiamo registrato la tua preferenza', '<p>Non ti contatteremo più per questo sondaggio.</p>'
) ON CONFLICT (type, locale) DO UPDATE SET subject = EXCLUDED.subject, body_html = EXCLUDED.body_html, updated_at = NOW();

INSERT INTO email_templates (id, name, type, locale, subject, body_html)
VALUES (
    '10000000-0000-0000-0000-000000000005', 'Not Reached EN', 'not_reached', 'en',
    'We could not reach you', '<p>Sorry we missed you. Let us know if you prefer another time.</p>'
) ON CONFLICT (type, locale) DO UPDATE SET subject = EXCLUDED.subject, body_html = EXCLUDED.body_html, updated_at = NOW();

INSERT INTO email_templates (id, name, type, locale, subject, body_html)
VALUES (
    '10000000-0000-0000-0000-000000000006', 'Not Reached IT', 'not_reached', 'it',
    'Non siamo riusciti a contattarti', '<p>Spiacenti di non averti raggiunto. Facci sapere se preferisci un altro orario.</p>'
) ON CONFLICT (type, locale) DO UPDATE SET subject = EXCLUDED.subject, body_html = EXCLUDED.body_html, updated_at = NOW();

INSERT INTO exclusion_list_entries (id, phone_number, reason, source)
VALUES ('20000000-0000-0000-0000-000000000001', '+15555550100', 'Prior opt-out', 'import')
ON CONFLICT (phone_number) DO UPDATE SET reason = EXCLUDED.reason, source = EXCLUDED.source, updated_at = NOW();

INSERT INTO exclusion_list_entries (id, phone_number, reason, source)
VALUES ('20000000-0000-0000-0000-000000000002', '+15555550101', 'Regulatory block', 'manual')
ON CONFLICT (phone_number) DO UPDATE SET reason = EXCLUDED.reason, source = EXCLUDED.source, updated_at = NOW();