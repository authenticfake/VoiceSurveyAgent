# KIT Documentation — REQ-003: RBAC Authorization Middleware

## Overview

This KIT implements Role-Based Access Control (RBAC) for the VoiceSurveyAgent application. It provides:

- Role definitions with hierarchical privilege levels
- Permission-based access control
- FastAPI dependency decorators for route protection
- Structured logging for access denial events
- Configurable RBAC rules via environment variables

## Architecture

### Module Structure

```
app/auth/rbac/
├── __init__.py          # Public API exports
├── roles.py             # Role enum and hierarchy
├── permissions.py       # FastAPI dependencies for access control
├── logging.py           # Access denial logging
└── config.py            # Configuration management
```

### Role Hierarchy

```
admin (100)
  └── campaign_manager (50)
        └── viewer (10)
```

Higher privilege roles inherit access to lower privilege endpoints.

### Permissions

Each role has a defined set of permissions:

| Permission | Viewer | Campaign Manager | Admin |
|------------|--------|------------------|-------|
| campaigns:read | ✓ | ✓ | ✓ |
| campaigns:create | | ✓ | ✓ |
| campaigns:update | | ✓ | ✓ |
| campaigns:delete | | | ✓ |
| config:read | | | ✓ |
| config:update | | | ✓ |
| exclusions:delete | | | ✓ |

## Usage

### Protecting Routes

```python
from fastapi import Depends
from app.auth.rbac import require_role, require_permission, Role

# Require minimum role
@router.get("/admin/config")
async def get_config(
    _: Role = Depends(require_role(Role.ADMIN))
):
    ...

# Require specific permission
@router.post("/campaigns")
async def create_campaign(
    _: Role = Depends(require_permission("campaigns:create"))
):
    ...

# Allow multiple roles
@router.put("/campaigns/{id}")
async def update_campaign(
    _: Role = Depends(require_any_role([Role.ADMIN, Role.CAMPAIGN_MANAGER]))
):
    ...
```

### Configuration

Environment variables:

- `RBAC_ADMIN_PATHS`: Comma-separated admin path prefixes (default: `/api/admin`)
- `RBAC_MANAGER_PATHS`: Comma-separated manager path prefixes (default: `/api/campaigns`)
- `RBAC_LOG_DENIALS`: Whether to log denials (default: `true`)
- `RBAC_LOG_REQUEST_DETAILS`: Whether to log request details (default: `true`)

## Access Denial Logging

All access denials are logged in structured JSON format:

```json
{
  "event": "access_denied",
  "timestamp": "2024-01-15T10:30:00Z",
  "user_id": "user-123",
  "endpoint": "GET /api/admin/config",
  "required_role": "admin",
  "user_role": "viewer",
  "request_context": {
    "method": "GET",
    "path": "/api/admin/config",
    "client_ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "correlation_id": "corr-abc123"
  }
}
```

## Dependencies

- Requires REQ-001 (Database schema) for User model
- Requires REQ-002 (OIDC authentication) for JWT validation and user context

## Testing

Run tests:

```bash
cd runs/kit/REQ-003
pytest test/ -v
```

Coverage includes:
- Role hierarchy validation
- Permission checking
- Route protection decorators
- Access denial logging
- Configuration loading
- FastAPI integration