# KIT — REQ-007 (Dashboard stats and CSV export APIs)

## Summary
Implemented campaign reporting services covering stats, contact listings, and CSV exports. The FastAPI router exposes:
- `GET /api/campaigns/{id}/stats`
- `GET /api/campaigns/{id}/contacts`
- `GET /api/campaigns/{id}/export`

A reusable `ReportingService` aggregates counts via SQLAlchemy, enforces pagination/filtering, and streams CSV data.

## Key Decisions
- **Composition-first**: introduced `value_objects` dataclasses consumed by the router schemas to keep domain logic isolated from HTTP concerns.
- **RBAC alignment**: stats/contacts allow viewer access; CSV export restricted to campaign_manager/admin.
- **Streaming CSV**: generator-based writer avoids holding exports in memory and ensures deterministic ordering.

## Testing
`pytest -q runs/kit/REQ-007/test`

Coverage includes stats calculations, list pagination/filtering, CSV content, and 404 handling.

## Follow-ups
- Hook metrics/tracing (OpenTelemetry) once infra helpers (REQ-010) land.
- Extend CSV exports with async job orchestration if campaign sizes exceed current slice needs.