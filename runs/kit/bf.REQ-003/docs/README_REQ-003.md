# REQ-003: RBAC Authorization Middleware

## Summary

Implements role-based access control (RBAC) for the VoiceSurveyAgent API. Provides FastAPI dependencies for protecting routes based on user roles with a hierarchical permission model.

## Quick Start

### Installation

```bash
# From project root
pip install -e .
```

### Usage

```python
from app.auth import ViewerUser, CampaignManagerUser, AdminUser

# Protect a route - viewer level (any authenticated user)
@router.get("/data")
async def get_data(user: ViewerUser):
    return {"user": user.email}

# Protect a route - campaign manager level
@router.post("/campaigns")
async def create_campaign(user: CampaignManagerUser):
    return {"created_by": user.id}

# Protect a route - admin only
@router.delete("/users/{id}")
async def delete_user(user: AdminUser, id: UUID):
    return {"deleted": id}
```

## Roles

| Role | Level | Can Access |
|------|-------|------------|
| `viewer` | 0 | Read-only endpoints |
| `campaign_manager` | 1 | Campaign CRUD, viewer endpoints |
| `admin` | 2 | All endpoints including system config |

## Files

- `src/app/auth/rbac.py` - RBAC implementation
- `src/app/auth/service.py` - JWT validation service
- `src/app/shared/exceptions.py` - Custom exceptions
- `test/test_rbac.py` - RBAC tests
- `test/test_auth_service.py` - Auth service tests

## Running Tests

```bash
pytest runs/kit/REQ-003/test/ -v