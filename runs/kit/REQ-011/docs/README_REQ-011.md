# REQ-011 — Web console

## Features
- Campaign catalogue with role-aware create/edit links.
- Campaign wizard form validating questions, scripts, retry policy, and windows.
- Dashboard view aggregating stats plus contact table, CSV upload, and export actions.
- Shared API client + form utilities for future slices.

## Running Locally
```bash
cd runs/kit/REQ-011/src/web
npm install
npm run dev
```
Visit http://localhost:3000 (requires backend endpoints + OIDC session for `/api/auth/me`).

## Tests
```bash
cd runs/kit/REQ-011/src/web
npm run test
```

## Lint & Build
```bash
npm run lint
npm run build
```

## Environment
- `NEXT_PUBLIC_API_BASE_URL` — backend REST base (defaults to `http://localhost:8000`).
- Browser session must already hold the OIDC-authenticated cookie for backend.