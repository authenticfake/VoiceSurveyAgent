# KIT Documentation — REQ-003: RBAC Authorization Middleware

## Overview

This KIT implements role-based access control (RBAC) for the VoiceSurveyAgent application. It extends the authentication module from REQ-002 to provide fine-grained authorization based on user roles.

## Acceptance Criteria Coverage

| Criterion | Implementation | Status |
|-----------|----------------|--------|
| Role extracted from JWT claims or user database record | `AuthService._extract_role()` extracts from multiple claim locations; `get_current_user()` falls back to database | ✅ |
| Route decorators enforce minimum required role | `RequireRole` class with role hierarchy comparison | ✅ |
| Admin endpoints restricted to admin role only | `require_admin` / `AdminUser` dependency | ✅ |
| Campaign modification restricted to campaign_manager and admin | `require_campaign_manager` / `CampaignManagerUser` dependency | ✅ |
| Denied access attempts logged with user ID, endpoint, and timestamp | Structured logging in `RequireRole.__call__()` | ✅ |

## Architecture

### Role Hierarchy

```
ADMIN (level 2)
    ↓
CAMPAIGN_MANAGER (level 1)
    ↓
VIEWER (level 0)
```

Higher-level roles inherit access to lower-level endpoints.

### Components

1. **AuthService** (`app/auth/service.py`)
   - JWT token validation via JWKS
   - Role extraction from multiple claim formats (direct, Keycloak realm_access, resource_access)

2. **RBAC Dependencies** (`app/auth/rbac.py`)
   - `get_token_payload`: Extracts and validates JWT from Authorization header
   - `get_current_user`: Resolves user from database, creates on first login
   - `RequireRole`: Configurable role requirement with hierarchy support
   - Pre-configured dependencies: `require_viewer`, `require_campaign_manager`, `require_admin`
   - Type aliases: `ViewerUser`, `CampaignManagerUser`, `AdminUser`

3. **Exceptions** (`app/shared/exceptions.py`)
   - `AuthenticationError`: 401 responses for auth failures
   - `AuthorizationError`: 403 responses for insufficient permissions

## Usage

### Protecting Routes

```python
from app.auth import ViewerUser, CampaignManagerUser, AdminUser

@router.get("/campaigns")
async def list_campaigns(user: ViewerUser) -> list[Campaign]:
    """Any authenticated user can list campaigns."""
    ...

@router.post("/campaigns")
async def create_campaign(user: CampaignManagerUser, data: CampaignCreate) -> Campaign:
    """Only campaign managers and admins can create campaigns."""
    ...

@router.put("/admin/config")
async def update_config(user: AdminUser, data: ConfigUpdate) -> Config:
    """Only admins can update system configuration."""
    ...
```

### Custom Role Requirements

```python
from app.auth import RequireRole, UserRole

custom_requirement = RequireRole(UserRole.CAMPAIGN_MANAGER)

@router.get("/custom")
async def custom_endpoint(user: Annotated[UserContext, Depends(custom_requirement)]):
    ...
```

## Configuration

Required environment variables:

```env
OIDC_ISSUER_URL=https://idp.example.com
OIDC_CLIENT_ID=voicesurvey-client
OIDC_ROLE_CLAIM=role
```

## Testing

Run tests:
```bash
cd runs/kit/REQ-003
pytest test/ -v --cov=app.auth
```

## Dependencies

- REQ-002: OIDC authentication integration (provides base auth schemas and middleware)
- REQ-001: Database schema (provides User model)