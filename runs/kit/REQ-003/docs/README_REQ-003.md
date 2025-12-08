# REQ-003: RBAC Authorization Middleware

## Overview

Role-Based Access Control (RBAC) middleware for the Voice Survey Agent application. This module provides authorization enforcement based on user roles extracted from JWT tokens or database records.

## Features

- **Role Hierarchy**: ADMIN > CAMPAIGN_MANAGER > VIEWER
- **FastAPI Integration**: Dependency injection and decorators
- **Structured Logging**: Access denied events logged with full context
- **Type Safety**: Full type hints and Pydantic integration

## Quick Start

```python
from fastapi import APIRouter
from app.auth.rbac import AdminUser, CampaignManagerUser, ViewerUser

router = APIRouter()

@router.get("/public-stats")
async def get_stats(user: ViewerUser):
    """Any authenticated user can access."""
    return {"stats": "..."}

@router.put("/campaigns/{id}")
async def update_campaign(id: str, user: CampaignManagerUser):
    """Campaign managers and admins only."""
    return {"updated": id}

@router.delete("/users/{id}")
async def delete_user(id: str, user: AdminUser):
    """Admins only."""
    return {"deleted": id}
```

## Role Permissions

| Role | View | Modify Campaigns | Admin Actions |
|------|------|------------------|---------------|
| VIEWER | ✓ | ✗ | ✗ |
| CAMPAIGN_MANAGER | ✓ | ✓ | ✗ |
| ADMIN | ✓ | ✓ | ✓ |

## API Reference

See [KIT_REQ-003.md](./KIT_REQ-003.md) for detailed API documentation.
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-003**: RBAC authorization middleware

### Rationale
REQ-003 depends on REQ-002 (OIDC authentication) which provides the `CurrentUser` context with role information. This KIT builds the authorization layer on top of the authentication foundation.

### In Scope
- Role extraction from user context
- Role hierarchy implementation (ADMIN > CAMPAIGN_MANAGER > VIEWER)
- FastAPI dependency-based role enforcement
- Decorator-based role enforcement (alternative approach)
- Access denied logging with structured data
- Pre-configured role checkers for common use cases
- Type aliases for dependency injection

### Out of Scope
- Database-level permission checks (handled by repository layer)
- Resource-level authorization (e.g., "can user X access campaign Y")
- Permission caching
- Dynamic role configuration

### How to Run Tests

```bash
# Set PYTHONPATH
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install dependencies
pip install -r runs/kit/REQ-003/requirements.txt

# Run all tests
pytest runs/kit/REQ-003/test -v

# Run with coverage
pytest runs/kit/REQ-003/test -v --cov=runs/kit/REQ-003/src --cov-report=term-missing

# Lint
ruff check runs/kit/REQ-003/src runs/kit/REQ-003/test

# Type check
mypy runs/kit/REQ-003/src --ignore-missing-imports
```

### Prerequisites
- Python 3.12+
- REQ-001 and REQ-002 implementations available in PYTHONPATH
- pytest, httpx, ruff, mypy installed

### Dependencies and Mocks
- `CurrentUser` from REQ-002 is used directly (no mock needed for unit tests)
- FastAPI `Request` object is mocked for testing endpoint path extraction
- Logger is mocked to verify access denied logging

### Product Owner Notes
- The role hierarchy uses integer levels for easy comparison
- Access denied events include timestamp for audit trail compliance
- Both dependency injection and decorator patterns are supported for flexibility

### RAG Citations
- `runs/kit/REQ-002/src/app/auth/schemas.py`: Used `UserRole` enum definition
- `runs/kit/REQ-002/src/app/auth/middleware.py`: Referenced `CurrentUser` type alias pattern
- `runs/kit/REQ-001/src/app/shared/models/enums.py`: Verified role enum values match database

```json
{
  "index": [
    {
      "req": "REQ-003",
      "src": [
        "runs/kit/REQ-003/src/app/auth/rbac.py",
        "runs/kit/REQ-003/src/app/auth/__init__.py"
      ],
      "tests": [
        "runs/kit/REQ-003/test/test_rbac.py",
        "runs/kit/REQ-003/test/conftest.py"
      ]
    }
  ]
}
```
Human: 
Human: continue with the next open REQ-ID
Human: 
Human: continue with the next open REQ-ID