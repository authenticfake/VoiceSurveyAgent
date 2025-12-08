# KIT Documentation: REQ-002 - OIDC Authentication Integration

## Overview

This KIT implements OIDC (OpenID Connect) authentication integration for the Voice Survey Agent application. It provides secure user authentication via an external Identity Provider (IdP) using the authorization code flow.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| OIDC authorization code flow implemented with configurable IdP endpoints | ✅ | `AuthService.generate_authorization_url()`, `AuthService.exchange_code_for_tokens()` |
| JWT tokens validated on every API request via middleware | ✅ | `AuthMiddleware`, `get_current_user` dependency |
| User record created or updated on first login with OIDC subject mapping | ✅ | `AuthService.get_or_create_user()` |
| Session tokens have configurable expiration with refresh capability | ✅ | `AuthService.refresh_tokens()`, settings-based expiration |
| Invalid or expired tokens return 401 with appropriate error message | ✅ | `InvalidTokenError`, `ExpiredTokenError` exceptions |

## Architecture

### Components

```
app/auth/
├── __init__.py          # Module exports
├── schemas.py           # Pydantic models for auth data
├── exceptions.py        # Custom authentication exceptions
├── service.py           # Core authentication logic
├── middleware.py        # JWT validation middleware
└── router.py            # REST API endpoints
```

### Flow Diagram

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Client  │────▶│ /login  │────▶│  IdP    │────▶│/callback│
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                                                     │
                                                     ▼
                                              ┌─────────────┐
                                              │ JWT Token   │
                                              │ + User Ctx  │
                                              └─────────────┘
```

## API Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/api/auth/login` | Initiate OIDC login | No |
| GET | `/api/auth/callback` | Handle OIDC callback | No |
| POST | `/api/auth/refresh` | Refresh access token | No |
| GET | `/api/auth/me` | Get current user profile | Yes |
| POST | `/api/auth/logout` | Logout (client-side) | Yes |

## Configuration

Required environment variables:

```bash
OIDC_ISSUER=https://idp.example.com
OIDC_AUTHORIZATION_ENDPOINT=https://idp.example.com/authorize
OIDC_TOKEN_ENDPOINT=https://idp.example.com/token
OIDC_USERINFO_ENDPOINT=https://idp.example.com/userinfo
OIDC_JWKS_URI=https://idp.example.com/.well-known/jwks.json
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=http://localhost:8000/api/auth/callback
```

## Dependencies

- REQ-001: Database schema (User model)

## Security Considerations

1. **CSRF Protection**: State parameter validated on callback
2. **Token Validation**: RS256 signature verification via JWKS
3. **Secure Storage**: Client secrets via environment variables
4. **Token Expiration**: Configurable expiration with refresh capability

## Testing

```bash
# Run all auth tests
pytest runs/kit/REQ-002/test/ -v

# Run with coverage
pytest runs/kit/REQ-002/test/ --cov=runs/kit/REQ-002/src/app/auth