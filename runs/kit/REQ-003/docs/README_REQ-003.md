# REQ-003: RBAC Authorization Middleware

## Quick Start

```bash
# Set environment
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install dependencies
cd runs/kit/REQ-003
pip install -r requirements.txt

# Run tests
pytest test/ -v
```

## What This Implements

- **Role-based access control** with three roles: `admin`, `campaign_manager`, `viewer`
- **Route decorators** for enforcing minimum required roles
- **Permission-based access** for fine-grained control
- **Access denied logging** with user ID, endpoint, method, and timestamp

## Key Components

### Role Enforcement

```python
from app.auth.rbac import AdminUser, CampaignManagerUser, ViewerUser

@router.get("/admin/config")
async def admin_only(user: AdminUser):
    ...

@router.post("/campaigns")
async def manager_only(user: CampaignManagerUser):
    ...

@router.get("/campaigns")
async def all_users(user: ViewerUser):
    ...
```

### Permission Enforcement

```python
from app.auth.rbac import require_permission, Permission

@router.delete("/exclusions/{id}")
async def delete_exclusion(
    user = Depends(require_permission(Permission.ADMIN_EXCLUSION_MANAGE))
):
    ...
```

## Role Hierarchy

| Role | Can Access |
|------|------------|
| admin | Everything |
| campaign_manager | Campaigns, Contacts, Stats |
| viewer | Read-only access |

## Access Denied Response

When access is denied, the middleware:
1. Returns HTTP 403 Forbidden
2. Logs the attempt with:
   - User ID
   - User role
   - Endpoint path
   - HTTP method
   - Required role/permission
   - Timestamp

## Dependencies

- REQ-001: Database schema
- REQ-002: OIDC authentication
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-003**: RBAC authorization middleware

### Rationale
REQ-003 depends on REQ-002 (OIDC authentication) which provides the `CurrentUser` context with role information. This KIT extends the authentication module with authorization capabilities.

### In Scope
- Role extraction from JWT claims or user database record
- Route decorators (`require_role`, `require_permission`) for enforcing access control
- Admin endpoint restriction to admin role only
- Campaign modification restriction to campaign_manager and admin roles
- Access denied logging with user ID, endpoint, and timestamp
- Type aliases for common role requirements (`AdminUser`, `CampaignManagerUser`, `ViewerUser`)
- Permission enum for fine-grained access control
- Role-permission mapping (configurable without code changes)

### Out of Scope
- Database integration tests (requires running PostgreSQL)
- Full end-to-end tests with real OIDC provider
- UI components for role management
- Dynamic role/permission configuration via API

### How to Run Tests

```bash
# Set PYTHONPATH to include all required KIT sources
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install dependencies
cd runs/kit/REQ-003
pip install -r requirements.txt

# Run all tests
pytest test/ -v --tb=short

# Run with coverage
pytest test/ -v --cov=src --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- pip for dependency management
- REQ-001 and REQ-002 source code available in PYTHONPATH

### Dependencies and Mocks
- **Mocked**: `CurrentUser` context (provided by REQ-002 middleware)
- **Mocked**: HTTP request objects for testing decorators
- **Mocked**: Logger for verifying access denied logging
- **Real**: FastAPI application for integration tests

### Product Owner Notes
- RBAC rules are defined in `ROLE_PERMISSIONS` dictionary and can be modified without code changes
- Permission enum follows `resource:action` naming convention for clarity
- Role hierarchy is: admin > campaign_manager > viewer
- All access denied events are logged with structured JSON format

### RAG Citations
- `runs/kit/REQ-002/src/app/auth/middleware.py` - CurrentUser context and get_current_user dependency
- `runs/kit/REQ-002/src/app/auth/schemas.py` - UserRole enum definition
- `runs/kit/REQ-001/src/app/shared/models/enums.py` - Database enum definitions
- `docs/harper/lane-guides/python.md` - Python lane guide for testing and tooling

### Index

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
        "runs/kit/REQ-003/test/test_rbac_integration.py"
      ]
    }
  ]
}
```
Human: kit REQ-004