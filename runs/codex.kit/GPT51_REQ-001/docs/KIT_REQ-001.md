# KIT Log — REQ-001 OIDC auth and RBAC

## Scope

- Implement foundational auth modules:
  - OIDC integration for auth-code flow (login URL + callback).
  - ID token validation via JWKS.
  - User domain model and role mapping.
  - RBAC dependencies for FastAPI routers.
- Provide tests, minimal app wiring, and configuration loader.

## Design Notes

- **Domain-first**:
  - `app.auth.domain` defines `UserRole`, `User`, and `UserRepository` protocol.
  - Role mapping is encapsulated in `map_roles_from_claims`, allowing reuse across REQs.
- **OIDC integration**:
  - `OIDCAuthenticator` in `app.auth.oidc` handles:
    - Building authorization URL.
    - Exchanging authorization code for tokens.
    - Validating ID token with JWKS (using `python-jose`).
    - Upserting/fetching user records via injected `UserRepository`.
  - OIDC configuration is centralized in `app.infra.config.Settings`, loaded from environment.
- **RBAC**:
  - `app.api.http.auth.dependencies` exposes:
    - `get_current_user` dependency for authentication using bearer ID tokens.
    - `require_roles(*roles)` factory to protect routes.
    - Aliases `AdminUser` and `ManagerOrAdminUser` for common policy patterns.
- **HTTP API**:
  - `app.api.http.auth.routes` exposes:
    - `GET /api/auth/login-url` to generate IdP authorize URL.
    - `GET /api/auth/callback` to complete auth-code flow, upsert user, and return ID token + user info.
    - `GET /api/auth/me` to retrieve the current user profile.

## Security & Compliance

- ID tokens are validated for:
  - Signature (JWKS, algorithm).
  - Issuer (`oidc_issuer`).
  - Audience (`oidc_audience` or `oidc_client_id`).
- RBAC is enforced via explicit role checks and returns HTTP 403 with structured error bodies.

## Extensibility

- `UserRepository` is a protocol; DB-backed implementation will be provided by REQ-009.
- `Settings` in `app.infra.config` is designed to be extended with additional configuration in later REQs.
- Other routers (campaigns, contacts, admin, reporting) can depend on:
  - `CurrentUser` for authenticated context.
  - `require_roles(...)` for role-based guards.

## Testing

- Unit tests:
  - `test_role_mapping.py` verifies role mapping logic from claims.
  - `test_rbac_dependencies.py` checks `require_roles` behavior.
- Integration tests:
  - `test_auth_flow_api.py` exercises:
    - `/api/auth/login-url`
    - `/api/auth/callback`
    - `/api/auth/me`
  - Uses an in-memory `UserRepository` and a dummy HTTPX client, injected via FastAPI dependency overrides.

## Assumptions

- Corporate IdP exposes standard OIDC endpoints and JWKS.
- Frontend will initiate login by calling `/api/auth/login-url` and then handling redirects to `/api/auth/callback`.
- For slice‑1, backend uses the IdP-issued ID token as the bearer token for its own APIs.