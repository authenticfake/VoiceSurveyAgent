--
-- PostgreSQL database dump
--

-- Dumped from database version 14.5
-- Dumped by pg_dump version 14.4

-- Started on 2025-12-31 18:19:34 CET

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 4365 (class 0 OID 110978)
-- Dependencies: 219
-- Data for Name: email_templates; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.email_templates (id, name, type, subject, body_html, body_text, locale, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4364 (class 0 OID 110961)
-- Dependencies: 218
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.users (id, oidc_sub, email, name, role, created_at, updated_at) FROM stdin;
4ae6e899-be1c-4d61-803b-9771df64616f	732a1429-d843-411f-8672-f8c0409fa7cf	manager@voicesurveyagent.ai	Manager Campaigns	campaign_manager	2025-12-22 12:52:07.420728+01	2025-12-22 12:57:34.894181+01
4b2e232f-9cf0-4dee-adb0-23dafd60540b	test-sub-d69af049-3baf-422f-aaaf-1f93026395d8	tester-983bd43b-7e53-446f-bb53-acdf91db0460@example.com	Test User	viewer	2025-12-20 14:47:19.983108+01	2025-12-20 14:47:19.983108+01
0e9f1267-7b8e-498d-8acf-4da4c76ae317	d254e6da-83a9-4800-9d0d-c184ef07ceca	authenticfake@hotmail.com	Andrea Franco	admin	2025-12-21 17:12:31.01204+01	2025-12-22 12:57:34.894181+01
93c8a1e8-ca3e-4dbe-a71f-d68c373fec3e	2048205d-70a9-4c85-92d5-d5e12bf0c6a6	viewer@voicesurveyagent.ai	Viewer Campaigns	viewer	2025-12-22 12:54:47.535936+01	2025-12-22 12:57:34.894181+01
\.


--
-- TOC entry 4366 (class 0 OID 110991)
-- Dependencies: 220
-- Data for Name: campaigns; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at, completion_message) FROM stdin;
53fd9acd-af11-4a76-83e7-4b8dc1c8c530	Smoke Campaign	Local test	running	it	Ciao, sono l’assistente. Vuoi dare il consenso a partecipare a un breve sondaggio?	Come stai oggi?	free_text	Da 1 a 5 quanto sei soddisfatto?	scale	Vuoi aggiungere un commento finale?	free_text	2	30	00:00:00	23:59:59	\N	\N	\N	4ae6e899-be1c-4d61-803b-9771df64616f	2025-12-25 20:54:37.829626+01	2025-12-29 00:01:29.840164+01	Grazie, abbiamo finito.
\.


--
-- TOC entry 4367 (class 0 OID 111034)
-- Dependencies: 221
-- Data for Name: contacts; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at) FROM stdin;
b347d095-0015-43df-a984-fa3d159a3dae	53fd9acd-af11-4a76-83e7-4b8dc1c8c530	\N	+393289894333	\N	it	f	f	not_reached	2	2025-12-31 15:25:59.832312+01	completed	2025-12-25 20:55:56.940347+01	2025-12-31 15:49:15.317985+01
\.


--
-- TOC entry 4369 (class 0 OID 111073)
-- Dependencies: 223
-- Data for Name: call_attempts; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, answered_at, ended_at, outcome, provider_raw_status, error_code, metadata) FROM stdin;
e36c7cbb-9ecd-4dba-b363-59559d4d03d4	b347d095-0015-43df-a984-fa3d159a3dae	53fd9acd-af11-4a76-83e7-4b8dc1c8c530	1	73f29ac6-85f3-4b1b-8298-3bba5589105d	CA550229831fe162b8cc8e5157a863fb4b	2025-12-31 14:52:48.403607+01	2025-12-31 14:52:54.840958+01	2025-12-31 14:54:59.671629+01	\N	completed	\N	{"to": "+393289894333", "sid": "CA550229831fe162b8cc8e5157a863fb4b", "uri": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b.json", "from": "+15707156821", "price": null, "status": "queued", "duration": null, "end_time": null, "direction": "outbound-api", "group_sid": null, "trunk_sid": null, "annotation": null, "price_unit": "USD", "queue_time": "0", "start_time": null, "account_sid": "ACdaed056a0aac584fafc6a09861d56b07", "answered_by": null, "api_version": "2010-04-01", "caller_name": null, "date_created": null, "date_updated": null, "to_formatted": "+393289894333", "forwarded_from": null, "from_formatted": "(570) 715-6821", "parent_call_sid": null, "duration_seconds": 125, "phone_number_sid": "PNe9b8ff0fac553c89c2e88a1aacaa9bc8", "processed_events": {"call.ringing": true, "call.answered": true, "call.completed": true, "call.initiated": true}, "subresource_uris": {"events": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b/Events.json", "siprec": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b/Siprec.json", "streams": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b/Streams.json", "payments": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b/Payments.json", "recordings": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b/Recordings.json", "notifications": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b/Notifications.json", "transcriptions": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b/Transcriptions.json", "user_defined_messages": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b/UserDefinedMessages.json", "user_defined_message_subscriptions": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CA550229831fe162b8cc8e5157a863fb4b/UserDefinedMessageSubscriptions.json"}}
4afe5415-ef44-46c2-9d62-c47b9c2fcee6	b347d095-0015-43df-a984-fa3d159a3dae	53fd9acd-af11-4a76-83e7-4b8dc1c8c530	2	57c68e7e-f740-4ffb-b75d-3cfb9240b3bf	CAc3250efbb238e9e374ec4f888d0fcbef	2025-12-31 15:25:59.930316+01	\N	\N	\N	queued	\N	{"to": "+393289894333", "sid": "CAc3250efbb238e9e374ec4f888d0fcbef", "uri": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef.json", "from": "+15707156821", "price": null, "status": "queued", "duration": null, "end_time": null, "direction": "outbound-api", "group_sid": null, "trunk_sid": null, "annotation": null, "price_unit": "USD", "queue_time": "0", "start_time": null, "account_sid": "ACdaed056a0aac584fafc6a09861d56b07", "answered_by": null, "api_version": "2010-04-01", "caller_name": null, "date_created": null, "date_updated": null, "to_formatted": "+393289894333", "forwarded_from": null, "from_formatted": "(570) 715-6821", "parent_call_sid": null, "phone_number_sid": "PNe9b8ff0fac553c89c2e88a1aacaa9bc8", "subresource_uris": {"events": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef/Events.json", "siprec": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef/Siprec.json", "streams": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef/Streams.json", "payments": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef/Payments.json", "recordings": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef/Recordings.json", "notifications": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef/Notifications.json", "transcriptions": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef/Transcriptions.json", "user_defined_messages": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef/UserDefinedMessages.json", "user_defined_message_subscriptions": "/2010-04-01/Accounts/ACdaed056a0aac584fafc6a09861d56b07/Calls/CAc3250efbb238e9e374ec4f888d0fcbef/UserDefinedMessageSubscriptions.json"}}
\.


--
-- TOC entry 4371 (class 0 OID 111135)
-- Dependencies: 225
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.events (id, event_type, campaign_id, contact_id, call_attempt_id, payload, created_at) FROM stdin;
\.


--
-- TOC entry 4372 (class 0 OID 111165)
-- Dependencies: 226
-- Data for Name: email_notifications; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.email_notifications (id, event_id, contact_id, campaign_id, template_id, to_email, status, provider_message_id, error_message, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4368 (class 0 OID 111060)
-- Dependencies: 222
-- Data for Name: exclusion_list_entries; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.exclusion_list_entries (id, phone_number, reason, source, created_at) FROM stdin;
\.


--
-- TOC entry 4373 (class 0 OID 111201)
-- Dependencies: 227
-- Data for Name: provider_configs; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.provider_configs (id, provider_type, provider_name, outbound_number, max_concurrent_calls, llm_provider, llm_model, recording_retention_days, transcript_retention_days, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4375 (class 0 OID 111242)
-- Dependencies: 229
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.schema_migrations (version, checksum, applied_at, status) FROM stdin;
V0001	initial_schema_v1	2025-12-18 14:26:45.907996+01	applied
\.


--
-- TOC entry 4370 (class 0 OID 111102)
-- Dependencies: 224
-- Data for Name: survey_responses; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.survey_responses (id, contact_id, campaign_id, call_attempt_id, q1_answer, q2_answer, q3_answer, q1_confidence, q2_confidence, q3_confidence, completed_at) FROM stdin;
\.


--
-- TOC entry 4374 (class 0 OID 111219)
-- Dependencies: 228
-- Data for Name: transcript_snippets; Type: TABLE DATA; Schema: public; Owner: afranco
--

COPY public.transcript_snippets (id, call_attempt_id, transcript_text, language, created_at) FROM stdin;
\.


--
-- TOC entry 4397 (class 0 OID 128998)
-- Dependencies: 251
-- Data for Name: email_templates; Type: TABLE DATA; Schema: req008_66381ec0bd1140dc99502acccac265e9; Owner: afranco
--

COPY req008_66381ec0bd1140dc99502acccac265e9.email_templates (id, name, subject, body) FROM stdin;
\.


--
-- TOC entry 4396 (class 0 OID 128987)
-- Dependencies: 250
-- Data for Name: users; Type: TABLE DATA; Schema: req008_66381ec0bd1140dc99502acccac265e9; Owner: afranco
--

COPY req008_66381ec0bd1140dc99502acccac265e9.users (id, oidc_sub, email, name, role, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4398 (class 0 OID 129005)
-- Dependencies: 252
-- Data for Name: campaigns; Type: TABLE DATA; Schema: req008_66381ec0bd1140dc99502acccac265e9; Owner: afranco
--

COPY req008_66381ec0bd1140dc99502acccac265e9.campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4399 (class 0 OID 129038)
-- Dependencies: 253
-- Data for Name: contacts; Type: TABLE DATA; Schema: req008_66381ec0bd1140dc99502acccac265e9; Owner: afranco
--

COPY req008_66381ec0bd1140dc99502acccac265e9.contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4400 (class 0 OID 129056)
-- Dependencies: 254
-- Data for Name: call_attempts; Type: TABLE DATA; Schema: req008_66381ec0bd1140dc99502acccac265e9; Owner: afranco
--

COPY req008_66381ec0bd1140dc99502acccac265e9.call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, ended_at, outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4412 (class 0 OID 129950)
-- Dependencies: 266
-- Data for Name: email_templates; Type: TABLE DATA; Schema: req008_776ddef2b87846ff983f159fe179d141; Owner: afranco
--

COPY req008_776ddef2b87846ff983f159fe179d141.email_templates (id, name, subject, body) FROM stdin;
\.


--
-- TOC entry 4411 (class 0 OID 129939)
-- Dependencies: 265
-- Data for Name: users; Type: TABLE DATA; Schema: req008_776ddef2b87846ff983f159fe179d141; Owner: afranco
--

COPY req008_776ddef2b87846ff983f159fe179d141.users (id, oidc_sub, email, name, role, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4413 (class 0 OID 129957)
-- Dependencies: 267
-- Data for Name: campaigns; Type: TABLE DATA; Schema: req008_776ddef2b87846ff983f159fe179d141; Owner: afranco
--

COPY req008_776ddef2b87846ff983f159fe179d141.campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4414 (class 0 OID 129990)
-- Dependencies: 268
-- Data for Name: contacts; Type: TABLE DATA; Schema: req008_776ddef2b87846ff983f159fe179d141; Owner: afranco
--

COPY req008_776ddef2b87846ff983f159fe179d141.contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4415 (class 0 OID 130008)
-- Dependencies: 269
-- Data for Name: call_attempts; Type: TABLE DATA; Schema: req008_776ddef2b87846ff983f159fe179d141; Owner: afranco
--

COPY req008_776ddef2b87846ff983f159fe179d141.call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, ended_at, outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4402 (class 0 OID 129604)
-- Dependencies: 256
-- Data for Name: email_templates; Type: TABLE DATA; Schema: req008_790828377d6b4813bbdc38ac0f230b1b; Owner: afranco
--

COPY req008_790828377d6b4813bbdc38ac0f230b1b.email_templates (id, name, subject, body) FROM stdin;
\.


--
-- TOC entry 4401 (class 0 OID 129593)
-- Dependencies: 255
-- Data for Name: users; Type: TABLE DATA; Schema: req008_790828377d6b4813bbdc38ac0f230b1b; Owner: afranco
--

COPY req008_790828377d6b4813bbdc38ac0f230b1b.users (id, oidc_sub, email, name, role, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4403 (class 0 OID 129611)
-- Dependencies: 257
-- Data for Name: campaigns; Type: TABLE DATA; Schema: req008_790828377d6b4813bbdc38ac0f230b1b; Owner: afranco
--

COPY req008_790828377d6b4813bbdc38ac0f230b1b.campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4404 (class 0 OID 129644)
-- Dependencies: 258
-- Data for Name: contacts; Type: TABLE DATA; Schema: req008_790828377d6b4813bbdc38ac0f230b1b; Owner: afranco
--

COPY req008_790828377d6b4813bbdc38ac0f230b1b.contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4405 (class 0 OID 129662)
-- Dependencies: 259
-- Data for Name: call_attempts; Type: TABLE DATA; Schema: req008_790828377d6b4813bbdc38ac0f230b1b; Owner: afranco
--

COPY req008_790828377d6b4813bbdc38ac0f230b1b.call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, ended_at, outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4377 (class 0 OID 128306)
-- Dependencies: 231
-- Data for Name: email_templates; Type: TABLE DATA; Schema: req008_8235e58edfc644c39cfedd5a9e2b4f61; Owner: afranco
--

COPY req008_8235e58edfc644c39cfedd5a9e2b4f61.email_templates (id, name, subject, body) FROM stdin;
\.


--
-- TOC entry 4376 (class 0 OID 128295)
-- Dependencies: 230
-- Data for Name: users; Type: TABLE DATA; Schema: req008_8235e58edfc644c39cfedd5a9e2b4f61; Owner: afranco
--

COPY req008_8235e58edfc644c39cfedd5a9e2b4f61.users (id, oidc_sub, email, name, role, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4378 (class 0 OID 128313)
-- Dependencies: 232
-- Data for Name: campaigns; Type: TABLE DATA; Schema: req008_8235e58edfc644c39cfedd5a9e2b4f61; Owner: afranco
--

COPY req008_8235e58edfc644c39cfedd5a9e2b4f61.campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4379 (class 0 OID 128346)
-- Dependencies: 233
-- Data for Name: contacts; Type: TABLE DATA; Schema: req008_8235e58edfc644c39cfedd5a9e2b4f61; Owner: afranco
--

COPY req008_8235e58edfc644c39cfedd5a9e2b4f61.contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4380 (class 0 OID 128364)
-- Dependencies: 234
-- Data for Name: call_attempts; Type: TABLE DATA; Schema: req008_8235e58edfc644c39cfedd5a9e2b4f61; Owner: afranco
--

COPY req008_8235e58edfc644c39cfedd5a9e2b4f61.call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, ended_at, outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4387 (class 0 OID 128652)
-- Dependencies: 241
-- Data for Name: email_templates; Type: TABLE DATA; Schema: req008_b227e488c740425eafefc63df6e36af7; Owner: afranco
--

COPY req008_b227e488c740425eafefc63df6e36af7.email_templates (id, name, subject, body) FROM stdin;
\.


--
-- TOC entry 4386 (class 0 OID 128641)
-- Dependencies: 240
-- Data for Name: users; Type: TABLE DATA; Schema: req008_b227e488c740425eafefc63df6e36af7; Owner: afranco
--

COPY req008_b227e488c740425eafefc63df6e36af7.users (id, oidc_sub, email, name, role, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4388 (class 0 OID 128659)
-- Dependencies: 242
-- Data for Name: campaigns; Type: TABLE DATA; Schema: req008_b227e488c740425eafefc63df6e36af7; Owner: afranco
--

COPY req008_b227e488c740425eafefc63df6e36af7.campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4389 (class 0 OID 128692)
-- Dependencies: 243
-- Data for Name: contacts; Type: TABLE DATA; Schema: req008_b227e488c740425eafefc63df6e36af7; Owner: afranco
--

COPY req008_b227e488c740425eafefc63df6e36af7.contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4390 (class 0 OID 128710)
-- Dependencies: 244
-- Data for Name: call_attempts; Type: TABLE DATA; Schema: req008_b227e488c740425eafefc63df6e36af7; Owner: afranco
--

COPY req008_b227e488c740425eafefc63df6e36af7.call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, ended_at, outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4407 (class 0 OID 129778)
-- Dependencies: 261
-- Data for Name: email_templates; Type: TABLE DATA; Schema: req008_bb83924b05e34855a95c57c1df2571f3; Owner: afranco
--

COPY req008_bb83924b05e34855a95c57c1df2571f3.email_templates (id, name, subject, body) FROM stdin;
\.


--
-- TOC entry 4406 (class 0 OID 129767)
-- Dependencies: 260
-- Data for Name: users; Type: TABLE DATA; Schema: req008_bb83924b05e34855a95c57c1df2571f3; Owner: afranco
--

COPY req008_bb83924b05e34855a95c57c1df2571f3.users (id, oidc_sub, email, name, role, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4408 (class 0 OID 129785)
-- Dependencies: 262
-- Data for Name: campaigns; Type: TABLE DATA; Schema: req008_bb83924b05e34855a95c57c1df2571f3; Owner: afranco
--

COPY req008_bb83924b05e34855a95c57c1df2571f3.campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4409 (class 0 OID 129818)
-- Dependencies: 263
-- Data for Name: contacts; Type: TABLE DATA; Schema: req008_bb83924b05e34855a95c57c1df2571f3; Owner: afranco
--

COPY req008_bb83924b05e34855a95c57c1df2571f3.contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4410 (class 0 OID 129836)
-- Dependencies: 264
-- Data for Name: call_attempts; Type: TABLE DATA; Schema: req008_bb83924b05e34855a95c57c1df2571f3; Owner: afranco
--

COPY req008_bb83924b05e34855a95c57c1df2571f3.call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, ended_at, outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4392 (class 0 OID 128826)
-- Dependencies: 246
-- Data for Name: email_templates; Type: TABLE DATA; Schema: req008_ef6866ac564a4e20a9c60a92e6ac1e37; Owner: afranco
--

COPY req008_ef6866ac564a4e20a9c60a92e6ac1e37.email_templates (id, name, subject, body) FROM stdin;
\.


--
-- TOC entry 4391 (class 0 OID 128815)
-- Dependencies: 245
-- Data for Name: users; Type: TABLE DATA; Schema: req008_ef6866ac564a4e20a9c60a92e6ac1e37; Owner: afranco
--

COPY req008_ef6866ac564a4e20a9c60a92e6ac1e37.users (id, oidc_sub, email, name, role, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4393 (class 0 OID 128833)
-- Dependencies: 247
-- Data for Name: campaigns; Type: TABLE DATA; Schema: req008_ef6866ac564a4e20a9c60a92e6ac1e37; Owner: afranco
--

COPY req008_ef6866ac564a4e20a9c60a92e6ac1e37.campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4394 (class 0 OID 128866)
-- Dependencies: 248
-- Data for Name: contacts; Type: TABLE DATA; Schema: req008_ef6866ac564a4e20a9c60a92e6ac1e37; Owner: afranco
--

COPY req008_ef6866ac564a4e20a9c60a92e6ac1e37.contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4395 (class 0 OID 128884)
-- Dependencies: 249
-- Data for Name: call_attempts; Type: TABLE DATA; Schema: req008_ef6866ac564a4e20a9c60a92e6ac1e37; Owner: afranco
--

COPY req008_ef6866ac564a4e20a9c60a92e6ac1e37.call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, ended_at, outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4382 (class 0 OID 128478)
-- Dependencies: 236
-- Data for Name: email_templates; Type: TABLE DATA; Schema: req008_fe170bb7aaed4718b07b4c8915a46a1e; Owner: afranco
--

COPY req008_fe170bb7aaed4718b07b4c8915a46a1e.email_templates (id, name, subject, body) FROM stdin;
\.


--
-- TOC entry 4381 (class 0 OID 128467)
-- Dependencies: 235
-- Data for Name: users; Type: TABLE DATA; Schema: req008_fe170bb7aaed4718b07b4c8915a46a1e; Owner: afranco
--

COPY req008_fe170bb7aaed4718b07b4c8915a46a1e.users (id, oidc_sub, email, name, role, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4383 (class 0 OID 128485)
-- Dependencies: 237
-- Data for Name: campaigns; Type: TABLE DATA; Schema: req008_fe170bb7aaed4718b07b4c8915a46a1e; Owner: afranco
--

COPY req008_fe170bb7aaed4718b07b4c8915a46a1e.campaigns (id, name, description, status, language, intro_script, question_1_text, question_1_type, question_2_text, question_2_type, question_3_text, question_3_type, max_attempts, retry_interval_minutes, allowed_call_start_local, allowed_call_end_local, email_completed_template_id, email_refused_template_id, email_not_reached_template_id, created_by_user_id, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4384 (class 0 OID 128518)
-- Dependencies: 238
-- Data for Name: contacts; Type: TABLE DATA; Schema: req008_fe170bb7aaed4718b07b4c8915a46a1e; Owner: afranco
--

COPY req008_fe170bb7aaed4718b07b4c8915a46a1e.contacts (id, campaign_id, external_contact_id, phone_number, email, preferred_language, has_prior_consent, do_not_call, state, attempts_count, last_attempt_at, last_outcome, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 4385 (class 0 OID 128536)
-- Dependencies: 239
-- Data for Name: call_attempts; Type: TABLE DATA; Schema: req008_fe170bb7aaed4718b07b4c8915a46a1e; Owner: afranco
--

COPY req008_fe170bb7aaed4718b07b4c8915a46a1e.call_attempts (id, contact_id, campaign_id, attempt_number, call_id, provider_call_id, started_at, ended_at, outcome, created_at, updated_at) FROM stdin;
\.


-- Completed on 2025-12-31 18:19:35 CET

--
-- PostgreSQL database dump complete
--

