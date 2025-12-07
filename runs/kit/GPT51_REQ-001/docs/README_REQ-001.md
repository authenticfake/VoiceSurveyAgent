# REQ-001 — OIDC auth and RBAC for backend APIs

This REQ implements foundational authentication and authorization for the `voicesurveyagent` backend.

## Modules

- `app.auth.domain`
  - `UserRole` — enum for `admin`, `campaign_manager`, `viewer`.
  - `User` — domain model for authenticated users.
  - `UserRepository` — protocol for persistence (to be implemented in infra).
  - `map_roles_from_claims` — maps IdP claims/groups to a `UserRole`.
- `app.auth.oidc`
  - `OIDCConfig` — OIDC settings.
  - `OIDCAuthenticator` — builds authorize URL, exchanges code for tokens, validates ID tokens, and upserts users.
- `app.api.http.auth.dependencies`
  - `AuthenticatedUser` — Pydantic model for route context.
  - `get_current_user` — FastAPI dependency; authenticates bearer tokens.
  - `require_roles(*roles)` — RBAC guard for routes.
  - `AdminUser`, `ManagerOrAdminUser` — common role aliases.
- `app.api.http.auth.routes`
  - `GET /api/auth/login-url` — returns IdP authorization URL + state echo.
  - `GET /api/auth/callback` — completes auth-code flow and returns `{ token, user }`.
  - `GET /api/auth/me` — returns the authenticated user.
- `app.infra.config`
  - `Settings` — loads OIDC-related configuration from environment.
- `app.main`
  - `create_app()` — application factory that wires the auth router.
  - `app` — FastAPI instance.

## Configuration

Set the following environment variables (or use a `.env` file):

- `OIDC_ISSUER`
- `OIDC_CLIENT_ID`
- `OIDC_CLIENT_SECRET`
- `OIDC_AUTH_ENDPOINT`
- `OIDC_TOKEN_ENDPOINT`
- `OIDC_JWKS_URI`
- `OIDC_REDIRECT_URI`
- `OIDC_AUDIENCE` (optional)
- `OIDC_SCOPE` (optional, default `openid profile email`)

## Usage

- Protect a route with authentication only:

  ```python
  from fastapi import APIRouter
  from app.api.http.auth.dependencies import CurrentUser

  router = APIRouter()

  @router.get("/whoami")
  async def whoami(user: CurrentUser):
      return {"email": user.email, "role": user.role.value}
  ```

- Protect a route with RBAC:

  ```python
  from app.api.http.auth.dependencies import AdminUser

  @router.post("/admin/task")
  async def admin_only_task(user: AdminUser):
      ...
  ```

Other REQs (campaigns, contacts, admin, reporting) should import these dependencies rather than re-implementing auth or RBAC.

## Tests

Run tests for this REQ:

```bash
pytest -p no:cacheprovider -q runs/kit/REQ-001/test