# KIT Documentation — REQ-003: RBAC Authorization Middleware

## Overview

This KIT implements Role-Based Access Control (RBAC) for the Voice Survey Agent application. It provides:

1. **Role-Permission Mapping**: Defines what each role (admin, campaign_manager, viewer) can do
2. **Permission Checking**: Functions to verify if a role has specific permissions
3. **FastAPI Dependencies**: Reusable dependencies for protecting routes
4. **Decorator Support**: For protecting service methods outside of FastAPI context
5. **Access Logging**: Denied access attempts are logged with user ID, endpoint, and timestamp

## Architecture

### Role Hierarchy

```
admin (level 3)
  └── campaign_manager (level 2)
        └── viewer (level 1)
```

Higher-level roles inherit access to lower-level role requirements.

### Permission Categories

| Category | Permissions |
|----------|-------------|
| Campaign | create, read, update, delete, activate |
| Contact | read, upload, export |
| Exclusion | read, manage |
| Admin | config:read, config:write |
| Stats | read, export |

### Role Permissions

| Permission | Admin | Campaign Manager | Viewer |
|------------|-------|------------------|--------|
| campaign:create | ✓ | ✓ | ✗ |
| campaign:read | ✓ | ✓ | ✓ |
| campaign:update | ✓ | ✓ | ✗ |
| campaign:delete | ✓ | ✓ | ✗ |
| campaign:activate | ✓ | ✓ | ✗ |
| contact:read | ✓ | ✓ | ✓ |
| contact:upload | ✓ | ✓ | ✗ |
| contact:export | ✓ | ✓ | ✗ |
| exclusion:read | ✓ | ✓ | ✗ |
| exclusion:manage | ✓ | ✗ | ✗ |
| admin:config:read | ✓ | ✗ | ✗ |
| admin:config:write | ✓ | ✗ | ✗ |
| stats:read | ✓ | ✓ | ✓ |
| stats:export | ✓ | ✓ | ✗ |

## Usage

### Protecting Routes with Dependencies

```python
from fastapi import APIRouter, Depends
from app.auth.dependencies import (
    require_admin,
    require_campaign_manager,
    require_viewer,
    require_permission,
    Permission,
)

router = APIRouter()

# Require admin role
@router.get("/admin/config", dependencies=[Depends(require_admin())])
async def get_admin_config():
    ...

# Require campaign_manager or higher
@router.post("/campaigns", dependencies=[Depends(require_campaign_manager())])
async def create_campaign():
    ...

# Require specific permission
@router.post(
    "/campaigns/{id}/contacts/upload",
    dependencies=[Depends(require_permission(Permission.CONTACT_UPLOAD))]
)
async def upload_contacts():
    ...

# Require any of multiple permissions
@router.get(
    "/reports",
    dependencies=[Depends(require_any_permission(
        Permission.STATS_READ,
        Permission.STATS_EXPORT
    ))]
)
async def get_reports():
    ...
```

### Using Type Aliases

```python
from app.auth.dependencies import AdminRequired, CampaignManagerRequired

@router.put("/admin/config")
async def update_config(_: AdminRequired):
    ...

@router.post("/campaigns")
async def create_campaign(_: CampaignManagerRequired):
    ...
```

### Protecting Service Methods

```python
from app.auth.rbac import rbac_required, Permission
from app.auth.schemas import UserRole

class CampaignService:
    @rbac_required(minimum_role=UserRole.CAMPAIGN_MANAGER)
    async def create_campaign(self, user, data):
        ...

    @rbac_required(permission=Permission.CAMPAIGN_DELETE)
    async def delete_campaign(self, user, campaign_id):
        ...
```

## Files

| File | Purpose |
|------|---------|
| `src/app/auth/rbac.py` | Core RBAC implementation |
| `src/app/auth/dependencies.py` | FastAPI dependency exports |
| `test/test_rbac.py` | Comprehensive test suite |

## Dependencies

- REQ-001: Database schema (User model with role field)
- REQ-002: OIDC authentication (provides user context in request.state)

## Acceptance Criteria Verification

| Criterion | Implementation |
|-----------|----------------|
| Role extracted from JWT claims or user database record | `RBACChecker` reads `request.state.user.role` set by auth middleware |
| Route decorators enforce minimum required role | `require_admin()`, `require_campaign_manager()`, `require_viewer()` |
| Admin endpoints restricted to admin role only | `require_admin()` dependency |
| Campaign modification restricted to campaign_manager and admin | `require_campaign_manager()` or `require_permission(Permission.CAMPAIGN_*)` |
| Denied access attempts logged with user ID, endpoint, and timestamp | `_log_denied()` method logs with structured JSON |