# KIT — REQ-001 (OIDC auth and RBAC)

## Scope

Implements the authentication slice defined in SPEC/PLAN:
- OIDC authorization-code callback flow with ID token validation via JWKS.
- User persistence after OIDC login (SQLAlchemy model + repository).
- Application-issued JWT used for backend RBAC.
- FastAPI router exposing `/api/auth/login`, `/api/auth/callback`, `/api/auth/me`, plus role-protected probes.
- RBAC dependency ensuring viewer/campaign_manager/admin access policies.

## Architecture Notes

- `app.infra.config` centralizes env-driven settings (OIDC endpoints, DB URL, JWT secret).
- `app.infra.db` provides async SQLAlchemy engine/session factory and metadata init.
- `app.auth.domain` contains role enum, domain models, ORM entity, and repository.
- `app.auth.oidc` handles provider integration (token exchange + JWKS cache).
- `app.auth.service` orchestrates login, persists/updates users, and issues app JWT.
- `app.auth.rbac` exposes FastAPI dependencies for current user resolution and role enforcement.
- `app.api.http.auth.router` wires HTTP endpoints.

Composition-first seams:
- Repository protocol allows swapping persistence implementation once REQ-009 formalizes migrations.
- `AppTokenEncoder` isolates JWT issuance for reuse by future routers/workers.
- JWKS cache is self-contained for reuse by future modules needing identity verification.

## Testing

Pytest suite (`test/auth/test_auth_flow.py`) covers:
- Happy-path OIDC callback with mocked token + JWKS endpoints, verifying `app_access_token` and `/api/auth/me`.
- RBAC enforcement blocking viewer-level token from manager route.

Respx mocks external HTTP calls. Tests use httpx `ASGITransport` per constraint and SQLite (aiosqlite) for persistence.

## Configuration

Environment variables (see `settings.py`) drive endpoints/secrets. Defaults support local dev but **must** be overridden in real deployments.

Key vars:
- `DATABASE_URL`
- `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_AUTHORIZATION_URL`, `OIDC_TOKEN_URL`, `OIDC_JWKS_URL`, `OIDC_ISSUER`
- `APP_JWT_SECRET`, `APP_JWT_ALGORITHM`, `APP_JWT_EXPIRES_SECONDS`

## Next Steps

- REQ-009 will formalize migrations/enums referencing `users` table.
- Downstream REQs should reuse `get_current_user`/`require_roles`.
- Add session storage/state nonce validation once frontend integration arrives (future REQ).