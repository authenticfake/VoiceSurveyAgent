# HOWTO — REQ-001 Execution

## Prerequisites
- Python 3.12
- Recommended virtual environment
- Network access to the configured OIDC issuer (for real runs)
- Environment variables:
  - `OIDC_ISSUER`
  - `OIDC_CLIENT_ID`
  - `OIDC_CLIENT_SECRET`
  - `OIDC_TOKEN_ENDPOINT`
  - `OIDC_JWKS_URI`
  - Optional: `OIDC_AUDIENCE`

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r runs/kit/REQ-001/requirements.txt
export PYTHONPATH=.
```

## Running Tests
```bash
pytest -q runs/kit/REQ-001/test
```

## Local API Smoke
```python
from app.infra.config import ConfigLoader
from app.auth.domain.role_mapper import ConfigurableRoleMapper
from app.auth.oidc.client import OIDCClient
from app.auth.domain.service import AuthService
from app.auth.rbac import CurrentUserProvider, RBACDependencies
from app.api.http.auth.router import build_auth_router
from app.main import create_app

settings = ConfigLoader().load()
oidc_client = OIDCClient(settings.oidc)
role_mapper = ConfigurableRoleMapper({"roles": {"viewer": Role.viewer}})
user_repo = ...  # inject SQL-backed implementation
auth_service = AuthService(user_repo, oidc_client, role_mapper)
rbac = RBACDependencies(CurrentUserProvider(oidc_client, user_repo, role_mapper))
app = create_app(build_auth_router(auth_service, rbac))
```

## Enterprise Runner Notes
- Jenkins/GitHub Actions should execute the LTC case:
  ```bash
  pytest -q runs/kit/REQ-001/test
  ```
- Ensure `PYTHONPATH=.` during jobs.

## Troubleshooting
- **Missing env vars:** `app.infra.config.ConfigLoader` raises `OIDCConfigurationError`.
- **Invalid tokens:** `AuthenticationError` surfaces as `401/403` with structured JSON.
- **Import errors:** verify `PYTHONPATH=.` and that the virtualenv is active.

KIT Iteration Log
- **Targeted REQ-ID(s)**: REQ-001 (first open dependency-free App track item; foundational for later KITs)
- **In/Out of scope**: Implemented OIDC callback, token validation, role mapping, RBAC dependencies, FastAPI router, config loader, and tests. Persistence, session storage, and DB wiring deferred to REQ-009.
- **How to run tests**: `pytest -q runs/kit/REQ-001/test`
- **Prerequisites**: Python 3.12, ability to install requirements. Real runs need OIDC env vars; tests rely solely on bundled fakes.
- **Dependencies and mocks**: Used in-memory user repo and fake OIDC client inside tests only, as production code stays abstracted via interfaces.
- **Product Owner Notes**: Admin ping route serves as RBAC reference implementation; future routers should reuse `RBACDependencies`.
- **RAG citations**: SPEC.md (auth requirements), PLAN.md (module layout, acceptance), plan.json (lane metadata), TECH_CONSTRAINTS.yaml (Python lane expectations)

```json
{
  "index": [
    {
      "req": "REQ-001",
      "src": [
        "runs/kit/REQ-001/src/app/auth/*",
        "runs/kit/REQ-001/src/app/api/http/auth/*",
        "runs/kit/REQ-001/src/app/infra/config/*",
        "runs/kit/REQ-001/src/app/main.py"
      ],
      "tests": [
        "runs/kit/REQ-001/test/test_auth_flow.py"
      ]
    }
  ]
}