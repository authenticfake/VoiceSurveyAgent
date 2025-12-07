# IDEA — voicesurveyagent

## Vision
Automate national and international phone surveys with an AI voice agent that can place calls, obtain explicit consent, and complete a 3‑question survey at scale. Organizations reduce cost per completed interview and human workload while gaining standardized, compliant conversations and structured results. End users experience a short, transparent, human-like call with clear identity, purpose, and easy opt-out. The differentiator is a pluggable telephony/voice layer (custom APIs vs. voice AI platforms) plus strong observability and regulatory controls. Slice‑1 delivers one configurable campaign, 3 questions, and outbound calls via a single provider.

## Problem Statement
Research institutes and enterprises running phone surveys rely on human callers using scripts and spreadsheets or basic dialer tools. This is expensive, hard to scale beyond a few hundred calls/day, and produces inconsistent tone, consent handling, and data capture. Orchestrating retries, busy/no‑answer outcomes, exclusion lists, and follow‑up emails is manual and error‑prone, leading to missed responses and regulatory risk. Existing tools focus on generic outbound calling or IVR, not persuasive, compliant, natural-language surveys with full traceability. For slice‑1, the problem is “run a single 3‑question survey campaign, with up to 5 call attempts per contact, handling consent, refusals, and simple emails, while logging every call outcome and survey answer.” The solution is “good enough” when a non-technical operator can start a campaign from a CSV, the system automatically runs calls and retries with <1.5s conversational latency, and final results are queryable in a dashboard or export.

## Target Users & Context
- **Primary user:** Survey/campaign manager at a research institute or enterprise  
  - Define survey scripts and 3 questions  
  - Upload contact lists and schedule calls  
  - Monitor completion/refusal/not-reachable rates and export results
- **Secondary stakeholders:**  
  - Legal/compliance: ensure consent, exclusion lists, and auditability  
  - IT/engineering: integrate with LLM gateway, telephony provider, and email systems  
  - Finance/ops: control cost per completed interview and call volumes
- **Operating context:**  
  - Web-based back-office for campaign setup and monitoring  
  - Backend in cloud or on-prem; outbound calls via one telephony or voice AI provider for slice‑1  
  - Volumes: slice‑1 up to ~1,000 calls/day (assumption)  
  - Languages: English and Italian to start (assumption)  
  - Accessibility: voice calls only; no special UI accessibility constraints in slice‑1; i18n limited to EN/IT in the console (assumption)

## Value & Outcomes (with initial targets)
- Outcome 1: Reduce human caller effort by ≥70% (assumption) for targeted campaigns by automating outbound survey calls.
- Outcome 2: Achieve ≥40% survey completion rate among answered calls in pilot campaigns.
- Outcome 3: Maintain conversational latency <1.5s round-trip in ≥95% of turns during calls.
- Outcome 4: Ensure 100% of calls have a stored outcome (completed/refused/not-reachable) and structured event logs.
- Outcome 5: Cut cost per completed interview by ≥30% versus baseline human-only process (assumption).

## Out of Scope (slice-1)
- Inbound call handling or call transfers to human agents.
- More than 3 survey questions or complex branching/skip logic.
- Multi-tenant campaign management across many client organizations.
- Multi-channel surveys (SMS, WhatsApp, web forms) beyond simple follow-up emails.
- Integration with CRM/ERP systems or advanced analytics dashboards beyond basic metrics and CSV export.
- Support for more than one telephony or voice AI provider at runtime (mode switch configurable but only one adapter fully implemented).

## Technology Constraints (SPEC-ready)
```yaml
tech_constraints:
  version: 1.1.0

  metadata:
    name: "voicesurveyagent"
    description: "AI voice agent to run compliant 3-question phone surveys with automated call orchestration and structured results."
    owner: "survey-platform-team"  # Assumption
    environment: [dev, qa, uat, prod]
    criticality: medium
    complexity: medium
    domain: "survey_automation"
    compliance:
      - "GDPR"  # consent, logging, retention
      - "local_telemarketing_rules"  # Assumption placeholder

  classification:
    solution_type: "web"
    location: "cloud"  # Assumption
    cloud_provider: "aws"  # Assumption
    tenant_model: "single"
    data_sensitivity: "internal"

  project_definition:
    type: "web_application"
    framework: "fastapi-react"  # Backend FastAPI + React-based front-end (assumption)
    language: "python-typescript"
    deployment_target: "aws-eks"  # Assumption

  technology_stack:
    core:
      framework: "FastAPI backend, React/Next.js frontend"  # Assumption
      language: "Python 3.12+, TypeScript"
      runtime: "Node.js 20+, CPython 3.12"
    styling:
      primary: "Tailwind CSS"
      components: "Headless UI or similar"
      icons: "Lucide"
    state_management:
      server_state: "REST/React Query"
      client_state: "Local state or lightweight store"
    database_and_backend:
      orm: "SQLAlchemy"  # Assumption
      database: "PostgreSQL"
      cache: "Redis"
      vector_store: "None for slice-1"
      auth: "OIDC-compatible provider (e.g., corporate IdP)"  # Assumption
    messaging:
      broker: "SQS_or_Kafka"  # abstracted; concrete choice in /spec
      event_stream: "Internal event bus abstraction"
    observability_stack:
      logging: "Centralized JSON logging (e.g., CloudWatch)"
      tracing: "OpenTelemetry"
      metrics: "Prometheus-compatible metrics"

  lanes:
    - name: "backend"
      lane: "python"
      purpose: "Survey campaigns, call orchestration APIs, provider webhooks, email triggers, logging"
      allowed_frameworks:
        - "FastAPI"
      forbidden_technologies:
        - "Flask_without_ASGI"
      default_test_profile:
        coverage_min: 80
        required_checks:
          - tests
          - lint
          - types
          - security
          - build
    - name: "frontend"
      lane: "js-ts"
      purpose: "Campaign setup UI and monitoring dashboard"
      allowed_frameworks:
        - "Next.js"
        - "React"
      forbidden_technologies:
        - "jQuery"
        - "Bootstrap"
      default_test_profile:
        coverage_min: 75
        required_checks:
          - tests
          - lint
          - types
          - build

  profiles:
    - name: "app-core"
      runtime: "python@3.12"
      platform: "aws-eks"
      api:
        - "rest"
        - "webhooks"
      storage:
        - "postgres"
        - "redis"
      messaging:
        - "sqs"
      auth:
        - "oidc"
      observability:
        - "cloudwatch"
        - "prometheus"
    - name: "ai-rag"
      runtime: "python@3.12"
      platform: "aws-lambda"  # Assumption; used if future LLM knowledge features are added
      api:
        - "rest"
      storage:
        - "s3"
      messaging:
        - "sns"
      auth:
        - "iam"
      observability:
        - "cloudwatch"
      rag_formats_supported:
        - "pdf"
        - "docx"
        - "pptx"
        - "xlsx"
        - "txt"

  ci_cd:
    system: "github_actions"
    runners: "ubuntu-latest"
    pipelines:
      main_branch: ".github/workflows/ci.yml"
      deploy_pipeline: ".github/workflows/cd.yml"
    external_quality_gates:
      sonar:
        enabled: false  # Assumption
        project_key: ""
      security_scanner:
        enabled: true
        tool: "Trivy_or_Snyk"
    default_branch_protection:
      require_pr: true
      require_reviews: 1
      require_status_checks: true

  security:
    internet_egress: "restricted"
    allowed_endpoints:
      - "https://api.openai.com"  # Assumption if GPT used
      - "https://api.anthropic.com"  # Assumption if Claude used
      - "https://generativelanguage.googleapis.com"  # Assumption if Gemini used
      - "https://api.twilio.com"  # Example telephony provider; swap per chosen vendor
    secrets_management: "AWS Secrets Manager"
    dependency_policy:
      allowlist:
        - "fastapi"
        - "pydantic"
        - "sqlalchemy"
      denylist:
        - "requests<2.32.0"
    authentication:
      user_auth: "OIDC"
      service_auth: "IAM_roles_or_JWT"
    authorization:
      method: "RBAC"
      policies_source: "app_database"
    data_protection:
      encryption_at_rest: true
      encryption_in_transit: true
      pii_handling: "PII (contact data, call transcripts) stored in Postgres with role-based access; transcripts and recordings subject to configurable retention and anonymization policies."

  data_management:
    primary_stores:
      - name: "core-db"
        engine: "postgres"
        region: "eu-central-1"  # Assumption; EU to align with GDPR
    backup_policy:
      rpo_minutes: 15
      rto_minutes: 60
    retention_policy:
      transactional_data_days: 3650
      logs_days: 365
    migration_strategy: "Alembic_or_compatible_migrations"
  
  eval_profiles:
    default:
      coverage_min: 80
      max_critical_vulns: 0
      lint_must_be_clean: true
      allow_snapshot_tests: true
    relaxed_non_prod:
      coverage_min: 60
      max_critical_vulns: 0
      allow_flaky_tests: true

  ai_policies:
    allowed_providers:
      - "openai"
      - "anthropic"
      - "azure-openai"
      - "google"
    allowed_models:
      - "gpt-4.1-mini"
      - "gpt-4.1"
      - "claude-3.5-sonnet"
    data_boundary: "EU-preferred_processing; vendor-specific regions configured where possible."
    logging:
      prompt_logging_enabled: false
      redaction_required: true
```

## Risks & Assumptions
- **Business assumptions:** Pilot campaigns will be limited to 1,000 contacts/day and 3 questions; legal/compliance stakeholders will provide concrete consent and exclusion-list policies; organizations will accept single-tenant deployment in slice‑1.
- **Technical assumptions:** AWS, PostgreSQL, Redis, and an OIDC IdP are available; at least one telephony/voice AI provider (e.g., Twilio or a voice AI platform) exposes suitable APIs and webhooks; LLM gateway access and keys are provisioned with sufficient rate limits.
- **Delivery risks:** Regulatory approvals for outbound calls may delay go‑live; telephony provider onboarding and number provisioning may have lead times; latency and audio quality may depend on external provider SLAs.
- **UX risks:** Overly robotic voice or latency >1.5s may reduce completion rates; unclear consent wording may cause refusals; campaign managers may need guidance to write effective but compliant scripts.

## Success Metrics (early slice)
- **TTFA (Time-to-First-Action):** ≤15 minutes from first login to launching a simple 3‑question campaign with a small test list.
- **Task success (slice flows):** ≥85% of campaign managers can upload contacts, configure survey, and start a campaign without assistance.
- **Critical error rate:** ≤2% of calls with missing or inconsistent outcome/survey data per campaign.
- **Idea→Demo lead time:** ≤10 calendar days to demonstrate an end-to-end call with one real telephony/voice AI provider.
- **CSAT/NPS (pilot):** ≥4.0/5.0 satisfaction from survey managers on usability and visibility of outcomes.

## Sources & Inspiration
- Internal notes: “IDEA_VoiceSurveyAgent (eng).md” describing business flows, non-functional requirements, and telephony/voice AI provider options.
- Market scan / baseline: Mentioned providers such as Twilio, Vonage, Plivo, Telnyx, Bland AI, Vapi, and Retell as reference implementation targets and capability baselines.

## Non-Goals
- Replacing full-fledged contact-center or CRM systems.
- Implementing sophisticated dialogue management, sentiment analysis, or dynamic question routing beyond basic persuasion and fixed 3‑question flow.
- Providing legal templates for consent or telemarketing policies (these must come from the customer).
- Achieving hyperscale (>100k calls/day) or multi-region active-active setups before validating business value.

## Constraints
- **Budget:** Assumed constrained to a 2–3-sprint MVP; prioritization must favor a single-provider, single-LLM path first.
- **Timeline:** Slice‑1 target is a functional demo in ≤2 weeks from start, with one campaign, one provider, and 3 questions.
- **Compliance:** Must support GDPR-oriented consent logging, contact exclusion flags, and configurable retention for recordings/transcripts.
- **Legal:** No political or sensitive-topic calls without explicit prior consent; strict handling of opt-out and do-not-call lists.
- **Platform limits:** Subject to telephony API concurrency and rate limits; LLM API quotas and latency constraints; sandbox vs. production numbers and keys managed separately.

## Strategic Fit
- Aligns with initiatives to automate data collection, reduce operational survey costs, and standardize customer feedback processes.
- Executive sponsors likely from research/insights, operations, or digital transformation units; go/no-go after a pilot with clear cost-per-interview and completion-rate data.
- Cross-function impacts include IT (integration and hosting), Security/DPO (GDPR, logging, retention), and Finance (telephony and LLM usage costs).

## /spec Handoff Readiness (bridge section)
- **Functional anchors:**
  - Campaign managers can create a 3‑question survey campaign with intro script, retry policy, and allowed time windows.
  - Users can upload a CSV contact list with phone, email, language, and consent flags, with validation and error feedback.
  - System initiates outbound calls via configured provider and drives a natural-language flow to obtain consent and ask 3 questions.
  - System handles call outcomes (completed, refused, no answer, busy, max retries) and updates contact state accordingly.
  - System publishes structured events (`survey.completed`, `survey.refused`, `survey.not_reached`) to an internal queue for downstream processing.
  - A worker consumes events to send predefined follow-up emails (thanks, info, or not-reached message).
  - Console provides a per-campaign dashboard listing calls, outcomes, and aggregated metrics (completion/refusal/not-reachable rates) plus CSV export.
  - Admins can configure environment mode (custom vs. voice AI platform) though only one adapter is wired in slice‑1.

- **Non-functional anchors:**
  - Performance: conversational round-trip latency ≤1.5s P95 for speech–LLM–speech loop.
  - Availability: core APIs and campaign dashboard available ≥99% during business hours in pilot.
  - Security: RBAC for access to campaigns and transcripts; PII classified and protected per GDPR; all access logged.
  - Observability: centralized logs for calls, events, and errors; metrics for answer/completion/refusal rates, call durations, and provider errors; correlation IDs across call, LLM, and email events.
  - Data lifecycle: configurable retention for call recordings and transcripts (e.g., default 180 days); permanent storage only for structured survey answers and minimal metadata; deletion mechanisms for individual contacts on request.

- **Acceptance hooks:**
  - **Campaign creation & upload**
    - Given a valid CSV with ≥10 contacts, when uploaded, then ≥95% of valid rows are accepted and invalid rows are reported with reasons.
    - Given a user defines intro + 3 questions + retries + time window, when saved, then the campaign is persisted and visible in the campaign list with correct configuration.
  - **Outbound calling & consent**
    - Given an active campaign and one reachable contact, when the system initiates a call, then the contact receives a call that states identity, purpose, and duration before asking for consent.
    - Given the callee clearly refuses, then the call ends within 10 seconds and the contact state becomes “Refused” with a logged refusal reason.
  - **Survey completion**
    - Given the callee accepts and answers all 3 questions, then a `survey.completed` event is emitted with contact ID, timestamp, and captured answers.
    - Given the event is processed, then the contact state becomes “Completed” and a thank-you email is sent to the configured address.
  - **Retry and not-reachable handling**
    - Given a contact does not answer within provider timeout, then the system logs outcome “No answer,” increments attempt count, and schedules a retry within the configured time window.
    - Given max attempts are reached without connection, then the state is “Not reachable,” no further calls are attempted, and (if enabled) a not-reached email is sent.
  - **Dashboard & export**
    - Given at least 50 calls were attempted, then the dashboard shows counts and percentages for completed, refused, and not-reachable within 1-minute freshness.
    - Given a user requests CSV export, then a file is generated containing at least contact ID, phone, outcome, attempt count, and (for completed) the 3 answers.