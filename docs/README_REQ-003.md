# REQ-003: RBAC Authorization Middleware

## Overview

This module implements Role-Based Access Control (RBAC) for the VoiceSurveyAgent API. It provides FastAPI dependencies that enforce role requirements on protected endpoints.

## Features

- **Role Hierarchy**: admin > campaign_manager > viewer
- **Route Decorators**: Pre-configured dependencies for common role requirements
- **Access Logging**: All denied access attempts are logged with full context
- **Flexible Configuration**: Permission sets can be checked programmatically

## Quick Start

```python
from fastapi import APIRouter, Depends
from app.auth.rbac import require_admin, require_campaign_manager, require_viewer
from app.auth.middleware import CurrentUser

router = APIRouter()

@router.get("/admin-only")
async def admin_endpoint(user: CurrentUser = Depends(require_admin)):
    return {"message": f"Hello admin {user.name}"}

@router.post("/campaigns")
async def create_campaign(user: CurrentUser = Depends(require_campaign_manager)):
    return {"message": "Campaign created"}

@router.get("/campaigns")
async def list_campaigns(user: CurrentUser = Depends(require_viewer)):
    return {"campaigns": []}
```

## API Reference

### Dependencies

| Dependency | Required Role | Use Case |
|------------|---------------|----------|
| `require_admin` | admin | Admin configuration, user management |
| `require_campaign_manager` | campaign_manager+ | Campaign CRUD, contact upload |
| `require_viewer` | viewer+ | Read-only access |
| `require_role(Role.X)` | Custom | Flexible role requirement |

### Error Responses

When access is denied, the API returns:

```json
{
  "detail": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "message": "Role 'admin' or higher required",
    "required_role": "admin",
    "current_role": "viewer"
  }
}
```

## Testing

```bash
# Run all RBAC tests
PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src" \
pytest runs/kit/REQ-003/test -v

# Run with coverage
pytest runs/kit/REQ-003/test --cov=runs/kit/REQ-003/src --cov-report=term-missing
```

## Related REQs

- **REQ-001**: Database schema with User.role field
- **REQ-002**: OIDC authentication and JWT validation
- **REQ-004**: Campaign CRUD API (uses RBAC)
- **REQ-019**: Admin configuration API (uses require_admin)
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-003**: RBAC authorization middleware

### Rationale
REQ-003 depends on REQ-002 (OIDC authentication) which is marked as `in_progress`. The RAG context shows REQ-002 implementation is substantially complete with middleware, schemas, and router. REQ-003 extends the authentication layer with role-based access control.

### In Scope
- Role enum with hierarchy (admin > campaign_manager > viewer)
- RBACChecker dependency class for FastAPI route protection
- Pre-configured dependencies: `require_admin`, `require_campaign_manager`, `require_viewer`
- `require_role()` factory function for custom role requirements
- Access denied logging with user ID, endpoint, method, and timestamp
- RolePermissions configuration class for programmatic checks
- Extended middleware to extract role from JWT claims with DB fallback
- Comprehensive unit and integration tests

### Out of Scope
- Actual campaign/admin endpoints (covered by REQ-004, REQ-019)
- Database integration tests (mocked in unit tests)
- OIDC flow changes (handled by REQ-002)

### How to Run Tests

```bash
# Set environment
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
export JWT_SECRET_KEY="test-secret-key-for-testing-purposes-only"

# Install dependencies
pip install -r runs/kit/REQ-003/requirements.txt

# Run tests
pytest runs/kit/REQ-003/test -v

# Run with coverage
pytest runs/kit/REQ-003/test --cov=runs/kit/REQ-003/src --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- REQ-001 and REQ-002 source code available in PYTHONPATH
- Environment variables for JWT configuration

### Dependencies and Mocks
- **Mocked**: Database session (AsyncSession), FastAPI Request object
- **Real**: JWT encoding/decoding via PyJWT, FastAPI test client via httpx
- **Dependency Override**: `get_current_user` is overridden in integration tests to inject test users

### Product Owner Notes
- Role hierarchy follows SPEC: admin has full access, campaign_manager can modify campaigns, viewer is read-only
- Access denied events include all required audit fields per acceptance criteria
- The implementation is designed to be configurable without code changes via the RolePermissions class

### RAG Citations
- `runs/kit/REQ-002/src/app/auth/middleware.py` - Extended CurrentUser model and get_current_user dependency
- `runs/kit/REQ-002/src/app/auth/schemas.py` - Reused TokenPayload and UserProfile schemas
- `runs/kit/REQ-002/src/app/shared/exceptions.py` - Reused InvalidTokenError, TokenExpiredError
- `runs/kit/REQ-002/src/app/shared/logging.py` - Reused get_logger for structured logging
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Referenced user_role enum definition
- `docs/harper/lane-guides/python.md` - Followed FastAPI project structure and testing patterns

```json
{
  "index": [
    {
      "req": "REQ-003",
      "src": [
        "runs/kit/REQ-003/src/app/auth/rbac.py",
        "runs/kit/REQ-003/src/app/auth/middleware.py",
        "runs/kit/REQ-003/src/app/auth/__init__.py"
      ],
      "tests": [
        "runs/kit/REQ-003/test/test_rbac.py",
        "runs/kit/REQ-003/test/conftest.py"
      ]
    }
  ]
}