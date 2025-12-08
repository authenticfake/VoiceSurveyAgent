# REQ-007 — Reporting APIs

## Endpoints
| Method | Path | Description | Roles |
|--------|------|-------------|-------|
| GET | `/api/campaigns/{campaign_id}/stats` | Aggregate contact counts and rates | viewer, campaign_manager, admin |
| GET | `/api/campaigns/{campaign_id}/contacts` | Paginated contact listing with filters | viewer, campaign_manager, admin |
| GET | `/api/campaigns/{campaign_id}/export` | CSV export with outcomes and answers | campaign_manager, admin |

## Dependencies
- `app.reporting.services.ReportingService` — core aggregation logic.
- `app.infra.db.models` — ORM entities from REQ-009.
- `app.auth.dependencies` — authentication & RBAC guards from REQ-001.

## Running Tests
```bash
pytest -q runs/kit/REQ-007/test
```

## Notes
- CSV exports stream rows to avoid memory spikes and include only mandated columns.
- Contact listing supports `state`, `last_outcome`, pagination, and recency sort toggles.
- All endpoints rely on standard DB session dependency to ensure shared transaction controls.