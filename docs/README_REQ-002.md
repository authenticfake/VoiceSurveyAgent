# REQ-002: OIDC Authentication Integration

## Quick Start

```bash
# Install dependencies
pip install -r runs/kit/REQ-002/requirements.txt

# Run tests
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v

# Start development server
cd runs/kit/REQ-002
PYTHONPATH=src uvicorn app.main:app --reload
```

## What This Implements

- **OIDC Login Flow**: Authorization code flow with any OIDC-compliant IdP
- **JWT Session Tokens**: Access tokens (1 hour) and refresh tokens (7 days)
- **User Provisioning**: Automatic user creation on first login
- **Auth Middleware**: Protects API endpoints with token validation
- **Role Support**: Users have roles (admin, campaign_manager, viewer)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | GET | Start OIDC login |
| `/api/auth/callback` | GET | Handle IdP callback |
| `/api/auth/refresh` | POST | Refresh tokens |
| `/api/auth/me` | GET | Get current user |
| `/health` | GET | Health check |

## Configuration

Set these environment variables:

```bash
OIDC_ISSUER_URL=https://your-idp.example.com
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
JWT_SECRET_KEY=your-secret-key
```

## Testing

```bash
# All tests
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v

# With coverage
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test --cov=runs/kit/REQ-002/src
```

## Files

- `src/app/auth/` - Authentication module
- `src/app/shared/` - Shared utilities
- `test/` - Test suite
- `ci/LTC.json` - Test contract
- `ci/HOWTO.md` - Detailed execution guide
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-002**: OIDC authentication integration

### Rationale
REQ-002 depends on REQ-001 (database schema) which is marked as `in_progress`. The schema from REQ-001 defines the `users` table with the required columns (`id`, `oidc_sub`, `email`, `name`, `role`, `created_at`, `updated_at`) and the `user_role` enum type. This implementation builds on that foundation.

### In Scope
- OIDC authorization code flow with configurable IdP endpoints
- JWT token creation and validation (access + refresh tokens)
- User record creation/update on first OIDC login
- Authentication middleware for FastAPI
- Session tokens with configurable expiration
- Login endpoint returning user profile with role
- Proper 401 responses for invalid/expired tokens

### Out of Scope
- RBAC authorization (REQ-003)
- Campaign management (REQ-004+)
- Frontend implementation
- Production OIDC provider integration testing

### How to Run Tests

```bash
# Install dependencies
pip install -r runs/kit/REQ-002/requirements.txt

# Run all tests with coverage
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v \
  --cov=runs/kit/REQ-002/src \
  --cov-report=term-missing

# Run specific test files
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test/test_jwt.py -v
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test/test_service.py -v
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test/test_middleware.py -v
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test/test_router.py -v
```

### Prerequisites
- Python 3.12+
- pip or Poetry
- PostgreSQL (production) or SQLite (testing)
- OIDC Identity Provider (for production use)

### Dependencies and Mocks
- **OIDC Client**: Mocked in tests using `MagicMock` to avoid external IdP calls
- **Database**: Uses SQLite in-memory for tests via `aiosqlite`
- **HTTP Client**: `httpx.AsyncClient` with `ASGITransport` for API tests

### Product Owner Notes
- Default user role is `viewer` on first login; role changes require admin action
- State parameter storage uses in-memory dict for demo; production should use Redis with TTL
- OIDC discovery endpoint support is implemented but uses well-known URL patterns by default
- Token refresh creates entirely new token pair (both access and refresh)

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - Referenced for User table schema and `user_role` enum
- `docs/harper/lane-guides/python.md` - Referenced for FastAPI project structure and testing patterns
- `PLAN.md` - Referenced for module namespace (`app.auth`) and acceptance criteria

```json
{
  "index": [
    {
      "req": "REQ-002",
      "src": [
        "runs/kit/REQ-002/src/app/__init__.py",
        "runs/kit/REQ-002/src/app/config.py",
        "runs/kit/REQ-002/src/app/main.py",
        "runs/kit/REQ-002/src/app/shared/__init__.py",
        "runs/kit/REQ-002/src/app/shared/database.py",
        "runs/kit/REQ-002/src/app/shared/exceptions.py",
        "runs/kit/REQ-002/src/app/shared/logging.py",
        "runs/kit/REQ-002/src/app/auth/__init__.py",
        "runs/kit/REQ-002/src/app/auth/schemas.py",
        "runs/kit/REQ-002/src/app/auth/models.py",
        "runs/kit/REQ-002/src/app/auth/repository.py",
        "runs/kit/REQ-002/src/app/auth/oidc.py",
        "runs/kit/REQ-002/src/app/auth/jwt.py",
        "runs/kit/REQ-002/src/app/auth/service.py",
        "runs/kit/REQ-002/src/app/auth/middleware.py",
        "runs/kit/REQ-002/src/app/auth/router.py"
      ],
      "tests": [
        "runs/kit/REQ-002/test/__init__.py",
        "runs/kit/REQ-002/test/conftest.py",
        "runs/kit/REQ-002/test/test_jwt.py",
        "runs/kit/REQ-002/test/test_repository.py",
        "runs/kit/REQ-002/test/test_service.py",
        "runs/kit/REQ-002/test/test_middleware.py",
        "runs/kit/REQ-002/test/test_router.py"
      ]
    }
  ]
}