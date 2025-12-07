# HOWTO — Execute REQ-001 Suite

## Prerequisites
- Python 3.12 with `venv`.
- Network access to your IdP endpoints (or ability to mock via `respx` in tests).
- Environment variables (override defaults):
  - `DATABASE_URL` (async SQLAlchemy URL, e.g. `sqlite+aiosqlite:///./auth.db` or `postgresql+asyncpg://user:pass@host/db`)
  - `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`
  - `OIDC_AUTHORIZATION_URL`, `OIDC_TOKEN_URL`, `OIDC_JWKS_URL`, `OIDC_ISSUER`
  - `APP_JWT_SECRET`

## Local Setup
```bash
cd runs/kit/REQ-001
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="sqlite+aiosqlite:///./.tmp/auth.db"
export OIDC_CLIENT_ID="local-client"
# ...set remaining env vars...
```

## Running Tests
```bash
pytest -q
```
Tests mock IdP interactions with `respx`, no real network calls occur.

## Running the API
```bash
uvicorn app.main:app --reload --port 8000
```
Then:
1. `GET /api/auth/login?redirect_uri=https://app.local/auth/callback`
2. Complete IdP login, exchange code via `POST /api/auth/callback`.
3. Use returned `app_access_token` for protected endpoints.

## CI / Enterprise Runners
- Use the provided `ci/LTC.json` definition.
- Ensure secrets are injected via runner vault (GitHub Actions env, Jenkins credentials, etc.).
- For Jenkins: add a pipeline stage executing `pip install -r runs/kit/REQ-001/requirements.txt && pytest -q runs/kit/REQ-001/test`.

## Troubleshooting
- **Import errors**: confirm `PYTHONPATH` includes `runs/kit/REQ-001/src` (e.g., `export PYTHONPATH=$PWD/src:$PYTHONPATH`).
- **SQLite path issues**: ensure `.tmp/` directory exists or point `DATABASE_URL` elsewhere.
- **Invalid token errors**: verify IdP JWKS URL reachable and matching algorithms; for local tests rely on defaults/mocks.
- **RBAC 403**: check the role embedded in `app_access_token`; only `campaign_manager` or `admin` can hit `/api/auth/manager/ping`.

```

KIT Iteration Log
-----------------
- **Targeted REQ-ID(s)**: REQ-001 (foundational auth/RBAC per PLAN order).
- **In/Out of scope**: Implemented OIDC callback, JWT issuance, RBAC deps, user persistence. UI, downstream routers, and nonce storage left for future REQs.
- **How to run tests**: `pytest -q runs/kit/REQ-001/test`
- **Prerequisites**: Python 3.12, ability to install dependencies from `requirements.txt`, configured OIDC+DB env vars (defaults included for local dev).
- **Dependencies and mocks**: External IdP endpoints mocked via `respx` in tests; SQLite used for persistence with SQLAlchemy async engine.
- **Product Owner Notes**: Future REQs should reuse `get_current_user`/`require_roles`; state/nonce validation and audit logging to be layered later.
- **RAG citations**: SPEC.md (auth requirements), PLAN.md (module map), plan.json (lane + acceptance).