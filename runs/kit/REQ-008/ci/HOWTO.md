# HOWTO — Execute REQ-008 Test Contract

## Prerequisites
- Python 3.12+
- `pip`/`uv` capable environment with internet access to install dependencies
- Optional: set env vars for email provider metadata  
  (`EMAIL_PROVIDER`, `EMAIL_FROM_ADDRESS`, `EMAIL_REPLY_TO`, `EMAIL_PROVIDER_REGION`)

## Setup
```bash
cd $PROJECT_ROOT
python -m venv .venv
source .venv/bin/activate
pip install -r runs/kit/REQ-008/requirements.txt
```

## Commands
- **Tests:** `pytest -q runs/kit/REQ-008/test`
- **Lint (optional):** `ruff check runs/kit/REQ-008/src`
- **Types (optional):** `mypy runs/kit/REQ-008/src`

## Environment
- Ensure `PYTHONPATH=.` so FastAPI modules resolve.
- Configure email metadata env vars if you want non-default response values.

## CI Integration
- Execute commands from repo root (matches LTC `cwd`).
- Publish junit/coverage reports under `runs/kit/REQ-008/reports/`.

## Troubleshooting
- **Import errors:** confirm `PYTHONPATH=.` or install package via `pip install -e .`.
- **Missing env vars:** API defaults to SES + placeholder sender; set vars for production.
- **Database access:** service expects a configured session factory from `app.infra.db.session`; when running isolated tests, overrides provide fakes.

## Enterprise Runner Notes
- Jenkins/GitHub Actions: add a job step `pip install -r runs/kit/REQ-008/requirements.txt` before running pytest.
- Ensure audit log output is captured via standard stdout/stderr for SIEM forwarders.


KIT Iteration Log
- **Targeted REQ‑ID(s)**: REQ-008 (admin config APIs) — next open requirement per plan dependencies.
- **In/Out of scope**: Implemented domain/service/router, audit logging, env-driven email metadata, unit+API tests, docs, LTC/HOWTO. No schema changes or frontend wiring were touched.
- **How to run tests**: `pytest -q runs/kit/REQ-008/test`
- **Prerequisites**: Python 3.12+, ability to install requirements from `runs/kit/REQ-008/requirements.txt`; optional email-related env vars for richer responses.
- **Dependencies and mocks**: Service tests use in-memory stubs for repositories and sessions; router tests override FastAPI dependencies with fake principals/services to avoid hitting real DB/auth.
- **Product Owner Notes**: Email provider metadata is read-only (env-based) while provider/retention/settings persist via DB. Audit log currently emits structured JSON to `audit.admin`.
- **RAG citations**: SPEC.md, PLAN.md, plan.json, TECH_CONSTRAINTS.yaml, schema snippets (`runs/kit/REQ-009/...`), and router/service patterns from REQ-002 context.