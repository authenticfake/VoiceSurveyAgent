# KIT Documentation — REQ-003: RBAC Authorization Middleware

## Summary

This KIT implements Role-Based Access Control (RBAC) authorization middleware for the Voice Survey Agent application. It provides role extraction from JWT claims or database records, route decorators for enforcing minimum required roles, and comprehensive access denied logging.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| Role extracted from JWT claims or user database record | ✅ | `rbac.py` - Role extracted via `CurrentUser` from middleware |
| Route decorators enforce minimum required role | ✅ | `require_role()` dependency factory |
| Admin endpoints restricted to admin role only | ✅ | `AdminUser` type alias, `require_role(UserRole.ADMIN)` |
| Campaign modification restricted to campaign_manager and admin | ✅ | `CampaignManagerUser` type alias |
| Denied access attempts logged with user ID, endpoint, and timestamp | ✅ | `log_access_denied()` function with structured logging |

## Architecture

### Components

1. **Permission Enum** (`Permission`)
   - Defines fine-grained permissions (e.g., `campaign:read`, `admin:config:update`)
   - Follows `resource:action` naming convention

2. **Role-Permission Mapping** (`ROLE_PERMISSIONS`)
   - Maps each role to a set of permissions
   - Configurable without code changes

3. **Role Checker Functions**
   - `has_permission(role, permission)` - Check specific permission
   - `has_minimum_role(user_role, required_role)` - Check role hierarchy

4. **Dependency Factories**
   - `require_role(minimum_role)` - Enforce minimum role
   - `require_permission(permission)` - Enforce specific permission

5. **Type Aliases**
   - `AdminUser` - Requires admin role
   - `CampaignManagerUser` - Requires campaign_manager or higher
   - `ViewerUser` - Requires viewer or higher

6. **Access Denied Logging**
   - `AccessDeniedLog` - Structured log entry
   - `log_access_denied()` - Log with correlation data

## Role Hierarchy

```
admin (level 3)
  └── campaign_manager (level 2)
        └── viewer (level 1)
```

## Usage

### Basic Role Enforcement

```python
from app.auth.rbac import require_role, AdminUser
from app.auth.schemas import UserRole

# Using type alias
@router.get("/admin/config")
async def get_config(user: AdminUser):
    return {"config": "data"}

# Using dependency directly
@router.post("/campaigns")
async def create_campaign(
    user = Depends(require_role(UserRole.CAMPAIGN_MANAGER))
):
    return {"id": "new"}
```

### Permission-Based Access

```python
from app.auth.rbac import require_permission, Permission

@router.delete("/exclusions/{id}")
async def delete_exclusion(
    user = Depends(require_permission(Permission.ADMIN_EXCLUSION_MANAGE))
):
    return {"deleted": True}
```

## Dependencies

- REQ-001: Database schema (User model with role field)
- REQ-002: OIDC authentication (CurrentUser context)

## Test Coverage

- Unit tests for permission mappings
- Unit tests for role hierarchy
- Integration tests with FastAPI
- Access denied logging tests

## Files

| File | Purpose |
|------|---------|
| `src/app/auth/rbac.py` | RBAC implementation |
| `src/app/auth/__init__.py` | Module exports |
| `test/test_rbac.py` | Unit tests |
| `test/test_rbac_integration.py` | Integration tests |