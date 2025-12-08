# REQ-002: OIDC Authentication Integration

## Summary

Implements OIDC-based authentication for the VoiceSurveyAgent application, enabling secure user login via corporate Identity Providers with JWT session management.

## Features

- ✅ OIDC authorization code flow
- ✅ JWT access and refresh tokens
- ✅ User creation/update on first login
- ✅ Token validation middleware
- ✅ Configurable token expiration
- ✅ Structured JSON logging

## Quick Start

bash
# Install dependencies
pip install -r runs/kit/REQ-002/requirements.txt

# Set environment variables
export OIDC_ISSUER_URL="https://your-idp.com"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export JWT_SECRET_KEY="your-secret-key"

# Run tests
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v

# Start server
PYTHONPATH=runs/kit/REQ-002/src uvicorn app.main:app --reload

## API Reference

### GET /api/auth/login

Initiates OIDC login flow.

**Response:**
json
{
  "authorization_url": "https://idp.com/authorize?...",
  "state": "random-state-string"
}

### GET /api/auth/callback

Handles OIDC callback.

**Query Parameters:**
- `code`: Authorization code from IdP
- `state`: State parameter for CSRF protection

**Response:**
json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "role": "viewer"
  },
  "tokens": {
    "access_token": "jwt-token",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "refresh-token"
  }
}

### POST /api/auth/refresh

Refreshes access token.

**Request Body:**
json
{
  "refresh_token": "refresh-token"
}

### GET /api/auth/me

Returns current user profile. Requires authentication.

### POST /api/auth/logout

Logs out current user. Requires authentication.

## File Structure

runs/kit/REQ-002/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── main.py
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── jwt.py
│       │   ├── middleware.py
│       │   ├── models.py
│       │   ├── oidc.py
│       │   ├── repository.py
│       │   ├── router.py
│       │   ├── schemas.py
│       │   └── service.py
│       └── shared/
│           ├── __init__.py
│           ├── database.py
│           ├── exceptions.py
│           └── logging.py
├── test/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth_router.py
│   ├── test_jwt.py
│   ├── test_middleware.py
│   └── test_repository.py
├── ci/
│   ├── LTC.json
│   └── HOWTO.md
├── docs/
│   ├── KIT_REQ-002.md
│   └── README_REQ-002.md
└── requirements.txt

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-002**: OIDC authentication integration

### Rationale
REQ-002 is marked as `in_progress` in the plan and has no blocking dependencies (REQ-001 provides the database schema which is already implemented). This REQ establishes the authentication foundation required by REQ-003 (RBAC) and all subsequent REQs that need user context.

### In Scope
- OIDC authorization code flow with configurable IdP endpoints
- JWT token creation, validation, and refresh
- User model and repository for database operations
- Authentication middleware for FastAPI
- Auth API endpoints (login, callback, refresh, me, logout)
- Structured JSON logging
- Comprehensive test coverage

### Out of Scope
- RBAC authorization (REQ-003)
- Redis-based state storage (using in-memory for slice-1)
- Token blacklisting for logout
- Multi-factor authentication

### How to Run Tests

bash
# Install dependencies
pip install -r runs/kit/REQ-002/requirements.txt

# Run tests with coverage
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v --cov=app --cov-report=term-missing

# Run linting
ruff check runs/kit/REQ-002/src runs/kit/REQ-002/test

# Run type checking
PYTHONPATH=runs/kit/REQ-002/src mypy runs/kit/REQ-002/src --ignore-missing-imports

### Prerequisites
- Python 3.12+
- pip for dependency management
- PostgreSQL 15+ (production) or SQLite (testing)
- OIDC-compatible Identity Provider

### Dependencies and Mocks
- **Database**: Uses SQLite in-memory for tests via `aiosqlite`
- **OIDC Client**: Real implementation but not tested against live IdP (would require integration tests)
- **JWT**: Real implementation with test secret key

### Product Owner Notes
- State storage uses in-memory dict for simplicity; should migrate to Redis for production scalability
- Token blacklisting not implemented; logout only clears cookies
- Default role for new users is `viewer` as per SPEC

### RAG Citations
- Used REQ-001 migration files for User model schema alignment
- Referenced PLAN.md for module structure (`app.auth`)
- Referenced TECH_CONSTRAINTS.yaml for FastAPI framework and Python 3.12 requirement

json
{
  "index": [
    {
      "req": "REQ-002",
      "src": [
        "runs/kit/REQ-002/src/app/__init__.py",
        "runs/kit/REQ-002/src/app/config.py",
        "runs/kit/REQ-002/src/app/main.py",
        "runs/kit/REQ-002/src/app/auth/__init__.py",
        "runs/kit/REQ-002/src/app/auth/models.py",
        "runs/kit/REQ-002/src/app/auth/schemas.py",
        "runs/kit/REQ-002/src/app/auth/oidc.py",
        "runs/kit/REQ-002/src/app/auth/jwt.py",
        "runs/kit/REQ-002/src/app/auth/repository.py",
        "runs/kit/REQ-002/src/app/auth/service.py",
        "runs/kit/REQ-002/src/app/auth/middleware.py",
        "runs/kit/REQ-002/src/app/auth/router.py",
        "runs/kit/REQ-002/src/app/shared/__init__.py",
        "runs/kit/REQ-002/src/app/shared/database.py",
        "runs/kit/REQ-002/src/app/shared/exceptions.py",
        "runs/kit/REQ-002/src/app/shared/logging.py"
      ],
      "tests": [
        "runs/kit/REQ-002/test/__init__.py",
        "runs/kit/REQ-002/test/conftest.py",
        "runs/kit/REQ-002/test/test_jwt.py",
        "runs/kit/REQ-002/test/test_repository.py",
        "runs/kit/REQ-002/test/test_auth_router.py",
        "runs/kit/REQ-002/test/test_middleware.py"
      ]
    }
  ]
}