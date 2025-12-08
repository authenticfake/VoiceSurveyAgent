# REQ-003 — Contact CSV Import & Exclusions

## Scope
Implements CSV ingestion, validation, persistence, and listing of campaign contacts with do-not-call enforcement and stats integration.

## Highlights
- Streaming CSV parser with strict schema validation and deterministic normalization (E.164, email, booleans).
- SQLAlchemy persistence models for contacts and exclusion lists, including indexes for scheduler eligibility queries.
- FastAPI router for uploads and listing with RBAC via existing auth dependencies.
- `SqlContactStatsProvider` plugged into campaign service DI to expose real eligible contact counts.
- Test suite exercises importer logic and HTTP endpoints using httpx + ASGITransport.

## Next Steps
- Extend repository and schemas once REQ-004 introduces scheduler eligibility filters.
- When REQ-009 finalizes migrations, align table DDL with canonical schema (add FK constraints, seeds).
- Integrate additional contact filters (outcomes, search) to support dashboard requirements (REQ-007).