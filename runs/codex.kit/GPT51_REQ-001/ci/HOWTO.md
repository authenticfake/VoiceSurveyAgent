# HOWTO — REQ-001 OIDC Auth and RBAC

This document explains how to run and test the REQ‑001 implementation locally or in CI.

## 1. Prerequisites

- Python 3.12 (recommended) installed and on `PATH`.
- Access to a shell (bash, zsh, PowerShell, etc.).
- Optional: a running OIDC IdP for manual end-to-end testing.

## 2. Environment Setup

Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r runs/kit/REQ-001/requirements.txt
```

Set minimal OIDC environment variables (for tests these can be dummy values):

```bash
export OIDC_ISSUER="https://example-issuer"
export OIDC_CLIENT_ID="client-id"
export OIDC_CLIENT_SECRET="client-secret"
export OIDC_AUTH_ENDPOINT="https://idp.example.com/auth"
export OIDC_TOKEN_ENDPOINT="https://idp.example.com/token"
export OIDC_JWKS_URI="https://idp.example.com/jwks"
export OIDC_REDIRECT_URI="https://app.example.com/callback"
```

Ensure the repository root is on `PYTHONPATH` (CI does this by default):

```bash
export PYTHONPATH="."
```

## 3. Running Tests

From the repository root:

```bash
pytest -p no:cacheprovider -q runs/kit/REQ-001/test
```

This executes:

- Unit tests for role mapping and RBAC.
- Integration tests for the OIDC login URL, callback, and `/api/auth/me` endpoint using FastAPI’s test client and mocked OIDC provider.

## 4. Running the API Locally

To start the FastAPI app with auth routes:

```bash
uvicorn app.main:app --reload
```

The main endpoints are:

- `GET /api/auth/login-url`
- `GET /api/auth/callback`
- `GET /api/auth/me`

In a real deployment you must:

- Provide a concrete implementation of `UserRepository` in the infra layer.
- Override `get_user_repository` and optionally `get_oidc_authenticator` via FastAPI dependency overrides at app startup.

## 5. CI / Enterprise Runner Notes

- The canonical test contract for this REQ is in `runs/kit/REQ-001/ci/LTC.json`.
- CI systems should:
  - Install dependencies from `runs/kit/REQ-001/requirements.txt`.
  - Execute the `cases[].run` command with `cwd` set to the repository root.
- For Jenkins or similar:
  - Configure a job that:
    - Checks out the repo.
    - Sets the environment variables listed above.
    - Creates a virtualenv and installs the requirements file.
    - Runs the pytest command.

## 6. Troubleshooting

- **Import errors (`ModuleNotFoundError: app...`)**
  - Ensure `PYTHONPATH` includes the repository root, or run commands from the repo root.
- **Settings validation errors**
  - Confirm all required `OIDC_*` environment variables are set and valid URLs.
- **OIDC integration with a real IdP**
  - Update the `OIDC_*` environment variables with real endpoints and credentials.
  - Ensure redirect URI registered at the IdP matches `OIDC_REDIRECT_URI`.
- **Token validation failures**
  - Check that issuer and audience in the ID token match `OIDC_ISSUER` and `OIDC_AUDIENCE`/`OIDC_CLIENT_ID`.
  - Verify JWKS URI is reachable from the API environment.


KIT Iteration Log
- Targeted REQ‑ID(s) and rationale: Implemented REQ-001 (OIDC auth and RBAC) as the first foundational backend requirement without dependencies, per PLAN.
- In/Out of scope for this iteration: In scope: OIDC auth-code flow endpoints, ID token validation, role mapping, RBAC dependencies, minimal app wiring and config loader, and tests. Out of scope: Database-backed UserRepository implementation, full session management beyond bearer ID tokens, integration with other domain routers.
- How to run tests (exact commands): `pytest -p no:cacheprovider -q runs/kit/REQ-001/test`
- Prerequisites (tooling, proxies, secrets, on-prem specifics): Python 3.12, network access to IdP JWKS/token endpoints for real runs (tests mock them), environment variables for OIDC configuration.
- Dependencies and mocks (what was mocked or faked and why): In tests, `InMemoryUserRepo` fakes `UserRepository` and `DummyAsyncClient` fakes OIDC token/JWKS endpoints to keep tests deterministic and avoid real network calls. Production code only depends on abstractions (`UserRepository`, `httpx.AsyncClient`).
- Product Owner Notes: Future REQs should provide a concrete DB-backed `UserRepository` and wire `get_user_repository` via dependency overrides in the application factory. Role mapping may need adjustment once actual IdP group/claim conventions are known.
- RAG citations (which repo/docs snippets were used to decide or implement): Aligned with SPEC.md (auth & RBAC, OIDC, roles), PLAN.md (module layout `app.auth.domain`, `app.auth.oidc`, `app.api.http.auth`, reuse of `app.infra.config`), and plan.json for lane (`python`) and acceptance criteria for REQ-001.

```json
{
  "index": [
    {
      "req": "REQ-001",
      "src": [
        "runs/kit/REQ-001/src/app/auth/domain.py",
        "runs/kit/REQ-001/src/app/auth/oidc.py",
        "runs/kit/REQ-001/src/app/api/http/auth/dependencies.py",
        "runs/kit/REQ-001/src/app/api/http/auth/routes.py",
        "runs/kit/REQ-001/src/app/infra/config.py",
        "runs/kit/REQ-001/src/app/main.py"
      ],
      "tests": [
        "runs/kit/REQ-001/test/auth/test_role_mapping.py",
        "runs/kit/REQ-001/test/auth/test_rbac_dependencies.py",
        "runs/kit/REQ-001/test/auth/test_auth_flow_api.py"
      ]
    }
  ]
}