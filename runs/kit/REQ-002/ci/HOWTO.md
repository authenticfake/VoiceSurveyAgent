# HOWTO — Execute REQ-002 Auth Suite

## Prerequisites
- Python 3.12+
- Virtualenv or pyenv recommended
- Internet access to fetch PyPI packages (FastAPI, SQLAlchemy, httpx, PyJWT)

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r runs/kit/REQ-002/src/requirements.txt
```

## Environment
Export the following (adapt for your IdP/prod env):

```bash
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/voicesurvey"
export OIDC_ISSUER="https://idp.example.com"
export OIDC_CLIENT_ID="voicesurvey-client"
export OIDC_CLIENT_SECRET="super-secret"
export OIDC_AUTHORIZATION_ENDPOINT="${OIDC_ISSUER}/authorize"
export OIDC_TOKEN_ENDPOINT="${OIDC_ISSUER}/token"
export OIDC_USERINFO_ENDPOINT="${OIDC_ISSUER}/userinfo"
export OIDC_REDIRECT_URI="https://console.example.com/oidc/callback"
export AUTH_TOKEN_SECRET="64+ character secret for HS256"
export ACCESS_TOKEN_TTL_SECONDS="900"
export REFRESH_TOKEN_TTL_SECONDS="86400"
```

## Run Locally
```bash
uvicorn app.main:app --reload --port 8080 --app-dir runs/kit/REQ-002/src
```

Interact with:
- `GET http://localhost:8080/api/auth/login`
- `POST http://localhost:8080/api/auth/callback`
- `POST http://localhost:8080/api/auth/refresh`
- `GET http://localhost:8080/api/protected` (requires Bearer token)

## Tests
Run via LTC command or manually:

```bash
pytest -q runs/kit/REQ-002/test
```

## Enterprise CI (Jenkins/GitHub)
- Install deps using requirements file.
- Inject env vars via credential store/secrets manager.
- Execute the LTC `tests` command.
- Collect pytest results from stdout (no extra report files in this kit).

## Troubleshooting
- **Missing tables**: ensure DATABASE_URL reachable; FastAPI lifespan auto-creates schema. For Postgres run migrations from REQ-001 before launching.
- **Token errors**: verify `AUTH_TOKEN_SECRET` consistent across app pods.
- **OIDC failures**: confirm client credentials + redirect URI match IdP config. Use `HTTP_TIMEOUT_SECONDS` env to tune network behavior.
- **SQLite memory in tests**: uses StaticPool for concurrency; no action needed unless overriding DATABASE_URL.

## Notes
- `get_current_user` dependency guards downstream APIs; RBAC layers (REQ-003) should stack on top.
- Replace mock transport overrides with actual IdP connectivity in non-test environments.

KIT Iteration Log
-----------------
- **Targeted REQ-ID(s)**: REQ-002 (next open dependency after REQ-001). Implemented OIDC auth stack per SPEC/PLAN.
- **In/Out of scope**: In scope—OIDC flow, JWT issuance, user persistence, middleware, tests, docs, CI artifacts. Out of scope—RBAC policies (REQ-003), campaign APIs, real IdP secrets storage.
- **How to run tests**: `pytest -q runs/kit/REQ-002/test`
- **Prerequisites**: Python 3.12+, ability to install requirements. Env vars for DB + OIDC endpoints; Postgres recommended outside tests.
- **Dependencies and mocks**: OIDC provider HTTP calls mocked via httpx `MockTransport` in tests to ensure determinism. Database uses SQLite in-memory for tests; schema compatible with Postgres per REQ-001.
- **Product Owner Notes**: Token + OIDC configuration fully environment-driven; ready for RBAC extension in REQ-003.
- **RAG citations**: REQ-001 schema/enums ensured user model alignment (docs/harper/plan.md, SPEC.md).