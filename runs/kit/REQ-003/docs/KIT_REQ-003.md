# KIT Documentation: REQ-003 - RBAC Authorization Middleware

## Summary

REQ-003 implements Role-Based Access Control (RBAC) authorization middleware for the VoiceSurveyAgent application. This builds on the OIDC authentication from REQ-002 to enforce role-based permissions across API endpoints.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| Role extracted from JWT claims or user database record | ✅ | `middleware.py` - `get_current_user()` extracts role from JWT, falls back to DB |
| Route decorators enforce minimum required role | ✅ | `rbac.py` - `RBACChecker` class with `require_admin`, `require_campaign_manager`, `require_viewer` |
| Admin endpoints restricted to admin role only | ✅ | `require_admin` dependency enforces admin-only access |
| Campaign modification restricted to campaign_manager and admin | ✅ | `require_campaign_manager` allows both roles via hierarchy |
| Denied access attempts logged with user ID, endpoint, and timestamp | ✅ | `rbac.py` - `log_access_denied()` and logging in `RBACChecker.__call__()` |

## Architecture

### Components

```
app/auth/
├── __init__.py          # Module exports
├── middleware.py        # JWT validation, CurrentUser extraction (extended from REQ-002)
└── rbac.py             # RBAC checker, Role enum, permissions config
```

### Role Hierarchy

```
admin (3) > campaign_manager (2) > viewer (1)
```

- **admin**: Full access to all endpoints including admin configuration
- **campaign_manager**: Can create/modify campaigns, upload contacts, export data
- **viewer**: Read-only access to campaigns and statistics

### Key Classes

#### `Role` Enum
- Defines the three roles with string values
- Implements `has_permission()` for hierarchy checking
- Provides `from_string()` for safe conversion

#### `RBACChecker`
- FastAPI dependency class for role enforcement
- Logs denied access attempts with full context
- Returns 403 Forbidden with structured error details

#### `RolePermissions`
- Configuration class defining permission sets per operation
- Used for programmatic permission checks outside routes

## Usage

### Route Protection

```python
from app.auth.rbac import require_admin, require_campaign_manager

@router.get("/admin/config")
async def admin_only(user: CurrentUser = Depends(require_admin)):
    ...

@router.post("/campaigns")
async def create_campaign(user: CurrentUser = Depends(require_campaign_manager)):
    ...
```

### Programmatic Checks

```python
from app.auth.rbac import RolePermissions, check_role_permission

if RolePermissions.can_perform(user.role, RolePermissions.CAMPAIGN_CREATE):
    # Allow operation
```

## Dependencies

- REQ-001: Database schema (User model with role field)
- REQ-002: OIDC authentication (JWT validation, CurrentUser)

## Test Coverage

- Unit tests for Role enum and hierarchy
- Unit tests for RBACChecker class
- Integration tests with FastAPI test client
- Tests for access denied logging
- Tests for permission configuration

## Security Considerations

1. Role is primarily extracted from JWT claims for performance
2. Database fallback ensures role changes are eventually consistent
3. All denied access attempts are logged for audit
4. Structured error responses don't leak sensitive information