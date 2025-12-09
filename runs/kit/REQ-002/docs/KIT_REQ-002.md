# KIT Documentation: REQ-002 - OIDC Authentication Integration

## Summary

This KIT implements OIDC (OpenID Connect) authentication integration for the Voice Survey Agent platform. It provides a complete authentication flow including authorization code exchange, JWT token validation, user management, and session handling.

## Acceptance Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| OIDC authorization code flow implemented with configurable IdP endpoints | ✅ | `OIDCClient` class handles full flow |
| JWT tokens validated on every API request via middleware | ✅ | `JWTAuthMiddleware` validates all protected routes |
| User record created or updated on first login with OIDC subject mapping | ✅ | `AuthService._get_or_create_user()` handles this |
| Session tokens have configurable expiration with refresh capability | ✅ | Configurable via environment variables |
| Invalid or expired tokens return 401 with appropriate error message | ✅ | Middleware returns structured error responses |

## Components

### Configuration (`config.py`)
- `AuthConfig`: Dataclass holding all OIDC and JWT configuration
- Loads from environment variables with sensible defaults
- Validates configuration completeness via `is_configured()`

### OIDC Client (`oidc_client.py`)
- `OIDCClient`: Handles OIDC authorization code flow
- Methods:
  - `generate_state()`: Creates CSRF protection state
  - `get_authorization_url()`: Builds IdP redirect URL
  - `exchange_code()`: Exchanges auth code for tokens
  - `refresh_tokens()`: Refreshes access token
  - `get_userinfo()`: Fetches user info from IdP

### JWT Validation (`jwt_validator.py`, `jwks.py`)
- `JWKSClient`: Fetches and caches JWKS from IdP
- `JWTValidator`: Validates JWT tokens using JWKS
- Handles key rotation via cache refresh

### Middleware (`middleware.py`)
- `JWTAuthMiddleware`: FastAPI middleware for token validation
- Configurable public paths (no auth required)
- Stores validated payload in request state

### Service (`service.py`)
- `AuthService`: Orchestrates authentication operations
- User creation/update on first login
- Token validation delegation

### API Routes (`router.py`)
- `GET /api/auth/login`: Initiates OIDC flow
- `GET /api/auth/callback`: Handles IdP callback
- `POST /api/auth/refresh`: Refreshes access token
- `GET /api/auth/me`: Returns current user profile
- `POST /api/auth/logout`: Logs out user

## Dependencies

### From REQ-001
- `User` model from `app.shared.models.user`
- `UserRole` enum from `app.shared.models.enums`
- Database session from `app.shared.database`

### External
- `python-jose`: JWT encoding/decoding
- `httpx`: Async HTTP client for OIDC calls
- `sqlalchemy`: Database ORM

## Test Coverage

- `test_auth_config.py`: Configuration loading tests
- `test_auth_models.py`: Pydantic model validation tests
- `test_jwt_validator.py`: JWT validation tests
- `test_auth_middleware.py`: Middleware integration tests
- `test_auth_service.py`: Service layer tests
- `test_auth_router.py`: API endpoint tests

## Security Considerations

1. **State Parameter**: CSRF protection via cryptographically secure state
2. **Token Validation**: Full JWT validation including signature, expiration, issuer, audience
3. **Key Rotation**: JWKS cache refresh on unknown key ID
4. **Error Handling**: No sensitive information leaked in error responses
5. **HTTPS**: All OIDC endpoints must use HTTPS in production