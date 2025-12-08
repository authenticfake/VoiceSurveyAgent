# HOWTO – Execute and Validate REQ-005

## Prerequisites
- Python 3.12+
- Poetry/pip/uv for dependency management.
- PostgreSQL (or SQLite for local tests).
- Environment variable `DATABASE_URL` (e.g. `postgresql+psycopg://user:pass@localhost:5432/voicesurveyagent`).

## Local Setup
1. Create virtualenv: `python -m venv .venv && source .venv/bin/activate`
2. Install deps (example using pip): `pip install -r runs/kit/REQ-005/requirements.txt`
3. Export DB URL: `export DATABASE_URL=postgresql+psycopg://...`

## Running Tests
```bash
pytest -q runs/kit/REQ-005/test
```

## FastAPI Integration
1. Mount router:
   ```python
   from app.api.http.telephony_webhooks.router import router as telephony_router
   app.include_router(telephony_router)
   ```
2. Ensure `app.infra.db.session.get_db_session` is added to FastAPI dependencies where needed.

## Enterprise Runner (Jenkins/GitHub Actions)
- Use Python 3.12 executor.
- Step order:
  1. `pip install -r runs/kit/REQ-005/requirements.txt`
  2. `export DATABASE_URL=postgresql+psycopg://...`
  3. `pytest -q runs/kit/REQ-005/test`
- Artifacts: pytest stdout (no junit configured in this slice).

## Troubleshooting
- **Missing env**: `RuntimeError: DATABASE_URL ...` → export valid DSN.
- **SQLite shared cache**: ensure filename path or `?cache=shared` when using memory DB.
- **Import errors**: confirm PYTHONPATH includes repo root (e.g., `export PYTHONPATH=$PWD`).

KIT Iteration Log
Targeted REQ-IDs: REQ-005 (per plan snapshot).
In scope: telephony webhook endpoint, dialogue processor, survey persistence, DB session helper, event publisher, unit tests, docs, LTC/HOWTO.
Out of scope: event bus transport (SQS), email worker behaviors, LLM orchestration beyond payload validation.
Tests: `pytest -q runs/kit/REQ-005/test`
Prerequisites: Python 3.12, pytest, SQLAlchemy, configured DATABASE_URL (SQLite acceptable for tests).
Dependencies/mocks: Real SQLAlchemy models; SQLite in-memory used for tests only to ensure deterministic behavior.
Product Owner Notes: assumes provider sends full three answers on completion; retries based on attempts_count already incremented by scheduler.
RAG citations: SPEC.md (functional scope), PLAN.md (module boundaries), TECH_CONSTRAINTS.yaml (python lane).