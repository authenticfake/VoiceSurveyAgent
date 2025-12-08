# KIT — REQ-011 (Web console for campaigns and monitoring)

## Scope
Implements the frontend console per SPEC/PLAN slice‑1:
- Campaign listing, creation, editing flows with validation and RBAC guards.
- CSV upload entry point, dashboard metrics, contact table, and export button.
- API client abstractions aligned with backend REST surface.
- Role-awareness via user context fetched from `/api/auth/me`.
- Tests (Vitest + RTL) covering form validation, RBAC guard, and export button.

## Design Highlights
- **Composition-first:** shared `ApiClient`, `forms/campaign` validation helpers, and RBAC utilities reused across components/pages.
- **RBAC:** `UserProvider` hydrates context once; `RbacGuard` enforces allowed roles inline with backend expectations.
- **Extensibility:** Pages rely on declarative components (`CampaignForm`, `DashboardStats`, etc.) to simplify future expansion (e.g., pagination controls, charts).
- **Config:** API base URL injected via `NEXT_PUBLIC_API_BASE_URL`.
- **Styling:** Tailwind utility classes keep UI light-weight yet consistent.

## Testing
- Vitest suite with jsdom environment (see `package.json` / `vitest.config.ts`).
- Coverage artifacts emitted to `test/web/coverage`.

Refer to `docs/README_REQ-011.md` for developer onboarding and `ci/HOWTO.md` for CI/CD execution steps.