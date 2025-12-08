# KIT Documentation - REQ-001

## REQ-001: OIDC Auth and RBAC for Backend APIs

### Summary

This KIT implements OIDC-based authentication and role-based access control (RBAC) for the Voice Survey Agent backend APIs. It provides the foundational security layer that all other REQs will depend on.

### Acceptance Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| OIDC login exchanges code for tokens and validates ID token | ✅ Implemented | `OIDCClient.exchange_code()` and `validate_id_token()` |
| RBAC middleware enforces role requirements for protected routes | ✅ Implemented | `require_role()` dependency |
| Unauthorized and unauthenticated requests return structured error responses | ✅ Implemented | Consistent `{code, message}` format |
| Viewer, campaign_manager, admin roles behave per SPEC permissions | ✅ Implemented | `RBACPolicy` class |
| Auth modules expose reusable dependencies for other routers | ✅ Implemented | Exported from `app.auth` |

### Architecture

```
app/
├── auth/
│   ├── __init__.py          # Public exports
│   ├── domain.py             # User, UserRole, RBACPolicy models
│   ├── oidc.py               # OIDCClient, OIDCConfig, TokenPayload
│   ├── errors.py             # Auth-specific exceptions
│   ├── dependencies.py       # FastAPI dependencies for auth/RBAC
│   ├── repository.py         # UserRepository interface + InMemory impl
│   └── service.py            # AuthService for auth flows
├── api/
│   └── http/
│       ├── auth.py           # Auth API routes
│       ├── protected.py      # Example protected routes
│       └── errors.py         # Common error schemas
└── main.py                   # FastAPI app entry point
```

### Key Components

#### Domain Models (`app.auth.domain`)

- **UserRole**: Enum with `admin`, `campaign_manager`, `viewer`
- **RBACPolicy**: Static methods for permission checks
- **User**: Core user model with OIDC subject, email, name, role

#### OIDC Client (`app.auth.oidc`)

- **OIDCConfig**: Configuration for OIDC provider
- **OIDCClient**: Handles discovery, authorization URLs, token exchange, validation
- **TokenPayload**: Decoded JWT claims

#### Dependencies (`app.auth.dependencies`)

- **get_current_user**: Extracts and validates user from Bearer token
- **require_role(*roles)**: Factory for role-checking dependencies
- **RequireAdmin/RequireWriter/RequireReader**: Pre-configured role checks

### Usage Examples

```python
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user, require_role, RequireWriter
from app.auth.domain import User, UserRole

router = APIRouter()

# Any authenticated user
@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return {"email": user.email}

# Specific roles
@router.post("/campaigns")
async def create_campaign(user: User = RequireWriter):
    return {"created_by": user.id}

# Custom role check
@router.delete("/admin/users/{id}")
async def delete_user(
    user: User = Depends(require_role(UserRole.ADMIN))
):
    return {"deleted": True}
```

### Error Responses

All auth errors follow a consistent schema:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable message"
}
```

Error codes:
- `MISSING_TOKEN`: No Authorization header
- `TOKEN_INVALID`: Token validation failed
- `TOKEN_EXPIRED`: Token has expired
- `USER_NOT_FOUND`: User not in database
- `INSUFFICIENT_PERMISSIONS`: Role check failed

### Testing

Tests cover:
- Domain model validation
- OIDC client operations (mocked)
- Repository CRUD operations
- Dependency injection and role checks
- API endpoint integration

Run tests:
```bash
PYTHONPATH=runs/kit/REQ-001/src pytest runs/kit/REQ-001/test -v
```

### Dependencies

- FastAPI >= 0.109.0
- Pydantic >= 2.5.0
- python-jose[cryptography] >= 3.3.0
- httpx >= 0.26.0

### Future Considerations

1. **Database Integration**: Replace `InMemoryUserRepository` with SQLAlchemy implementation in REQ-009
2. **Session Management**: Add Redis-based session storage if needed
3. **Token Refresh**: Implement refresh token flow
4. **Audit Logging**: Add auth event logging for compliance