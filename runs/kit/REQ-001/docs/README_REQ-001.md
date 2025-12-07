# REQ-001 — Auth & RBAC Implementation

## Key Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/auth/login` | Returns authorization URL, state, and nonce for browser redirect |
| POST   | `/api/auth/callback` | Exchanges OIDC code, validates ID token, persists user, issues app JWT |
| GET    | `/api/auth/me` | Returns current authenticated user profile (viewer+ roles) |
| GET    | `/api/auth/manager/ping` | Example endpoint requiring `campaign_manager` or `admin` |
| GET    | `/api/auth/admin/ping` | Example endpoint requiring `admin` |

## Usage
1. Call `/api/auth/login?redirect_uri=https://app/callback` to build redirect link.
2. After user authenticates and IdP calls back with `code`, POST to `/api/auth/callback`.
3. Store `app_access_token` returned by callback; supply as `Authorization: Bearer <token>` for protected APIs.
4. Use `/api/auth/me` to obtain role/email for UI rendering.

## Components
- `app.auth.domain`: roles, ORM, repository.
- `app.auth.oidc`: HTTP client + JWKS cache.
- `app.auth.service`: orchestration and JWT issuance.
- `app.auth.rbac`: FastAPI dependencies for RBAC enforcement.
- `app.api.http.auth`: HTTP router.

## Running Tests
```
pytest -q runs/kit/REQ-001/test
```

Ensure env vars for OIDC endpoints and secrets are set (or rely on defaults for local).