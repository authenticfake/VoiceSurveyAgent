# PLAN — voicesurveyagent

## Plan Snapshot

- **Counts:** total=11 / open=6 / in_progress=4 / done=1 / deferred=0
- **Progress:** 9% complete
- **Checklist:**
  - [x] SPEC aligned
  - [x] Prior REQ reconciled
  - [x] Dependencies mapped
  - [x] KIT-readiness per REQ confirmed

## Tracks & Scope Boundaries

- **Tracks:**
  - App: Auth, campaigns, contacts, telephony integration, dialogue outcomes, events, email worker, dashboards, admin config, web console.
  - Infra: Database schema/migrations, messaging scaffolding, deployment primitives for workers and scheduler.
- **Scope focus (slice‑1):**
  - Single-tenant, single outbound campaign model, one telephony/voice AI provider, three fixed questions.
  - Backend REST APIs, minimal but usable React/Next.js console for core flows.
- **Out of scope / Deferred:**
  - Multiple telephony providers, advanced branching or more than 3 questions.
  - Advanced analytics/BI, complex CRM integrations, multi-tenant support.
  - Full production‑grade CI/CD pipelines and EKS IaC (only minimal infra scaffolding in this plan).

## Module/Package & Namespace Plan

Canonical backend root: `app` (Python, FastAPI). Canonical frontend root: `web` (Next.js/React).

Slices and layering (App track):

- **auth**
  - Domain: users, roles, OIDC session handling.
  - Namespaces:
    - `app.auth.domain` – user and role models, RBAC policies.
    - `app.auth.oidc` – OIDC integration helpers.
    - `app.api.http.auth` – auth-related FastAPI routers and dependencies.
- **campaigns**
  - Domain: campaigns, lifecycle, validation.
  - Namespaces:
    - `app.campaigns.domain`
    - `app.campaigns.services`
    - `app.api.http.campaigns`
- **contacts**
  - Domain: contacts, CSV ingestion, exclusion lists.
  - Namespaces:
    - `app.contacts.domain`
    - `app.contacts.csv_import`
    - `app.api.http.contacts`
- **calling**
  - Domain: call scheduling, attempts, telephony provider, dialogue outcome handling.
  - Namespaces:
    - `app.calling.scheduler`
    - `app.calling.telephony`
    - `app.calling.dialogue`
    - `app.api.http.telephony_webhooks`
- **events_notifications**
  - Domain: internal survey events and email notifications.
  - Namespaces:
    - `app.events.bus`
    - `app.notifications.email`
- **reporting**
  - Domain: dashboards, stats, CSV export.
  - Namespaces:
    - `app.reporting.stats`
    - `app.reporting.export`
    - `app.api.http.reporting`
- **admin**
  - Domain: provider and LLM config, retention settings, admin actions.
  - Namespaces:
    - `app.admin.domain`
    - `app.api.http.admin`
- **frontend**
  - Domain: web console UX.
  - Namespaces (frontend):
    - `web/app` – Next.js app router.
    - `web/components/*`
    - `web/lib/api` – REST client wrappers.

Infra track namespaces:

- `app.infra.db` – SQLAlchemy models and Alembic migrations.
- `app.infra.messaging` – SQS abstraction and event publishing utilities.
- `app.infra.config` – config loading, secrets integration.
- `app.infra.observability` – logging, metrics, tracing helpers.

Each REQ below specifies:

- Primary module/namespace it owns.
- Shared modules it must reuse.
- Whether it may create new modules (only within its slice) or must extend existing ones.

## REQ-IDs Table

| ID | Title | Acceptance | DependsOn | Track | Status |
|---|---|---|---|---|---|
| REQ-001 | OIDC auth and RBAC for backend APIs | OIDC login exchanges code for tokens and validates ID token<br/>RBAC middleware enforces role requirements for protected routes<br/>Unauthorized and unauthenticated requests return structured error responses<br/>Viewer campaign_manager admin roles behave per SPEC permissions<br/>Auth modules expose reusable dependencies for other routers |  | App | in_progress |
| REQ-002 | Campaign CRUD and activation rules | Campaigns can be created updated fetched with validation<br/>Lifecycle transitions enforce allowed status changes only<br/>Activation requires valid contacts scripts retry policy window<br/>Unauthorized roles cannot mutate campaign resources<br/>APIs expose filters and pagination for campaign listing | REQ-001 | App | in_progress |
| REQ-003 | Contact CSV import and exclusion handling | CSV upload parses validates rows and reports errors<br/>At least 95 percent of valid contacts are persisted<br/>DNC and exclusion entries mark contacts as excluded<br/>Contact states and attempts default values are correct<br/>Contact list endpoint exposes state and basic metadata | REQ-002 | App | in_progress |
| REQ-004 | Call scheduler and telephony provider adapter | Scheduler selects eligible contacts respecting time windows<br/>CallAttempt records created with unique call_id per attempt<br/>Telephony adapter starts outbound calls with metadata<br/>Contact state and attempts updated transactionally<br/>Concurrent calls limited by configurable max_concurrent_calls | REQ-003, REQ-009 | App | done |
| REQ-005 | Dialogue outcome handling and survey responses | Webhook endpoint receives telephony events reliably<br/>Consent outcomes stored with timestamps and final status<br/>Completed surveys persist three answers linked to attempt<br/>Contact state transitions follow outcomes and retry rules<br/>Survey events published with required payload fields | REQ-004, REQ-009 | App | open |
| REQ-006 | Event bus integration and email worker | Survey events are published to configured queue abstraction<br/>Email worker consumes events and sends templated emails<br/>EmailNotification records track send status and metadata<br/>Email sending is idempotent across retries and restarts<br/>Worker exposes metrics or logs for monitoring and debugging | REQ-005, REQ-009 | App | open |
| REQ-007 | Dashboard stats and CSV export APIs | Stats endpoint returns counts and completion refusal rates<br/>Contacts endpoint lists paginated contacts with outcomes<br/>CSV export returns required columns and no duplicates<br/>Exports exclude transcripts and unnecessary PII fields<br/>Endpoints enforce RBAC and handle missing campaigns cleanly | REQ-002, REQ-003, REQ-005, REQ-009 | App | open |
| REQ-008 | Admin configuration and retention settings APIs | Admin endpoints expose provider and retention configuration<br/>Only admin role can modify provider and retention settings<br/>Configuration changes are persisted and retrievable<br/>Invalid settings are rejected with clear validation errors<br/>Audit log entries created for configuration modifications | REQ-001, REQ-009 | App | open |
| REQ-009 | Database schema models and migrations | ORM models defined for all specified entities<br/>Alembic migrations create tables constraints and indexes<br/>Enum and foreign key relationships align with data model<br/>Migrations apply cleanly on fresh and existing databases<br/>Connection management configured with pooling and settings |  | Infra | in_progress |
| REQ-010 | Messaging and worker infra scaffolding | Messaging abstraction wraps SQS configuration and publishing<br/>Worker entrypoints implemented for scheduler and email worker<br/>Config loader reads messaging and provider settings<br/>Observability helpers configure logging metrics tracing hooks<br/>Deployment notes describe running workers on EKS | REQ-009 | Infra | open |
| REQ-011 | Web console for campaigns and monitoring | Frontend allows campaign creation editing and listing<br/>CSV upload and activation available via UI using backend APIs<br/>Dashboard pages display stats and contact lists<br/>Export controls trigger and download CSV exports<br/>RBAC enforced in UI based on user role information | REQ-001, REQ-002, REQ-003, REQ-007 | App | open |

zed and unauthenticated requests return structured error responses<br/>Viewer campaign_manager admin roles behave per SPEC permissions<br/>Auth modules expose reusable dependencies for other routers |  | App | in_progress |
| REQ-002 | Campaign CRUD and activation rules | Campaigns can be created updated fetched with validation<br/>Lifecycle transitions enforce allowed status changes only<br/>Activation requires valid contacts scripts retry policy window<br/>Unauthorized roles cannot mutate campaign resources<br/>APIs expose filters and pagination for campaign listing | REQ-001 | App | in_progress |
| REQ-003 | Contact CSV import and exclusion handling | CSV upload parses validates rows and reports errors<br/>At least 95 percent of valid contacts are persisted<br/>DNC and exclusion entries mark contacts as excluded<br/>Contact states and attempts default values are correct<br/>Contact list endpoint exposes state and basic metadata | REQ-002 | App | in_progress |
| REQ-004 | Call scheduler and telephony provider adapter | Scheduler selects eligible contacts respecting time windows<br/>CallAttempt records created with unique call_id per attempt<br/>Telephony adapter starts outbound calls with metadata<br/>Contact state and attempts updated transactionally<br/>Concurrent calls limited by configurable max_concurrent_calls | REQ-003, REQ-009 | App | in_progress |
| REQ-005 | Dialogue outcome handling and survey responses | Webhook endpoint receives telephony events reliably<br/>Consent outcomes stored with timestamps and final status<br/>Completed surveys persist three answers linked to attempt<br/>Contact state transitions follow outcomes and retry rules<br/>Survey events published with required payload fields | REQ-004, REQ-009 | App | open |
| REQ-006 | Event bus integration and email worker | Survey events are published to configured queue abstraction<br/>Email worker consumes events and sends templated emails<br/>EmailNotification records track send status and metadata<br/>Email sending is idempotent across retries and restarts<br/>Worker exposes metrics or logs for monitoring and debugging | REQ-005, REQ-009 | App | open |
| REQ-007 | Dashboard stats and CSV export APIs | Stats endpoint returns counts and completion refusal rates<br/>Contacts endpoint lists paginated contacts with outcomes<br/>CSV export returns required columns and no duplicates<br/>Exports exclude transcripts and unnecessary PII fields<br/>Endpoints enforce RBAC and handle missing campaigns cleanly | REQ-002, REQ-003, REQ-005, REQ-009 | App | open |
| REQ-008 | Admin configuration and retention settings APIs | Admin endpoints expose provider and retention configuration<br/>Only admin role can modify provider and retention settings<br/>Configuration changes are persisted and retrievable<br/>Invalid settings are rejected with clear validation errors<br/>Audit log entries created for configuration modifications | REQ-001, REQ-009 | App | open |
| REQ-009 | Database schema models and migrations | ORM models defined for all specified entities<br/>Alembic migrations create tables constraints and indexes<br/>Enum and foreign key relationships align with data model<br/>Migrations apply cleanly on fresh and existing databases<br/>Connection management configured with pooling and settings |  | Infra | in_progress |
| REQ-010 | Messaging and worker infra scaffolding | Messaging abstraction wraps SQS configuration and publishing<br/>Worker entrypoints implemented for scheduler and email worker<br/>Config loader reads messaging and provider settings<br/>Observability helpers configure logging metrics tracing hooks<br/>Deployment notes describe running workers on EKS | REQ-009 | Infra | open |
| REQ-011 | Web console for campaigns and monitoring | Frontend allows campaign creation editing and listing<br/>CSV upload and activation available via UI using backend APIs<br/>Dashboard pages display stats and contact lists<br/>Export controls trigger and download CSV exports<br/>RBAC enforced in UI based on user role information | REQ-001, REQ-002, REQ-003, REQ-007 | App | open |

zed and unauthenticated requests return structured error responses<br/>Viewer campaign_manager admin roles behave per SPEC permissions<br/>Auth modules expose reusable dependencies for other routers |  | App | in_progress |
| REQ-002 | Campaign CRUD and activation rules | Campaigns can be created updated fetched with validation<br/>Lifecycle transitions enforce allowed status changes only<br/>Activation requires valid contacts scripts retry policy window<br/>Unauthorized roles cannot mutate campaign resources<br/>APIs expose filters and pagination for campaign listing | REQ-001 | App | in_progress |
| REQ-003 | Contact CSV import and exclusion handling | CSV upload parses validates rows and reports errors<br/>At least 95 percent of valid contacts are persisted<br/>DNC and exclusion entries mark contacts as excluded<br/>Contact states and attempts default values are correct<br/>Contact list endpoint exposes state and basic metadata | REQ-002 | App | in_progress |
| REQ-004 | Call scheduler and telephony provider adapter | Scheduler selects eligible contacts respecting time windows<br/>CallAttempt records created with unique call_id per attempt<br/>Telephony adapter starts outbound calls with metadata<br/>Contact state and attempts updated transactionally<br/>Concurrent calls limited by configurable max_concurrent_calls | REQ-003, REQ-009 | App | open |
| REQ-005 | Dialogue outcome handling and survey responses | Webhook endpoint receives telephony events reliably<br/>Consent outcomes stored with timestamps and final status<br/>Completed surveys persist three answers linked to attempt<br/>Contact state transitions follow outcomes and retry rules<br/>Survey events published with required payload fields | REQ-004, REQ-009 | App | open |
| REQ-006 | Event bus integration and email worker | Survey events are published to configured queue abstraction<br/>Email worker consumes events and sends templated emails<br/>EmailNotification records track send status and metadata<br/>Email sending is idempotent across retries and restarts<br/>Worker exposes metrics or logs for monitoring and debugging | REQ-005, REQ-009 | App | open |
| REQ-007 | Dashboard stats and CSV export APIs | Stats endpoint returns counts and completion refusal rates<br/>Contacts endpoint lists paginated contacts with outcomes<br/>CSV export returns required columns and no duplicates<br/>Exports exclude transcripts and unnecessary PII fields<br/>Endpoints enforce RBAC and handle missing campaigns cleanly | REQ-002, REQ-003, REQ-005, REQ-009 | App | open |
| REQ-008 | Admin configuration and retention settings APIs | Admin endpoints expose provider and retention configuration<br/>Only admin role can modify provider and retention settings<br/>Configuration changes are persisted and retrievable<br/>Invalid settings are rejected with clear validation errors<br/>Audit log entries created for configuration modifications | REQ-001, REQ-009 | App | open |
| REQ-009 | Database schema models and migrations | ORM models defined for all specified entities<br/>Alembic migrations create tables constraints and indexes<br/>Enum and foreign key relationships align with data model<br/>Migrations apply cleanly on fresh and existing databases<br/>Connection management configured with pooling and settings |  | Infra | in_progress |
| REQ-010 | Messaging and worker infra scaffolding | Messaging abstraction wraps SQS configuration and publishing<br/>Worker entrypoints implemented for scheduler and email worker<br/>Config loader reads messaging and provider settings<br/>Observability helpers configure logging metrics tracing hooks<br/>Deployment notes describe running workers on EKS | REQ-009 | Infra | open |
| REQ-011 | Web console for campaigns and monitoring | Frontend allows campaign creation editing and listing<br/>CSV upload and activation available via UI using backend APIs<br/>Dashboard pages display stats and contact lists<br/>Export controls trigger and download CSV exports<br/>RBAC enforced in UI based on user role information | REQ-001, REQ-002, REQ-003, REQ-007 | App | open |

zed and unauthenticated requests return structured error responses<br/>Viewer campaign_manager admin roles behave per SPEC permissions<br/>Auth modules expose reusable dependencies for other routers |  | App | in_progress |
| REQ-002 | Campaign CRUD and activation rules | Campaigns can be created updated fetched with validation<br/>Lifecycle transitions enforce allowed status changes only<br/>Activation requires valid contacts scripts retry policy window<br/>Unauthorized roles cannot mutate campaign resources<br/>APIs expose filters and pagination for campaign listing | REQ-001 | App | in_progress |
| REQ-003 | Contact CSV import and exclusion handling | CSV upload parses validates rows and reports errors<br/>At least 95 percent of valid contacts are persisted<br/>DNC and exclusion entries mark contacts as excluded<br/>Contact states and attempts default values are correct<br/>Contact list endpoint exposes state and basic metadata | REQ-002 | App | in_progress |
| REQ-004 | Call scheduler and telephony provider adapter | Scheduler selects eligible contacts respecting time windows<br/>CallAttempt records created with unique call_id per attempt<br/>Telephony adapter starts outbound calls with metadata<br/>Contact state and attempts updated transactionally<br/>Concurrent calls limited by configurable max_concurrent_calls | REQ-003, REQ-009 | App | open |
| REQ-005 | Dialogue outcome handling and survey responses | Webhook endpoint receives telephony events reliably<br/>Consent outcomes stored with timestamps and final status<br/>Completed surveys persist three answers linked to attempt<br/>Contact state transitions follow outcomes and retry rules<br/>Survey events published with required payload fields | REQ-004, REQ-009 | App | open |
| REQ-006 | Event bus integration and email worker | Survey events are published to configured queue abstraction<br/>Email worker consumes events and sends templated emails<br/>EmailNotification records track send status and metadata<br/>Email sending is idempotent across retries and restarts<br/>Worker exposes metrics or logs for monitoring and debugging | REQ-005, REQ-009 | App | open |
| REQ-007 | Dashboard stats and CSV export APIs | Stats endpoint returns counts and completion refusal rates<br/>Contacts endpoint lists paginated contacts with outcomes<br/>CSV export returns required columns and no duplicates<br/>Exports exclude transcripts and unnecessary PII fields<br/>Endpoints enforce RBAC and handle missing campaigns cleanly | REQ-002, REQ-003, REQ-005, REQ-009 | App | open |
| REQ-008 | Admin configuration and retention settings APIs | Admin endpoints expose provider and retention configuration<br/>Only admin role can modify provider and retention settings<br/>Configuration changes are persisted and retrievable<br/>Invalid settings are rejected with clear validation errors<br/>Audit log entries created for configuration modifications | REQ-001, REQ-009 | App | open |
| REQ-009 | Database schema models and migrations | ORM models defined for all specified entities<br/>Alembic migrations create tables constraints and indexes<br/>Enum and foreign key relationships align with data model<br/>Migrations apply cleanly on fresh and existing databases<br/>Connection management configured with pooling and settings |  | Infra | open |
| REQ-010 | Messaging and worker infra scaffolding | Messaging abstraction wraps SQS configuration and publishing<br/>Worker entrypoints implemented for scheduler and email worker<br/>Config loader reads messaging and provider settings<br/>Observability helpers configure logging metrics tracing hooks<br/>Deployment notes describe running workers on EKS | REQ-009 | Infra | open |
| REQ-011 | Web console for campaigns and monitoring | Frontend allows campaign creation editing and listing<br/>CSV upload and activation available via UI using backend APIs<br/>Dashboard pages display stats and contact lists<br/>Export controls trigger and download CSV exports<br/>RBAC enforced in UI based on user role information | REQ-001, REQ-002, REQ-003, REQ-007 | App | open |

zed and unauthenticated requests return structured error responses<br/>Viewer campaign_manager admin roles behave per SPEC permissions<br/>Auth modules expose reusable dependencies for other routers |  | App | in_progress |
| REQ-002 | Campaign CRUD and activation rules | Campaigns can be created updated fetched with validation<br/>Lifecycle transitions enforce allowed status changes only<br/>Activation requires valid contacts scripts retry policy window<br/>Unauthorized roles cannot mutate campaign resources<br/>APIs expose filters and pagination for campaign listing | REQ-001 | App | in_progress |
| REQ-003 | Contact CSV import and exclusion handling | CSV upload parses validates rows and reports errors<br/>At least 95 percent of valid contacts are persisted<br/>DNC and exclusion entries mark contacts as excluded<br/>Contact states and attempts default values are correct<br/>Contact list endpoint exposes state and basic metadata | REQ-002 | App | open |
| REQ-004 | Call scheduler and telephony provider adapter | Scheduler selects eligible contacts respecting time windows<br/>CallAttempt records created with unique call_id per attempt<br/>Telephony adapter starts outbound calls with metadata<br/>Contact state and attempts updated transactionally<br/>Concurrent calls limited by configurable max_concurrent_calls | REQ-003, REQ-009 | App | open |
| REQ-005 | Dialogue outcome handling and survey responses | Webhook endpoint receives telephony events reliably<br/>Consent outcomes stored with timestamps and final status<br/>Completed surveys persist three answers linked to attempt<br/>Contact state transitions follow outcomes and retry rules<br/>Survey events published with required payload fields | REQ-004, REQ-009 | App | open |
| REQ-006 | Event bus integration and email worker | Survey events are published to configured queue abstraction<br/>Email worker consumes events and sends templated emails<br/>EmailNotification records track send status and metadata<br/>Email sending is idempotent across retries and restarts<br/>Worker exposes metrics or logs for monitoring and debugging | REQ-005, REQ-009 | App | open |
| REQ-007 | Dashboard stats and CSV export APIs | Stats endpoint returns counts and completion refusal rates<br/>Contacts endpoint lists paginated contacts with outcomes<br/>CSV export returns required columns and no duplicates<br/>Exports exclude transcripts and unnecessary PII fields<br/>Endpoints enforce RBAC and handle missing campaigns cleanly | REQ-002, REQ-003, REQ-005, REQ-009 | App | open |
| REQ-008 | Admin configuration and retention settings APIs | Admin endpoints expose provider and retention configuration<br/>Only admin role can modify provider and retention settings<br/>Configuration changes are persisted and retrievable<br/>Invalid settings are rejected with clear validation errors<br/>Audit log entries created for configuration modifications | REQ-001, REQ-009 | App | open |
| REQ-009 | Database schema models and migrations | ORM models defined for all specified entities<br/>Alembic migrations create tables constraints and indexes<br/>Enum and foreign key relationships align with data model<br/>Migrations apply cleanly on fresh and existing databases<br/>Connection management configured with pooling and settings |  | Infra | open |
| REQ-010 | Messaging and worker infra scaffolding | Messaging abstraction wraps SQS configuration and publishing<br/>Worker entrypoints implemented for scheduler and email worker<br/>Config loader reads messaging and provider settings<br/>Observability helpers configure logging metrics tracing hooks<br/>Deployment notes describe running workers on EKS | REQ-009 | Infra | open |
| REQ-011 | Web console for campaigns and monitoring | Frontend allows campaign creation editing and listing<br/>CSV upload and activation available via UI using backend APIs<br/>Dashboard pages display stats and contact lists<br/>Export controls trigger and download CSV exports<br/>RBAC enforced in UI based on user role information | REQ-001, REQ-002, REQ-003, REQ-007 | App | open |

zed and unauthenticated requests return structured error responses<br/>Viewer campaign_manager admin roles behave per SPEC permissions<br/>Auth modules expose reusable dependencies for other routers |  | App | in_progress |
| REQ-002 | Campaign CRUD and activation rules | Campaigns can be created updated fetched with validation<br/>Lifecycle transitions enforce allowed status changes only<br/>Activation requires valid contacts scripts retry policy window<br/>Unauthorized roles cannot mutate campaign resources<br/>APIs expose filters and pagination for campaign listing | REQ-001 | App | open |
| REQ-003 | Contact CSV import and exclusion handling | CSV upload parses validates rows and reports errors<br/>At least 95 percent of valid contacts are persisted<br/>DNC and exclusion entries mark contacts as excluded<br/>Contact states and attempts default values are correct<br/>Contact list endpoint exposes state and basic metadata | REQ-002 | App | open |
| REQ-004 | Call scheduler and telephony provider adapter | Scheduler selects eligible contacts respecting time windows<br/>CallAttempt records created with unique call_id per attempt<br/>Telephony adapter starts outbound calls with metadata<br/>Contact state and attempts updated transactionally<br/>Concurrent calls limited by configurable max_concurrent_calls | REQ-003, REQ-009 | App | open |
| REQ-005 | Dialogue outcome handling and survey responses | Webhook endpoint receives telephony events reliably<br/>Consent outcomes stored with timestamps and final status<br/>Completed surveys persist three answers linked to attempt<br/>Contact state transitions follow outcomes and retry rules<br/>Survey events published with required payload fields | REQ-004, REQ-009 | App | open |
| REQ-006 | Event bus integration and email worker | Survey events are published to configured queue abstraction<br/>Email worker consumes events and sends templated emails<br/>EmailNotification records track send status and metadata<br/>Email sending is idempotent across retries and restarts<br/>Worker exposes metrics or logs for monitoring and debugging | REQ-005, REQ-009 | App | open |
| REQ-007 | Dashboard stats and CSV export APIs | Stats endpoint returns counts and completion refusal rates<br/>Contacts endpoint lists paginated contacts with outcomes<br/>CSV export returns required columns and no duplicates<br/>Exports exclude transcripts and unnecessary PII fields<br/>Endpoints enforce RBAC and handle missing campaigns cleanly | REQ-002, REQ-003, REQ-005, REQ-009 | App | open |
| REQ-008 | Admin configuration and retention settings APIs | Admin endpoints expose provider and retention configuration<br/>Only admin role can modify provider and retention settings<br/>Configuration changes are persisted and retrievable<br/>Invalid settings are rejected with clear validation errors<br/>Audit log entries created for configuration modifications | REQ-001, REQ-009 | App | open |
| REQ-009 | Database schema models and migrations | ORM models defined for all specified entities<br/>Alembic migrations create tables constraints and indexes<br/>Enum and foreign key relationships align with data model<br/>Migrations apply cleanly on fresh and existing databases<br/>Connection management configured with pooling and settings |  | Infra | open |
| REQ-010 | Messaging and worker infra scaffolding | Messaging abstraction wraps SQS configuration and publishing<br/>Worker entrypoints implemented for scheduler and email worker<br/>Config loader reads messaging and provider settings<br/>Observability helpers configure logging metrics tracing hooks<br/>Deployment notes describe running workers on EKS | REQ-009 | Infra | open |
| REQ-011 | Web console for campaigns and monitoring | Frontend allows campaign creation editing and listing<br/>CSV upload and activation available via UI using backend APIs<br/>Dashboard pages display stats and contact lists<br/>Export controls trigger and download CSV exports<br/>RBAC enforced in UI based on user role information | REQ-001, REQ-002, REQ-003, REQ-007 | App | open |

zed and unauthenticated requests return structured error responses<br/>Viewer campaign_manager admin roles behave per SPEC permissions<br/>Auth modules expose reusable dependencies for other routers |  | App | in_progress |
| REQ-002 | Campaign CRUD and activation rules | Campaigns can be created updated fetched with validation<br/>Lifecycle transitions enforce allowed status changes only<br/>Activation requires valid contacts scripts retry policy window<br/>Unauthorized roles cannot mutate campaign resources<br/>APIs expose filters and pagination for campaign listing | REQ-001 | App | open |
| REQ-003 | Contact CSV import and exclusion handling | CSV upload parses validates rows and reports errors<br/>At least 95 percent of valid contacts are persisted<br/>DNC and exclusion entries mark contacts as excluded<br/>Contact states and attempts default values are correct<br/>Contact list endpoint exposes state and basic metadata | REQ-002 | App | open |
| REQ-004 | Call scheduler and telephony provider adapter | Scheduler selects eligible contacts respecting time windows<br/>CallAttempt records created with unique call_id per attempt<br/>Telephony adapter starts outbound calls with metadata<br/>Contact state and attempts updated transactionally<br/>Concurrent calls limited by configurable max_concurrent_calls | REQ-003, REQ-009 | App | open |
| REQ-005 | Dialogue outcome handling and survey responses | Webhook endpoint receives telephony events reliably<br/>Consent outcomes stored with timestamps and final status<br/>Completed surveys persist three answers linked to attempt<br/>Contact state transitions follow outcomes and retry rules<br/>Survey events published with required payload fields | REQ-004, REQ-009 | App | open |
| REQ-006 | Event bus integration and email worker | Survey events are published to configured queue abstraction<br/>Email worker consumes events and sends templated emails<br/>EmailNotification records track send status and metadata<br/>Email sending is idempotent across retries and restarts<br/>Worker exposes metrics or logs for monitoring and debugging | REQ-005, REQ-009 | App | open |
| REQ-007 | Dashboard stats and CSV export APIs | Stats endpoint returns counts and completion refusal rates<br/>Contacts endpoint lists paginated contacts with outcomes<br/>CSV export returns required columns and no duplicates<br/>Exports exclude transcripts and unnecessary PII fields<br/>Endpoints enforce RBAC and handle missing campaigns cleanly | REQ-002, REQ-003, REQ-005, REQ-009 | App | open |
| REQ-008 | Admin configuration and retention settings APIs | Admin endpoints expose provider and retention configuration<br/>Only admin role can modify provider and retention settings<br/>Configuration changes are persisted and retrievable<br/>Invalid settings are rejected with clear validation errors<br/>Audit log entries created for configuration modifications | REQ-001, REQ-009 | App | open |
| REQ-009 | Database schema models and migrations | ORM models defined for all specified entities<br/>Alembic migrations create tables constraints and indexes<br/>Enum and foreign key relationships align with data model<br/>Migrations apply cleanly on fresh and existing databases<br/>Connection management configured with pooling and settings |  | Infra | open |
| REQ-010 | Messaging and worker infra scaffolding | Messaging abstraction wraps SQS configuration and publishing<br/>Worker entrypoints implemented for scheduler and email worker<br/>Config loader reads messaging and provider settings<br/>Observability helpers configure logging metrics tracing hooks<br/>Deployment notes describe running workers on EKS | REQ-009 | Infra | open |
| REQ-011 | Web console for campaigns and monitoring | Frontend allows campaign creation editing and listing<br/>CSV upload and activation available via UI using backend APIs<br/>Dashboard pages display stats and contact lists<br/>Export controls trigger and download CSV exports<br/>RBAC enforced in UI based on user role information | REQ-001, REQ-002, REQ-003, REQ-007 | App | open |

zed and unauthenticated requests return structured error responses<br/>Viewer campaign_manager admin roles behave per SPEC permissions<br/>Auth modules expose reusable dependencies for other routers |  | App | in_progress |
| REQ-002 | Campaign CRUD and activation rules | Campaigns can be created updated fetched with validation<br/>Lifecycle transitions enforce allowed status changes only<br/>Activation requires valid contacts scripts retry policy window<br/>Unauthorized roles cannot mutate campaign resources<br/>APIs expose filters and pagination for campaign listing | REQ-001 | App | open |
| REQ-003 | Contact CSV import and exclusion handling | CSV upload parses validates rows and reports errors<br/>At least 95 percent of valid contacts are persisted<br/>DNC and exclusion entries mark contacts as excluded<br/>Contact states and attempts default values are correct<br/>Contact list endpoint exposes state and basic metadata | REQ-002 | App | open |
| REQ-004 | Call scheduler and telephony provider adapter | Scheduler selects eligible contacts respecting time windows<br/>CallAttempt records created with unique call_id per attempt<br/>Telephony adapter starts outbound calls with metadata<br/>Contact state and attempts updated transactionally<br/>Concurrent calls limited by configurable max_concurrent_calls | REQ-003, REQ-009 | App | open |
| REQ-005 | Dialogue outcome handling and survey responses | Webhook endpoint receives telephony events reliably<br/>Consent outcomes stored with timestamps and final status<br/>Completed surveys persist three answers linked to attempt<br/>Contact state transitions follow outcomes and retry rules<br/>Survey events published with required payload fields | REQ-004, REQ-009 | App | open |
| REQ-006 | Event bus integration and email worker | Survey events are published to configured queue abstraction<br/>Email worker consumes events and sends templated emails<br/>EmailNotification records track send status and metadata<br/>Email sending is idempotent across retries and restarts<br/>Worker exposes metrics or logs for monitoring and debugging | REQ-005, REQ-009 | App | open |
| REQ-007 | Dashboard stats and CSV export APIs | Stats endpoint returns counts and completion refusal rates<br/>Contacts endpoint lists paginated contacts with outcomes<br/>CSV export returns required columns and no duplicates<br/>Exports exclude transcripts and unnecessary PII fields<br/>Endpoints enforce RBAC and handle missing campaigns cleanly | REQ-002, REQ-003, REQ-005, REQ-009 | App | open |
| REQ-008 | Admin configuration and retention settings APIs | Admin endpoints expose provider and retention configuration<br/>Only admin role can modify provider and retention settings<br/>Configuration changes are persisted and retrievable<br/>Invalid settings are rejected with clear validation errors<br/>Audit log entries created for configuration modifications | REQ-001, REQ-009 | App | open |
| REQ-009 | Database schema models and migrations | ORM models defined for all specified entities<br/>Alembic migrations create tables constraints and indexes<br/>Enum and foreign key relationships align with data model<br/>Migrations apply cleanly on fresh and existing databases<br/>Connection management configured with pooling and settings |  | Infra | open |
| REQ-010 | Messaging and worker infra scaffolding | Messaging abstraction wraps SQS configuration and publishing<br/>Worker entrypoints implemented for scheduler and email worker<br/>Config loader reads messaging and provider settings<br/>Observability helpers configure logging metrics tracing hooks<br/>Deployment notes describe running workers on EKS | REQ-009 | Infra | open |
| REQ-011 | Web console for campaigns and monitoring | Frontend allows campaign creation editing and listing<br/>CSV upload and activation available via UI using backend APIs<br/>Dashboard pages display stats and contact lists<br/>Export controls trigger and download CSV exports<br/>RBAC enforced in UI based on user role information | REQ-001, REQ-002, REQ-003, REQ-007 | App | open |

zed access rejected with structured error|[]|App|open|
|REQ-002|Campaign CRUD and activation rules|Create update fetch campaigns with validation<br>Status transitions enforced per lifecycle rules<br>Activation fails without valid contacts and config|[REQ-001]|App|open|
|REQ-003|Contact CSV import and exclusion handling|CSV uploaded parsed validated with error report<br>Contacts stored with correct initial state<br>DNC and exclusion list contacts never dialed|[REQ-002]|App|open|
|REQ-004|Call scheduler and telephony provider adapter|Scheduler selects eligible contacts and enqueues calls<br>Telephony adapter starts outbound calls with metadata<br>Attempts and states updated per outcome rules|[REQ-003, REQ-009]|App|open|
|REQ-005|Dialogue outcome handling and survey responses|Consent outcomes stored with timestamps<br>Completed surveys store three answers linked to attempts<br>Survey events published for completed refused not_reached|[REQ-004, REQ-009]|App|open|
|REQ-006|Event bus integration and email worker|Survey events published to queue abstraction<br>Email worker sends templated emails per event<br>Email attempts and statuses persisted|[REQ-005, REQ-009]|App|open|
|REQ-007|Dashboard stats and CSV export APIs|Campaign stats endpoint returns aggregates<br>Contacts listing paginated with outcomes<br>CSV export returns required fields without duplicates|[REQ-002, REQ-003, REQ-005, REQ-009]|App|open|
|REQ-008|Admin configuration and retention settings APIs|Admin config CRUD for providers and retention<br>Settings protected to admin role only<br>Retention fields persisted and readable|[REQ-001, REQ-009]|App|open|
|REQ-009|Database schema models and migrations|Core entities modeled with SQLAlchemy<br>Alembic migrations create required tables<br>Constraints align with specified enums and relations|[]|Infra|open|
|REQ-010|Messaging and worker infra scaffolding|SQS abstraction module created and configurable<br>Worker processes runnable via CLI entrypoints<br>Basic deployment config placeholders documented|[REQ-009]|Infra|open|
|REQ-011|Web console for campaigns and monitoring|Users can manage campaigns via UI forms<br>CSV upload and activation available from console<br>Dashboard views display stats and contact lists|[REQ-001, REQ-002, REQ-003, REQ-007]|App|open|

### Acceptance — REQ-001

- Backend integrates with configured OIDC provider using authorization code flow, exchanging code for tokens and validating ID token signature.
- On first successful login, user record is created or updated with OIDC subject, email, display name, and mapped role.
- RBAC middleware or dependency enforces required roles per route group, rejecting unauthorized access with HTTP 403 and stable error schema.
- All API endpoints in campaign, contacts, reporting, and admin routers require authenticated users, no anonymous access allowed.
- Viewer role can read campaigns, contacts, stats, and exports metadata but cannot modify campaigns, upload CSVs, or change admin settings.
- Campaign manager role can create and edit campaigns, upload contacts, activate/pause campaigns, view dashboards, and trigger exports.
- Admin role can additionally manage provider configuration, retention settings, exclusion lists, and view audit logs.
- Primary module: `app.auth.oidc` and `app.api.http.auth`; may create these modules and must reuse `app.infra.config` for settings.

### Acceptance — REQ-002

- FastAPI routes under `app.api.http.campaigns` allow authenticated users with `campaign_manager` or `admin` roles to create and update campaigns.
- Campaign fields include language, intro script, three questions with types, retry policy, and call time window, validated against specified enums and ranges.
- Campaign lifecycle transitions enforce allowed moves, for example draft to scheduled or running, running to paused or completed, and block invalid changes.
- Activation endpoint verifies campaign has at least one non-excluded contact, valid scripts, retry settings, and time windows before setting status to running or scheduled.
- Campaign queries are scoped to single tenant, list endpoint supports filtering by status and creation date, and returns pagination metadata.
- Unauthorized roles, such as viewer, receive HTTP 403 when attempting to create, update, activate, pause, or delete campaigns.
- Primary module: `app.campaigns.domain` and `app.api.http.campaigns`; must reuse `app.auth.domain` for user context and `app.infra.db` for persistence.

### Acceptance — REQ-003

- Endpoint accepts CSV upload for a specific campaign, parses rows streaming where possible, and validates required columns and data formats.
- At least 95 percent of valid rows are inserted as Contact records; invalid rows are reported with row number and error reason in the response summary.
- Contact entity persists external_contact_id, normalized E.164 phone, email, language override, has_prior_consent flag, and do_not_call flag per SPEC.
- Contacts with do_not_call true or present in a global ExclusionListEntry table are stored with state excluded and are never marked eligible for dialing.
- Upload summary response returns total rows, accepted count, rejected count, and sample errors, and is accessible only to campaign_manager and admin roles.
- Contact listing endpoint for a campaign shows state, attempts_count, last_outcome, and timestamps, supporting pagination and role-based access.
- Primary module: `app.contacts.csv_import` and `app.contacts.domain`; may create these modules and must reuse `app.infra.db` and `app.campaigns.domain`.

### Acceptance — REQ-004

- Scheduler component in `app.calling.scheduler` can be run on a schedule to select eligible contacts based on state, attempts_count, retry_interval, and time window.
- Eligible contacts exclude those with do_not_call true, excluded state, or outside campaign allowed_call_start_local and allowed_call_end_local when local time applied.
- For each scheduled attempt, a CallAttempt record is created with unique call_id, linked campaign and contact, attempt_number, and timestamps.
- Telephony adapter module abstracts provider API, initiating outbound calls with to, from, callback URL, language, and metadata including campaign_id and contact_id.
- On enqueue, contact state transitions from pending or not_reached to in_progress, and attempts_count and last_attempt_at are updated transactionally.
- Scheduler respects a configurable maximum concurrent calls parameter, uses Redis or database for locking, and avoids overshooting provider rate limits.
- Maximum attempts per contact are enforced; when limit reached without completion or refusal, contact is no longer selected for scheduling.
- Primary module: `app.calling.scheduler` and `app.calling.telephony`; must reuse `app.contacts.domain`, `app.campaigns.domain`, `app.infra.db`, `app.infra.config`.

### Acceptance — REQ-005

- Telephony webhook endpoint receives provider events and maps them to call lifecycle states including initiated, ringing, answered, completed, failed, no_answer, and busy.
- On answered events, dialogue handling or provider payload ensures intro script and consent request have been executed before any question answers are processed.
- Explicit consent refusal results in CallAttempt outcome refused, contact state refused, and recording of consent timestamp and reason where available.
- Explicit consent acceptance and successful completion of three questions create a SurveyResponse record linked to the CallAttempt, contact, and campaign.
- For no_answer or busy outcomes, CallAttempt outcome is set accordingly, contact last_outcome updated, and state remains pending or not_reached as per retry rules.
- When attempts_count reaches max_attempts without completion or refusal, contact state becomes not_reached and a survey.not_reached event is prepared.
- Internal events survey.completed, survey.refused, and survey.not_reached are published via the event bus abstraction with required payload fields.
- Primary module: `app.calling.dialogue` and `app.api.http.telephony_webhooks`; must reuse `app.calling.telephony`, `app.events.bus`, `app.infra.observability`.

### Acceptance — REQ-006

- Event bus abstraction in `app.events.bus` exposes functions to publish survey events to SQS or equivalent queue with idempotent message keys.
- Email worker process subscribes to survey events queue, deserializes messages, and looks up associated campaign, contact, and email template records.
- For survey.completed events with configured templates, worker sends thank-you email using integrated email provider client and records EmailNotification with status.
- For survey.refused and survey.not_reached events, if templates exist, worker sends appropriate email; if templates are absent, worker logs and skips sending.
- Email send function is idempotent, using provider_message_id or deduplication keys to avoid duplicate sends on retried events or process restarts.
- Failed email attempts are retried with exponential backoff up to a configurable limit; terminal failures are logged and persist status failed in EmailNotification.
- Email worker exposes health or metrics endpoint or logs to allow monitoring of queue lag, send success rate, and error rates.
- Primary module: `app.events.bus` and `app.notifications.email`; must reuse `app.infra.messaging`, `app.infra.config`, `app.infra.observability`, `app.infra.db`.

### Acceptance — REQ-007

- Campaign stats endpoint returns counts of contacts by state, completion, refusal, and not_reached rates, and optionally basic time-series aggregates.
- Endpoint returns data within performance constraints, using indexed queries and avoiding full table scans for campaigns with up to 1,000 contacts.
- Contacts listing endpoint supports filtering by outcome, pagination, and sorting by last_attempt_at, and includes attempts_count and last_outcome.
- CSV export endpoint for a campaign returns required columns campaign_id, contact_id, external_contact_id, phone_number, outcome, attempt_count, timestamps, and three answers when completed.
- Export excludes any transcript text or free-form PII beyond required columns and ensures one row per contact in a terminal state without duplicates.
- Export supports streaming or async generation but provides a stable download mechanism and is accessible only to campaign_manager and admin roles.
- Dashboard-related endpoints are protected by RBAC and tested for viewer role read-only access and correct handling of non-existent campaigns.
- Primary module: `app.reporting.stats` and `app.reporting.export`; must reuse `app.contacts.domain`, `app.campaigns.domain`, `app.infra.db`, `app.auth.domain`.

### Acceptance — REQ-008

- Admin configuration API endpoints allow admins to view and update ProviderConfig including provider_type, provider_name, outbound_number, max_concurrent_calls, llm_provider, and llm_model.
- Retention settings for recordings and transcripts, including recording_retention_days and transcript_retention_days, are persisted and retrievable via admin APIs.
- Only admin role can access admin configuration endpoints; other roles receive HTTP 403 with consistent error responses.
- Changes to critical configuration fields, such as provider credentials or retention days, are recorded in an audit log entity with timestamp, user, field names, and previous values.
- Validation prevents obviously invalid settings, for example negative retention days or unsupported combinations of provider_type and provider_name.
- Administrative endpoints expose current email provider configuration and default email templates per event type and locale.
- Primary module: `app.admin.domain` and `app.api.http.admin`; must reuse `app.auth.domain`, `app.infra.db`, `app.infra.config`, `app.infra.observability`.

### Acceptance — REQ-009

- SQLAlchemy ORM models are defined for all core entities described in the SPEC including User, Campaign, Contact, ExclusionListEntry, CallAttempt, SurveyResponse, Event, EmailNotification, EmailTemplate, ProviderConfig, and optional TranscriptSnippet.
- Models include fields, types, enums, foreign keys, uniqueness constraints, and indexes aligned with the logical data model and performance requirements.
- Alembic migration scripts create the necessary tables, constraints, and indexes for fresh environments, and support upgrade and downgrade operations.
- Database connection management integrates with FastAPI lifecycle, uses connection pooling, and reads connection configuration from environment or config modules.
- Enum fields are represented as database enums or constrained text values with validation, matching domain enums used in application code.
- Basic seed or fixture utilities exist for local development to create an admin user and minimal ProviderConfig records.
- Primary module: `app.infra.db`; may create this module and must be reused by all other REQs needing persistence.

### Acceptance — REQ-010

- Messaging abstraction in `app.infra.messaging` supports publishing survey events to SQS or equivalent, with configuration for queue names and credentials.
- Worker processes for scheduler and email worker expose CLI entrypoints or main functions that can be run by process managers or Kubernetes deployments.
- Configuration module `app.infra.config` loads messaging, email provider, telephony provider, and LLM gateway settings from environment variables or secrets.
- Documentation or comments describe expected deployment patterns for running scheduler as a CronJob and workers as Deployments on EKS.
- Observability helpers in `app.infra.observability` configure JSON logging, metrics emission, and optional tracing integration for workers and API processes.
- Error handling strategies ensure unhandled exceptions cause safe process termination and visibility, not silent failures or orphaned messages.
- Primary module: `app.infra.messaging` and `app.infra.config`; may extend `app.infra.observability` and must not duplicate messaging logic elsewhere.

### Acceptance — REQ-011

- Next.js or React frontend provides authenticated views for campaign listing, creation, editing, and status display using the backend REST APIs.
- Campaign creation form captures required fields including language, intro script, three questions with types, retry policy, and allowed call times, with client-side validation.
- CSV upload UI allows selection and upload of CSV file to the backend endpoint, then displays accepted and rejected row counts and sample errors from backend response.
- Campaign dashboard page shows aggregate stats, completion and refusal rates, and a paginated table of contacts with latest outcome and attempt count.
- Export control allows authorized users to trigger CSV export and download the resulting file, handling loading and error states appropriately.
- Admin-only sections are visible only to admin role, and viewer role sees read-only dashboards and campaign details without editing capabilities.
- Frontend API client layer centralizes HTTP calls, attaches auth tokens, and handles error responses consistent with backend schema.
- Primary module: `web/app` and `web/lib/api`; may create pages and components but must conform to backend API contracts and RBAC expectations.

## Dependency Graph

- REQ-001 -> (none)
- REQ-002 -> REQ-001
- REQ-003 -> REQ-002
- REQ-004 -> REQ-003, REQ-009
- REQ-005 -> REQ-004, REQ-009
- REQ-006 -> REQ-005, REQ-009
- REQ-007 -> REQ-002, REQ-003, REQ-005, REQ-009
- REQ-008 -> REQ-001, REQ-009
- REQ-009 -> (none)
- REQ-010 -> REQ-009
- REQ-011 -> REQ-001, REQ-002, REQ-003, REQ-007

## Iteration Strategy

- **Batch 1 (Foundations, size M, confidence ±1 REQ):**
  - REQ-009 (DB schema and migrations)
  - REQ-001 (Auth and RBAC)
  - REQ-010 (Messaging and worker scaffolding)
- **Batch 2 (Core campaign and contacts, size M, confidence ±1 REQ):**
  - REQ-002 (Campaign CRUD and activation)
  - REQ-003 (Contact CSV import and exclusion)
  - Hook RBAC from REQ-001 into these APIs.
- **Batch 3 (Calling and dialogue, size L, confidence ±1 REQ):**
  - REQ-004 (Scheduler and telephony adapter)
  - REQ-005 (Dialogue outcomes and survey responses)
- **Batch 4 (Events, emails, reporting, size M, confidence ±1 REQ):**
  - REQ-006 (Event bus and email worker)
  - REQ-007 (Dashboard stats and CSV export)
- **Batch 5 (Admin and frontend, size M, confidence ±1 REQ):**
  - REQ-008 (Admin configuration and retention)
  - REQ-011 (Web console)

Infra work in REQ-010 can be pulled earlier if needed to unblock workers for REQ-004 and REQ-006.

## Test Strategy

- **Per REQ:**
  - REQ-001: Unit tests for OIDC handlers, RBAC decorators, and role mapping; integration tests for protected routes.
  - REQ-002: Unit tests for campaign validation and lifecycle; API tests for create, update, activate, pause scenarios.
  - REQ-003: Unit tests for CSV parsing and validation; integration tests verifying accepted and rejected counts and exclusion handling.
  - REQ-004: Unit tests for scheduler selection logic and concurrency limits; integration tests with mocked telephony adapter and database state changes.
  - REQ-005: Unit tests for mapping telephony events to outcomes; integration tests for webhook idempotency and SurveyResponse creation.
  - REQ-006: Unit tests for event bus publishing; worker tests with in-memory or test queue verifying email sends and idempotency.
  - REQ-007: Integration tests for stats endpoint accuracy, pagination, and CSV export contents, including edge cases.
  - REQ-008: Unit and API tests for admin config CRUD, validation, and RBAC; audit logging assertions.
  - REQ-009: Model tests ensuring relationships, constraints, and migrations apply correctly on a test database.
  - REQ-010: Tests for config loading, messaging wrappers against a stubbed SQS client, and worker entrypoint behavior on errors.
  - REQ-011: Frontend component and page tests for forms, API integration, routing, and RBAC-driven visibility; e2e happy path for campaign creation and launch.

- **Per batch:**
  - Batch-level integration tests simulating end-to-end workflows:
    - Create campaign, upload CSV, activate.
    - Run scheduler and simulate telephony events to produce completed, refused, not_reached contacts.
    - Trigger email sending and verify dashboards and exports reflect final outcomes.

- **E2E / System tests:**
  - Limited E2E flows using mocked external providers for telephony, LLM, and email in non-production.
  - Performance checks for scheduler and key APIs under approximate 1,000 contacts.

## KIT Readiness

Common expectations:

- Backend source root per REQ under `/runs/kit/<REQ-ID>/src/app/...`.
- Backend tests per REQ under `/runs/kit/<REQ-ID>/test/...`.
- Frontend source for REQ-011 under `/runs/kit/REQ-011/src/web/...` with tests under `/runs/kit/REQ-011/test/...`.
- No conflicting new top-level namespaces beyond those listed.

Per REQ:

- **REQ-001**
  - Root package: `app.auth`
  - Paths:
    - `/runs/kit/REQ-001/src/app/auth`
    - `/runs/kit/REQ-001/src/app/api/http/auth`
    - `/runs/kit/REQ-001/test/auth`
  - KIT-functional: yes
  - API testing: OIDC callback and protected resource tests under `/runs/kit/REQ-001/test/api`.

- **REQ-002**
  - Root package: `app.campaigns`
  - Paths:
    - `/runs/kit/REQ-002/src/app/campaigns`
    - `/runs/kit/REQ-002/src/app/api/http/campaigns`
    - `/runs/kit/REQ-002/test/campaigns`
  - KIT-functional: yes
  - API testing for create, update, activate endpoints under `/runs/kit/REQ-002/test/api`.

- **REQ-003**
  - Root package: `app.contacts`
  - Paths:
    - `/runs/kit/REQ-003/src/app/contacts`
    - `/runs/kit/REQ-003/src/app/api/http/contacts`
    - `/runs/kit/REQ-003/test/contacts`
  - KIT-functional: yes
  - CSV upload tests and data validation under `/runs/kit/REQ-003/test/api`.

- **REQ-004**
  - Root package: `app.calling.scheduler`
  - Paths:
    - `/runs/kit/REQ-004/src/app/calling`
    - `/runs/kit/REQ-004/test/calling`
  - KIT-functional: yes
  - Tests include scheduler run functions and telephony adapter mocks.

- **REQ-005**
  - Root package: `app.calling.dialogue`
  - Paths:
    - `/runs/kit/REQ-005/src/app/calling`
    - `/runs/kit/REQ-005/src/app/api/http/telephony_webhooks`
    - `/runs/kit/REQ-005/test/calling`
  - KIT-functional: yes
  - Webhook API tests verifying outcome handling under `/runs/kit/REQ-005/test/api`.

- **REQ-006**
  - Root package: `app.notifications`
  - Paths:
    - `/runs/kit/REQ-006/src/app/events`
    - `/runs/kit/REQ-006/src/app/notifications`
    - `/runs/kit/REQ-006/test/notifications`
  - KIT-functional: yes
  - Worker behavior and event publishing tests in `/runs/kit/REQ-006/test`.

- **REQ-007**
  - Root package: `app.reporting`
  - Paths:
    - `/runs/kit/REQ-007/src/app/reporting`
    - `/runs/kit/REQ-007/src/app/api/http/reporting`
    - `/runs/kit/REQ-007/test/reporting`
  - KIT-functional: yes
  - Stats and export API tests, including CSV content checks.

- **REQ-008**
  - Root package: `app.admin`
  - Paths:
    - `/runs/kit/REQ-008/src/app/admin`
    - `/runs/kit/REQ-008/src/app/api/http/admin`
    - `/runs/kit/REQ-008/test/admin`
  - KIT-functional: yes
  - Admin API tests covering RBAC and audit logging.

- **REQ-009**
  - Root package: `app.infra.db`
  - Paths:
    - `/runs/kit/REQ-009/src/app/infra/db`
    - `/runs/kit/REQ-009/test/infra/db`
  - KIT-functional: yes
  - Migration tests using a temporary database.

- **REQ-010**
  - Root package: `app.infra.messaging`
  - Paths:
    - `/runs/kit/REQ-010/src/app/infra`
    - `/runs/kit/REQ-010/test/infra`
  - KIT-functional: yes
  - Tests cover messaging wrapper functions and worker entrypoints.

- **REQ-011**
  - Root package: `web`
  - Paths:
    - `/runs/kit/REQ-011/src/web`
    - `/runs/kit/REQ-011/test/web`
  - KIT-functional: yes
  - UI and integration tests for pages and components.

Where external APIs are involved, test doubles will live under each REQ’s `test` subtree. If needed, API documentation or Postman-style collections will be stored at `/runs/kit/<REQ-ID>/test/api`.

## Notes

- **Assumptions:**
  - Telephony provider offers webhook events and either a built-in LLM agent or structured payloads suitable for dialogue outcome processing.
  - LLM gateway is reachable within allowed endpoints and supports required models defined in TECH_CONSTRAINTS.
  - Email service credentials and SMTP or HTTP APIs are available and testable in non-production.
- **Risks:**
  - Mapping of telephony events and consent semantics may differ by provider; adapter must isolate provider-specific details.
  - Latency and throughput targets depend heavily on external providers; internal design will minimize added delays.
  - Frontend scope is intentionally minimal, focused on core flows; advanced UX and visualizations are deferred.
- **Lane detection:**
  - Lanes inferred from TECH_CONSTRAINTS: python (backend), node (frontend), sql (Postgres), ci (GitHub Actions), infra (EKS, Redis, SQS, Secrets Manager), aws (cloud provider).
  - Only canonical lanes python, node, sql, ci, infra are used in plan.json; aws lane is documented via a lane guide but not referenced by REQs.
- **Out-of-band constraints:**
  - Internet egress is restricted to whitelisted providers; all external client modules must be configurable and respect proxy or network policies.
  - No triple-backtick code fences will be used in KIT source planning to avoid conflicts with surrounding tooling.

PLAN_END