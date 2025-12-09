# REQ-002: OIDC Authentication Integration

## Overview

This module provides OIDC (OpenID Connect) authentication for the Voice Survey Agent platform. It implements the authorization code flow for user authentication and JWT token validation for API protection.

## Features

- **OIDC Authorization Code Flow**: Complete implementation of OAuth 2.0 authorization code flow with PKCE support ready
- **JWT Token Validation**: Validates access tokens using JWKS from the IdP
- **User Management**: Automatic user creation/update on first login
- **Session Management**: Configurable token expiration with refresh capability
- **Middleware Protection**: FastAPI middleware for protecting API routes

## Quick Start

### 1. Configure Environment

bash
export OIDC_ISSUER_URL="https://your-idp.example.com"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_JWKS_URI="https://your-idp.example.com/.well-known/jwks.json"

### 2. Add to FastAPI App

python
from fastapi import FastAPI
from app.auth.config import AuthConfig
from app.auth.middleware import JWTAuthMiddleware
from app.auth.router import router as auth_router

app = FastAPI()
config = AuthConfig.from_env()
app.add_middleware(JWTAuthMiddleware, config=config)
app.include_router(auth_router)

### 3. Protect Routes

python
from fastapi import Depends
from app.auth.dependencies import get_current_user
from app.shared.models.user import User

@app.get("/api/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"message": f"Hello, {user.name}!"}

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | GET | Initiates OIDC login flow |
| `/api/auth/callback` | GET | Handles IdP callback |
| `/api/auth/refresh` | POST | Refreshes access token |
| `/api/auth/me` | GET | Returns current user profile |
| `/api/auth/logout` | POST | Logs out user |

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `OIDC_ISSUER_URL` | - | IdP issuer URL |
| `OIDC_CLIENT_ID` | - | OAuth client ID |
| `OIDC_CLIENT_SECRET` | - | OAuth client secret |
| `OIDC_JWKS_URI` | - | JWKS endpoint URL |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token lifetime |
| `JWT_ALGORITHM` | RS256 | JWT signing algorithm |

## Error Responses

All authentication errors return a consistent format:

json
{
  "error": "error_code",
  "error_description": "Human-readable description"
}

Common error codes:
- `missing_token`: No Authorization header
- `invalid_token`: Token validation failed
- `token_expired`: Token has expired
- `invalid_header`: Malformed Authorization header

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-002**: OIDC authentication integration

### Rationale
REQ-002 is the next open requirement after REQ-001 (Database schema and migrations) which is marked as in_progress. REQ-002 depends on REQ-001 for the User model and database infrastructure.

### In Scope
- OIDC authorization code flow implementation
- JWT token validation middleware
- User record creation/update on first login
- Session tokens with configurable expiration
- Refresh token capability
- 401 responses for invalid/expired tokens
- Login endpoint returning user profile with role

### Out of Scope
- RBAC authorization (REQ-003)
- Token blacklisting for logout
- Multi-factor authentication
- Social login providers

### How to Run Tests

bash
# Set PYTHONPATH to include both REQ-001 and REQ-002 sources
export PYTHONPATH="runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install dependencies
pip install -r runs/kit/REQ-002/requirements.txt

# Run tests
pytest runs/kit/REQ-002/test -v

# Run with coverage
pytest runs/kit/REQ-002/test -v --cov=runs/kit/REQ-002/src --cov-report=term-missing

### Prerequisites
- Python 3.12+
- PostgreSQL with REQ-001 migrations applied
- OIDC-compliant Identity Provider (for integration testing)
- Required packages: fastapi, pydantic, python-jose, httpx, sqlalchemy, asyncpg

### Dependencies and Mocks
- **Database**: Uses SQLAlchemy async session from REQ-001's `app.shared.database`
- **User Model**: Reuses `User` model from REQ-001's `app.shared.models.user`
- **Enums**: Reuses `UserRole` enum from REQ-001's `app.shared.models.enums`
- **OIDC Provider**: Mocked in tests using `MockJWKSClient` and mock HTTP responses
- **JWT Validation**: Uses `python-jose` with HS256 for testing (RS256 in production)

### Product Owner Notes
- The implementation uses in-memory state storage for CSRF protection. In production, this should be replaced with Redis for distributed deployments.
- Token blacklisting for logout is not implemented; clients should discard tokens on logout.
- The middleware skips authentication for paths starting with `/api/auth/` to allow the login flow.

### RAG Citations
- `runs/kit/REQ-001/src/app/shared/models/enums.py`: Reused `UserRole` enum
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql`: Referenced users table schema for User model alignment
- `runs/kit/REQ-001/src/storage/seed/seed.sql`: Referenced seed data structure for user roles

json
{
  "index": [
    {
      "req": "REQ-002",
      "src": [
        "runs/kit/REQ-002/src/app/auth/__init__.py",
        "runs/kit/REQ-002/src/app/auth/config.py",
        "runs/kit/REQ-002/src/app/auth/models.py",
        "runs/kit/REQ-002/src/app/auth/exceptions.py",
        "runs/kit/REQ-002/src/app/auth/jwks.py",
        "runs/kit/REQ-002/src/app/auth/oidc_client.py",
        "runs/kit/REQ-002/src/app/auth/jwt_validator.py",
        "runs/kit/REQ-002/src/app/auth/service.py",
        "runs/kit/REQ-002/src/app/auth/middleware.py",
        "runs/kit/REQ-002/src/app/auth/dependencies.py",
        "runs/kit/REQ-002/src/app/auth/router.py",
        "runs/kit/REQ-002/src/app/shared/database.py",
        "runs/kit/REQ-002/src/app/shared/models/user.py"
      ],
      "tests": [
        "runs/kit/REQ-002/test/test_auth_config.py",
        "runs/kit/REQ-002/test/test_auth_models.py",
        "runs/kit/REQ-002/test/test_jwt_validator.py",
        "runs/kit/REQ-002/test/test_auth_middleware.py",
        "runs/kit/REQ-002/test/test_auth_service.py",
        "runs/kit/REQ-002/test/test_auth_router.py",
        "runs/kit/REQ-002/test/conftest.py"
      ]
    }
  ]
}