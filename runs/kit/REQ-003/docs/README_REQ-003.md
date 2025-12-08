# REQ-003: RBAC Authorization Middleware

## Summary

Implements role-based access control (RBAC) for the VoiceSurveyAgent API, providing:

- Three-tier role hierarchy: `admin` > `campaign_manager` > `viewer`
- FastAPI dependency decorators for route protection
- Permission-based access control
- Structured access denial logging

## Quick Start

### Installation

```bash
pip install -r runs/kit/REQ-003/requirements.txt
```

### Basic Usage

```python
from fastapi import Depends
from app.auth.rbac import require_role, Role

@router.get("/admin/settings")
async def admin_settings(
    role: Role = Depends(require_role(Role.ADMIN))
):
    return {"settings": "..."}
```

### Running Tests

```bash
pytest runs/kit/REQ-003/test/ -v
```

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| Role extracted from JWT claims or user database record | ✅ |
| Route decorators enforce minimum required role | ✅ |
| Admin endpoints restricted to admin role only | ✅ |
| Campaign modification restricted to campaign_manager and admin | ✅ |
| Denied access attempts logged with user ID, endpoint, and timestamp | ✅ |

## Files

- `src/app/auth/rbac/` - RBAC module implementation
- `test/` - Unit and integration tests
- `docs/` - Documentation