# KIT — REQ-001 Auth Foundations

## Scope
Implements the authentication backbone for `voicesurveyagent`:
- OIDC authorization-code callback that exchanges the code for tokens and validates the ID token signature.
- Role mapping abstractions that normalize IdP claims to internal roles.
- FastAPI dependencies for authenticated user resolution and RBAC guards.
- HTTP router exposing `/api/auth/oidc/callback`, `/api/auth/me`, and `/api/auth/admin/ping`.

## Architecture Notes
- `app.auth.domain` hosts pure domain types (`Role`, `User`, `OIDCProfile`, `TokenSet`, `IDTokenClaims`) and repository interfaces.
- `app.auth.oidc` provides a production-grade `OIDCClient` that uses `httpx` and `python-jose` to execute the OAuth code exchange and JWKS-backed token validation.
- `app.auth.domain.role_mapper` offers a configurable mapper so future REQs can inject custom claim translations without touching auth service logic.
- `app.auth.rbac` exposes `CurrentUserProvider` and `RBACDependencies` which downstream routers can reuse to guard endpoints with `require_roles`.
- `app.api.http.auth.router.build_auth_router` wires the service & RBAC dependencies into FastAPI routes; no global state is created, keeping composition-first principles intact.

## Testing
`pytest` suite covers:
- Successful OIDC callback flow with token exchange (using fakes) and response payload structure.
- Authenticated `/me` endpoint requiring bearer tokens.
- RBAC enforcement for admin-only endpoint.

Run tests via:
```bash
pytest -q runs/kit/REQ-001/test