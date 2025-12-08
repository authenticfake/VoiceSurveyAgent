# KIT Documentation: REQ-002 - OIDC Authentication Integration

## Overview

This KIT implements OIDC (OpenID Connect) authentication integration for the voicesurveyagent application. It provides:

- OIDC authorization code flow with configurable IdP endpoints
- JWT token validation on every API request via middleware
- User record creation/update on first login with OIDC subject mapping
- Session tokens with configurable expiration and refresh capability
- Proper error handling with 401 responses for invalid/expired tokens

## Architecture

### Components

```
app/auth/
├── __init__.py      # Module exports
├── schemas.py       # Pydantic models for auth data
├── service.py       # OIDC and JWT business logic
├── middleware.py    # FastAPI middleware for token validation
└── router.py        # API endpoints for auth flow
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

### GET /api/auth/login
Initiates OIDC authorization code flow.

**Response:**
```json
{
  "authorization_url": "https://idp.example.com/authorize?...",
  "state": "random-state-string"
}
```

### GET /api/auth/callback
Handles OIDC callback and exchanges code for tokens.

**Query Parameters:**
- `code`: Authorization code from IdP
- `state`: State parameter for validation

**Response:**
```json
{
  "access_token": "jwt-token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh-token",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "role": "viewer"
  }
}
```

### POST /api/auth/refresh
Refreshes access token using refresh token.

### GET /api/auth/me
Returns current user profile (requires authentication).

### POST /api/auth/logout
Logs out current user (client should discard tokens).

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| OIDC_ISSUER | OIDC provider URL | Required |
| OIDC_CLIENT_ID | OAuth client ID | voicesurveyagent |
| OIDC_CLIENT_SECRET | OAuth client secret | Required |
| OIDC_REDIRECT_URI | Callback URL | http://localhost:8000/api/auth/callback |
| JWT_SECRET_KEY | JWT signing key | Required |
| JWT_ALGORITHM | JWT algorithm | HS256 |
| JWT_EXPIRATION_MINUTES | Token expiration | 60 |

## Security Considerations

1. **State Parameter**: Random state is generated for each login to prevent CSRF
2. **Token Validation**: All tokens are validated for signature, expiration, and audience
3. **User Creation**: New users are created with minimal permissions (viewer role)
4. **Secrets**: All secrets should be stored in AWS Secrets Manager in production

## Dependencies

- `PyJWT`: JWT encoding/decoding
- `httpx`: Async HTTP client for OIDC discovery
- `cryptography`: Cryptographic operations for JWT
- `pydantic`: Data validation and serialization

## Testing

Tests cover:
- OIDC initialization and discovery
- Authorization URL generation
- Token exchange and validation
- User creation and retrieval
- Middleware authentication flow
- API endpoint behavior