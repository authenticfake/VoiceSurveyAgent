# HOWTO — Run & Operate REQ-004 Scheduler

## Prerequisites
- Python 3.12
- Pip (or uv/pipx) with ability to install `SQLAlchemy`, `httpx`, `pytest`.
- Access to Postgres (runtime) and network egress to the telephony provider.
- Environment must expose DB URL + secrets for provider API key (via `app.infra.config` integration).

## Local Setup
1. Install deps:
   ```bash
   pip install -r runs/kit/REQ-004/requirements.txt
   ```
2. Set `PYTHONPATH=.` to load the `app` package.
3. Configure the scheduler settings when wiring into the worker process:
   ```python
   settings = SchedulerSettings(
       callback_url=os.environ["TELEPHONY_CALLBACK_URL"],
       batch_size=int(os.getenv("SCHEDULER_BATCH", "25")),
       timezone=ZoneInfo(os.getenv("SCHEDULER_TZ", "UTC")),
   )
   service = SchedulerService(SessionLocal, telephony_provider, settings)
   service.run()
   ```

## Tests
```
pytest -q runs/kit/REQ-004/test
```

## Enterprise Runner Notes
- Jenkins/GitHub Actions: install deps via `pip install -r runs/kit/REQ-004/requirements.txt`.
- Ensure DB credentials + telephony secrets injected through Vault/Secrets Manager.
- Collect pytest JUnit output from `runs/kit/REQ-004/reports/junit.xml` if desired.

## Troubleshooting
- **Enum/DDL mismatches**: confirm DB schema from REQ-009 migrations is applied; run Alembic upgrade.
- **Capacity always zero**: check `provider_configurations.max_concurrent_calls` and ensure open CallAttempts have `ended_at` set.
- **Window filtering issues**: verify scheduler timezone matches campaign expectations.
- **Telephony errors**: logs show `Telephony provider failure` lines; confirm API key and provider availability.

KIT Iteration Log
-----------------
- **Targeted REQ-ID(s)**: REQ-004 (call scheduler + telephony adapter per PLAN).
- **In Scope**: Scheduler service, provider abstraction/HTTP adapter, unit tests, docs, LTC/HOWTO.
- **Out of Scope**: FastAPI routers, Redis locks, webhook handling (covered by later REQs).
- **Tests**: `pytest -q runs/kit/REQ-004/test`
- **Prerequisites**: Python 3.12, ability to install SQLAlchemy/httpx/pytest; Postgres schema from REQ-009 for runtime.
- **Dependencies & Mocks**: Database in tests uses SQLite + ORM metadata; telephony provider mocked via `FakeTelephonyProvider`.
- **Product Owner Notes**: Assumed uniform scheduler timezone; outbound number sourced from provider config or campaign-specific overrides when available.
- **RAG Citations**: Referenced SPEC.md (scheduler requirements), PLAN.md (module boundaries), plan.json (lane info), TECH_CONSTRAINTS.yaml (stack), REQ-009 schema snippets (model names/fields).