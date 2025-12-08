# REQ-008 — Admin configuration & retention APIs

## Overview
Adds admin-only APIs to view and update telephony/LLM provider settings, retention windows, and default email templates. Responses also expose read-only email provider metadata derived from environment configuration.

## Modules
- `app.admin.domain` — Pydantic models, enums, and repository helpers.
- `app.admin.services` — Audit logger and `AdminConfigService`.
- `app.api.http.admin.router` — FastAPI endpoints protected by admin RBAC.

## Key Endpoints
- `GET /api/admin/config` — Returns provider config, retention values, email provider metadata, and template summaries.
- `PUT /api/admin/config` — Updates provider config, retention durations, and optional template fields (subject/body/name). Records structured audit logs.

## Testing
```
pytest -q runs/kit/REQ-008/test
```

Ensure `EMAIL_PROVIDER`, `EMAIL_FROM_ADDRESS`, `EMAIL_REPLY_TO`, and `EMAIL_PROVIDER_REGION` env vars are set for realistic email provider metadata (defaults are provided otherwise).