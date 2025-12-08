# REQ-003: RBAC Authorization Middleware

## Quick Start

### Installation

The RBAC module is part of the `app.auth` package. No additional dependencies required beyond REQ-002.

### Basic Usage

```python
from fastapi import APIRouter, Depends
from app.auth.dependencies import require_admin, require_campaign_manager

router = APIRouter()

@router.get("/admin/settings", dependencies=[Depends(require_admin())])
async def admin_only():
    return {"access": "admin"}

@router.post("/campaigns", dependencies=[Depends(require_campaign_manager())])
async def manager_or_admin():
    return {"access": "manager+"}
```

## Running Tests

```bash
# From project root
cd runs/kit/REQ-003

# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest test/test_rbac.py -v

# Run with coverage
pytest test/test_rbac.py --cov=app.auth.rbac --cov-report=term-missing
```

## API Reference

### Dependencies

| Function | Description |
|----------|-------------|
| `require_admin()` | Requires admin role |
| `require_campaign_manager()` | Requires campaign_manager or admin |
| `require_viewer()` | Requires any authenticated user |
| `require_permission(perm)` | Requires specific permission |
| `require_any_permission(*perms)` | Requires any of the permissions |
| `require_all_permissions(*perms)` | Requires all permissions |

### Type Aliases

| Alias | Equivalent |
|-------|------------|
| `AdminRequired` | `Annotated[None, Depends(require_admin())]` |
| `CampaignManagerRequired` | `Annotated[None, Depends(require_campaign_manager())]` |
| `ViewerRequired` | `Annotated[None, Depends(require_viewer())]` |

## Troubleshooting

### 401 Unauthorized

The user is not authenticated. Ensure:
1. Auth middleware is configured
2. Valid JWT token is provided
3. `request.state.user` is set

### 403 Forbidden

The user lacks required permissions. Check:
1. User's role in database
2. Required permission for the endpoint
3. Role-permission mapping in `ROLE_PERMISSIONS`

### Logging

Access denials are logged at WARNING level:

```json
{
  "message": "Access denied",
  "user_id": "uuid",
  "endpoint": "PUT /admin/config",
  "reason": "minimum_role=admin"
}