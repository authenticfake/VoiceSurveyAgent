# REQ-001: OIDC Authentication and RBAC

## Quick Start

```bash
# Setup
cd runs/kit/REQ-001
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
export SKIP_OIDC_DISCOVERY=true

# Run tests
pytest test -v

# Start server
uvicorn app.main:app --reload
```

## What This Implements

- OIDC authentication flow (authorization code)
- JWT token validation
- Role-based access control (admin, campaign_manager, viewer)
- Reusable FastAPI dependencies for protected routes

## API Endpoints

- `GET /api/auth/login` - Get authorization URL
- `POST /api/auth/callback` - Exchange code for tokens
- `GET /api/auth/me` - Get current user (requires auth)
- `GET /api/protected/*` - Example protected routes

## For Other REQs

Import auth dependencies:

```python
from app.auth.dependencies import get_current_user, RequireWriter
from app.auth.domain import User, UserRole
```
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-001**: OIDC auth and RBAC for backend APIs

### Rationale
REQ-001 is the first open REQ with no dependencies, making it the correct starting point per the iteration strategy (Batch 1 - Foundations).

### In Scope
- OIDC client implementation with discovery, authorization URL generation, code exchange, and token validation
- User domain model with roles (admin, campaign_manager, viewer)
- RBAC policy definitions and enforcement
- FastAPI dependencies for authentication and role-based authorization
- User repository interface with in-memory implementation for testing
- Auth service for handling authentication flows
- API routes for login initiation, OAuth callback, and user info
- Example protected routes demonstrating RBAC
- Comprehensive unit and integration tests
- LTC and HOWTO documentation

### Out of Scope
- Database persistence (deferred to REQ-009)
- Session management with Redis
- Token refresh flow
- Audit logging for auth events
- Full OIDC logout with provider end_session_endpoint

### How to Run Tests

```bash
# From repository root
export PYTHONPATH="${PYTHONPATH}:$(pwd)/runs/kit/REQ-001/src"
export SKIP_OIDC_DISCOVERY=true

# Install dependencies
pip install -r runs/kit/REQ-001/requirements.txt

# Run all tests
pytest runs/kit/REQ-001/test -v

# Run with coverage
pytest runs/kit/REQ-001/test -v --cov=app --cov-report=html
```

### Prerequisites
- Python 3.12+
- pip
- Virtual environment (recommended)

### Dependencies and Mocks
- **OIDC Provider**: Mocked in tests via `patch` on `OIDCClient` methods
- **User Repository**: `InMemoryUserRepository` used for testing; will be replaced with SQLAlchemy implementation in REQ-009
- **Token Validation**: Mocked JWKS and JWT validation in tests

### Product Owner Notes
- The implementation uses an in-memory user repository which is suitable for testing but must be replaced with a database-backed implementation in REQ-009
- OIDC discovery can be skipped via `SKIP_OIDC_DISCOVERY=true` for local development without an IdP
- Role mapping from OIDC claims is not implemented; users default to VIEWER role and must be promoted via admin action or database update

### RAG Citations
- SPEC.md: Authentication & Authorization requirements, User entity definition, RBAC roles
- PLAN.md: REQ-001 acceptance criteria, module/namespace plan for `app.auth`
- plan.json: Lane (python), dependencies (none), test profile
- TECH_CONSTRAINTS.yaml: Python 3.12+, FastAPI, OIDC authentication, RBAC authorization

### Index

```json
{
  "index": [
    {
      "req": "REQ-001",
      "src": [
        "runs/kit/REQ-001/src/app/__init__.py",
        "runs/kit/REQ-001/src/app/auth/__init__.py",
        "runs/kit/REQ-001/src/app/auth/domain.py",
        "runs/kit/REQ-001/src/app/auth/oidc.py",
        "runs/kit/REQ-001/src/app/auth/errors.py",
        "runs/kit/REQ-001/src/app/auth/dependencies.py",
        "runs/kit/REQ-001/src/app/auth/repository.py",
        "runs/kit/REQ-001/src/app/auth/service.py",
        "runs/kit/REQ-001/src/app/api/__init__.py",
        "runs/kit/REQ-001/src/app/api/http/__init__.py",
        "runs/kit/REQ-001/src/app/api/http/auth.py",
        "runs/kit/REQ-001/src/app/api/http/errors.py",
        "runs/kit/REQ-001/src/app/api/http/protected.py",
        "runs/kit/REQ-001/src/app/main.py"
      ],
      "tests": [
        "runs/kit/REQ-001/test/__init__.py",
        "runs/kit/REQ-001/test/conftest.py",
        "runs/kit/REQ-001/test/auth/__init__.py",
        "runs/kit/REQ-001/test/auth/test_domain.py",
        "runs/kit/REQ-001/test/auth/test_oidc.py",
        "runs/kit/REQ-001/test/auth/test_repository.py",
        "runs/kit/REQ-001/test/auth/test_dependencies.py",
        "runs/kit/REQ-001/test/auth/test_service.py",
        "runs/kit/REQ-001/test/api/__init__.py",
        "runs/kit/REQ-001/test/api/test_auth_routes.py",
        "runs/kit/REQ-001/test/api/curl_tests.json"
      ],
      "docs": [
        "runs/kit/REQ-001/docs/KIT_REQ-001.md",
        "runs/kit/REQ-001/docs/README_REQ-001.md"
      ],
      "ci": [
        "runs/kit/REQ-001/ci/LTC.json",
        "runs/kit/REQ-001/ci/HOWTO.md"
      ]
    }
  ]
}