# KIT Documentation: REQ-003 - RBAC Authorization Middleware

## Summary

This KIT implements Role-Based Access Control (RBAC) middleware for the Voice Survey Agent application. It provides a comprehensive authorization layer that enforces role-based permissions on API endpoints.

## Acceptance Criteria Coverage

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| Role extracted from JWT claims or user database record | ✅ | `RoleChecker` extracts role from `CurrentUser` context |
| Route decorators enforce minimum required role | ✅ | `require_role()` factory and `rbac_decorator()` |
| Admin endpoints restricted to admin role only | ✅ | `require_admin` / `AdminUser` type alias |
| Campaign modification restricted to campaign_manager and admin | ✅ | `can_modify_campaigns()` and `CampaignManagerUser` |
| Denied access attempts logged with user ID, endpoint, and timestamp | ✅ | `log_access_denied()` with structured logging |

## Components

### Core Functions

- `has_minimum_role(user_role, required_role)`: Check if user meets minimum role requirement
- `can_modify_campaigns(role)`: Check campaign modification permission
- `is_admin(role)`: Check if role is admin

### Dependencies

- `require_role(role)`: Factory for creating role checker dependencies
- `require_viewer`: Pre-configured viewer role checker
- `require_campaign_manager`: Pre-configured campaign manager role checker
- `require_admin`: Pre-configured admin role checker

### Type Aliases

- `ViewerUser`: Annotated type for viewer-level access
- `CampaignManagerUser`: Annotated type for campaign manager access
- `AdminUser`: Annotated type for admin access

### Decorator

- `rbac_decorator(role)`: Alternative decorator-based approach for role enforcement

## Dependencies

- REQ-001: Database schema (User model)
- REQ-002: OIDC authentication (CurrentUser, UserRole)

## Test Coverage

- Role hierarchy tests
- Permission check tests
- Access denied logging tests
- FastAPI integration tests
- Decorator tests

## Files

| Path | Purpose |
|------|---------|
| `src/app/auth/rbac.py` | Main RBAC implementation |
| `src/app/auth/__init__.py` | Module exports |
| `test/test_rbac.py` | Comprehensive test suite |
| `test/conftest.py` | Test fixtures |