# KIT Notes — REQ-002 (Campaign CRUD and Activation)

## Summary
Implemented campaign CRUD APIs, validation logic, and lifecycle controls aligned with SPEC and PLAN requirements. The delivery introduces SQLAlchemy-backed persistence, service-layer validation, FastAPI routers with RBAC hooks, and activation readiness checks that consult a contact stats provider abstraction.

## Scope & Key Decisions
- **Domain fidelity:** Campaign definitions require exactly three questions, validated retry policy bounds, and strict call windows.
- **Persistence:** Added a SQLAlchemy `CampaignModel`, repository, and shared DB session factory. Models use enums for language/status to stay aligned with the future REQ-009 schema.
- **Service layer:** `CampaignService` centralizes lifecycle rules, ensuring only draft/paused campaigns may be edited, enforcing activation preconditions, and providing paginated listings.
- **RBAC integration seam:** Routes depend on `require_roles` and `get_current_user`; the latter intentionally raises until REQ-001 wires OIDC.
- **Contact readiness seam:** Activation relies on a `ContactStatsProvider` protocol. A null provider raises in production paths to prevent accidental activation without REQ-003 wiring. Tests inject a fake implementation.
- **API surface:** Exposed `POST/GET/PUT /api/campaigns`, plus `/activate` and `/pause` actions. Responses normalize question, retry, window, and email template structures for frontend reuse.
- **Configuration:** Added basic settings + DB session helpers (SQLite default) to keep code runnable; future REQs can override via env.

## Validation & Testing
- Pytest suite exercises creation, RBAC enforcement, activation failure/success, and listing filters through HTTP-level tests using `httpx.AsyncClient` + ASGITransport.
- Repository and service logic leveraged in tests via FastAPI dependency overrides with in-memory SQLite.

## Follow-ups / Dependencies
- **REQ-001:** Must provide real OIDC-backed `get_current_user`.
- **REQ-003:** Needs to implement a concrete `ContactStatsProvider` so activation reflects actual contact counts.
- **REQ-009:** Will extend schema/migrations to cover all entities; current model should be merged into the canonical migrations once available.