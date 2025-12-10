-- seed.sql - Idempotent seed data for REQ-022 retention jobs
-- Provides sample GDPR requests and retention job history for testing

-- ============================================================================
-- SEED GDPR DELETION REQUESTS (10 records)
-- ============================================================================

INSERT INTO gdpr_deletion_requests (id, contact_id, contact_phone, contact_email, requested_at, deadline, status, processed_at, items_deleted, error_message)
VALUES
    ('gd111111-1111-1111-1111-111111111111', 'd1111111-1111-1111-1111-111111111111', '+14155551001', 'contact1@example.com', NOW() - INTERVAL '1 day', NOW() + INTERVAL '2 days', 'pending', NULL, 0, NULL),
    ('gd222222-2222-2222-2222-222222222222', 'd2222222-2222-2222-2222-222222222222', '+14155551002', 'contact2@example.com', NOW() - INTERVAL '2 days', NOW() + INTERVAL '1 day', 'pending', NULL, 0, NULL),
    ('gd333333-3333-3333-3333-333333333333', 'd3333333-3333-3333-3333-333333333333', '+14155551003', 'contact3@example.com', NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 hour', 'pending', NULL, 0, NULL),
    ('gd444444-4444-4444-4444-444444444444', 'd4444444-4444-4444-4444-444444444444', '+14155551004', 'contact4@example.com', NOW() - INTERVAL '5 days', NOW() - INTERVAL '2 days', 'completed', NOW() - INTERVAL '4 days', 15, NULL),
    ('gd555555-5555-5555-5555-555555555555', 'd5555555-5555-5555-5555-555555555555', '+14155551005', 'contact5@example.com', NOW() - INTERVAL '4 days', NOW() - INTERVAL '1 day', 'completed', NOW() - INTERVAL '3 days', 8, NULL),
    ('gd666666-6666-6666-6666-666666666666', 'd6666666-6666-6666-6666-666666666666', '+14155551006', NULL, NOW() - INTERVAL '6 days', NOW() - INTERVAL '3 days', 'failed', NOW() - INTERVAL '5 days', 0, 'Contact not found'),
    ('gd777777-7777-7777-7777-777777777777', 'd7777777-7777-7777-7777-777777777777', NULL, 'contact7@example.com', NOW() - INTERVAL '12 hours', NOW() + INTERVAL '60 hours', 'processing', NULL, 0, NULL),
    ('gd888888-8888-8888-8888-888888888888', 'd8888888-8888-8888-8888-888888888888', '+393331234567', 'contact8@example.it', NOW() - INTERVAL '2 hours', NOW() + INTERVAL '70 hours', 'pending', NULL, 0, NULL),
    ('gd999999-9999-9999-9999-999999999999', 'd9999999-9999-9999-9999-999999999999', '+393339876543', NULL, NOW() - INTERVAL '30 minutes', NOW() + INTERVAL '71 hours 30 minutes', 'pending', NULL, 0, NULL),
    ('gdaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'daaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '+14155551010', 'contact10@example.com', NOW() - INTERVAL '7 days', NOW() - INTERVAL '4 days', 'completed', NOW() - INTERVAL '6 days', 22, NULL)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED RETENTION JOB HISTORY (15 records)
-- ============================================================================

INSERT INTO retention_job_history (id, started_at, completed_at, status, recordings_deleted, recordings_failed, transcripts_deleted, transcripts_failed, total_deleted, total_failed, error_message)
VALUES
    ('rj111111-1111-1111-1111-111111111111', NOW() - INTERVAL '1 day' + TIME '02:00', NOW() - INTERVAL '1 day' + TIME '02:05', 'completed', 45, 0, 38, 0, 83, 0, NULL),
    ('rj222222-2222-2222-2222-222222222222', NOW() - INTERVAL '2 days' + TIME '02:00', NOW() - INTERVAL '2 days' + TIME '02:03', 'completed', 12, 0, 15, 0, 27, 0, NULL),
    ('rj333333-3333-3333-3333-333333333333', NOW() - INTERVAL '3 days' + TIME '02:00', NOW() - INTERVAL '3 days' + TIME '02:08', 'completed', 67, 2, 54, 1, 121, 3, NULL),
    ('rj444444-4444-4444-4444-444444444444', NOW() - INTERVAL '4 days' + TIME '02:00', NOW() - INTERVAL '4 days' + TIME '02:02', 'completed', 8, 0, 5, 0, 13, 0, NULL),
    ('rj555555-5555-5555-5555-555555555555', NOW() - INTERVAL '5 days' + TIME '02:00', NOW() - INTERVAL '5 days' + TIME '02:15', 'partial', 89, 5, 72, 3, 161, 8, 'Some S3 objects not found'),
    ('rj666666-6666-6666-6666-666666666666', NOW() - INTERVAL '6 days' + TIME '02:00', NOW() - INTERVAL '6 days' + TIME '02:04', 'completed', 23, 0, 19, 0, 42, 0, NULL),
    ('rj777777-7777-7777-7777-777777777777', NOW() - INTERVAL '7 days' + TIME '02:00', NOW() - INTERVAL '7 days' + TIME '02:06', 'completed', 31, 0, 28, 0, 59, 0, NULL),
    ('rj888888-8888-8888-8888-888888888888', NOW() - INTERVAL '8 days' + TIME '02:00', NOW() - INTERVAL '8 days' + TIME '02:01', 'completed', 0, 0, 0, 0, 0, 0, NULL),
    ('rj999999-9999-9999-9999-999999999999', NOW() - INTERVAL '9 days' + TIME '02:00', NOW() - INTERVAL '9 days' + TIME '02:12', 'failed', 0, 15, 0, 12, 0, 27, 'Database connection timeout'),
    ('rjaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', NOW() - INTERVAL '10 days' + TIME '02:00', NOW() - INTERVAL '10 days' + TIME '02:07', 'completed', 56, 0, 43, 0, 99, 0, NULL),
    ('rjbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', NOW() - INTERVAL '11 days' + TIME '02:00', NOW() - INTERVAL '11 days' + TIME '02:09', 'completed', 78, 1, 65, 0, 143, 1, NULL),
    ('rjcccccc-cccc-cccc-cccc-cccccccccccc', NOW() - INTERVAL '12 days' + TIME '02:00', NOW() - INTERVAL '12 days' + TIME '02:04', 'completed', 34, 0, 29, 0, 63, 0, NULL),
    ('rjdddddd-dddd-dddd-dddd-dddddddddddd', NOW() - INTERVAL '13 days' + TIME '02:00', NOW() - INTERVAL '13 days' + TIME '02:11', 'completed', 91, 0, 84, 0, 175, 0, NULL),
    ('rjeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', NOW() - INTERVAL '14 days' + TIME '02:00', NOW() - INTERVAL '14 days' + TIME '02:03', 'completed', 17, 0, 14, 0, 31, 0, NULL),
    ('rjffffff-ffff-ffff-ffff-ffffffffffff', NOW() - INTERVAL '15 days' + TIME '02:00', NOW() - INTERVAL '15 days' + TIME '02:05', 'completed', 42, 0, 37, 0, 79, 0, NULL)
ON CONFLICT (id) DO NOTHING;