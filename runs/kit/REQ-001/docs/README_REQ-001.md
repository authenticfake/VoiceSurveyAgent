# REQ-001 – OIDC Auth & RBAC

## Contents
- `src/app/auth/*`: Domain models, service layer, OIDC client, RBAC helpers.
- `src/app/api/http/auth/*`: FastAPI router and schemas.
- `src/app/infra/config`: Environment-driven loader that produces `OIDCConfig`.
- `test/`: Pytest suite with fakes for OIDC client and user repository.

## Usage

1. **Install dependencies**
   ```bash
   pip install -r runs/kit/REQ-001/requirements.txt
   ```

2. **Configure environment**  
   Set the following before wiring the router into the main API service:
   - `OIDC_ISSUER`
   - `OIDC_CLIENT_ID`
   - `OIDC_CLIENT_SECRET`
   - `OIDC_TOKEN_ENDPOINT`
   - `OIDC_JWKS_URI`
   - `OIDC_AUDIENCE` (optional)

3. **Wire dependencies**
   ```python
   from app.infra.config import ConfigLoader
   from app.auth.oidc.client import OIDCClient
   from app.auth.domain.role_mapper import ConfigurableRoleMapper
   from app.auth.rbac import CurrentUserProvider, RBACDependencies
   from app.api.http.auth.router import build_auth_router
   from app.main import create_app

   settings = ConfigLoader().load()
   oidc_client = OIDCClient(settings.oidc)
   role_mapper = ConfigurableRoleMapper({"roles": {...}})
   user_repo = ...  # real implementation (REQ-009)
   auth_service = AuthService(user_repo, oidc_client, role_mapper)
   current_user = CurrentUserProvider(oidc_client, user_repo, role_mapper)
   app = create_app(build_auth_router(auth_service, RBACDependencies(current_user)))
   ```

4. **Run tests**
   ```bash
   pytest -q runs/kit/REQ-001/test
   ```

file:/runs/kit/REQ-001/ci/LTC.json
{
  "version": "1.0",
  "req_id": "REQ-001",
  "lane": "python",
  "tools": {
    "tests": true,
    "lint": false,
    "types": false,
    "security": false,
    "build": false
  },
  "commands": {
    "tests": "pytest -q runs/kit/REQ-001/test"
  },
  "cases": [
    {
      "name": "tests",
      "run": "pytest -q runs/kit/REQ-001/test",
      "cwd": ".",
      "pip-file": "runs/kit/REQ-001/requirements.txt",
      "expect": 0
    }
  ],
  "reports": [
    {
      "kind": "junit",
      "path": "runs/kit/REQ-001/reports/junit.xml",
      "format": "junit-xml"
    }
  ],
  "env": {
    "PYTHONPATH": "."
  },
  "normalize": {
    "eval.summary.json": {
      "tests_pass": "cases[].status"
    }
  },
  "gate_policy": {
    "tests_pass": true
  },
  "external_runner": null,
  "constraints_applied": [
    "TECH_CONSTRAINTS:v1.1.0",
    "PLAN:REQ-001 composition-first"
  ]
}

file:/runs/kit/REQ-001/ci/HOWTO.md
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