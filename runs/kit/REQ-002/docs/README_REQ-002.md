# REQ-002 — OIDC Authentication Integration

## Overview
This kit delivers the authentication foundation for the Voice Survey Agent backend:

- Configurable OIDC authorization-code flow.
- Secure token issuance (access + refresh) with customizable TTLs.
- User persistence aligned with the core schema (REQ-001).
- FastAPI endpoints for login redirect, callback, refresh, and `GET /api/auth/me`.
- Middleware/dependency helpers enforcing JWT validation on protected APIs.

## Project Layout
```
runs/kit/REQ-002/
├── src/app
│   ├── auth/        # OIDC client, repository, token service, router
│   ├── shared/      # SQLAlchemy base + user model
│   ├── config.py    # Environment-backed settings
│   └── main.py      # FastAPI app wiring + protected sample endpoint
├── test/            # pytest suite
├── ci/              # LTC + HOWTO
└── docs/            # This README + KIT summary
```

## Usage
1. Export required env vars (see HOWTO).
2. Install deps: `pip install -r runs/kit/REQ-002/src/requirements.txt`.
3. Run API locally: `uvicorn app.main:app --reload --port 8080`.
4. Execute tests: `pytest -q runs/kit/REQ-002/test`.

## Endpoints
- `GET /api/auth/login?redirect_uri=...` → authorization URL + state.
- `POST /api/auth/callback` (`{"code": "...", "redirect_uri": "..."}`) → session tokens + user profile.
- `POST /api/auth/refresh` (`{"refresh_token": "..."}`) → new token pair.
- `GET /api/auth/me` → current user profile (requires Bearer token).
- `GET /api/protected` → sample protected resource.

## Extensibility
- Token + OIDC clients injected via FastAPI dependencies for future mocking/adapter swaps.
- User repository encapsulates persistence for easy customization.
- `get_current_user` dependency will be reused by RBAC (REQ-003) and downstream services.