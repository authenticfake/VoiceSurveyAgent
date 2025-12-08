# KIT Notes — REQ-009 Database Schema

## Overview

REQ-009 establishes the persistence foundation for the entire platform. The work aligns with SPEC §Data Model and PLAN §Module/Package & Namespace Plan, focusing on:

- A canonical schema spec (`src/storage/schema/spec.yaml`) that enumerates all entities, enums, and constraints.
- Versioned SQL migrations (`V0001`) rendered from the spec, plus a migration ledger table for deterministic upgrades/downgrades.
- Idempotent seeds injecting 10 curated reference rows (admin user, provider configuration, bilingual templates, exclusion entries).
- SQLAlchemy models and session helpers under `app.infra.db`, matching the same naming conventions for reuse by downstream REQs.

## Key Design Decisions

- **Single Source of Truth**: The YAML spec drives both the ORM and SQL files, ensuring future automation can regenerate artifacts without divergence.
- **Idempotent SQL**: All types/tables use conditional creation; scripts can run multiple times safely. Ledger updates keep checksums (`sha256:<value>`) for auditability.
- **Naming Convention**: `Base.metadata` enforces deterministic constraint/index names, simplifying Alembic diffs and cross-REQ composition.
- **Enumerations**: Native Postgres enums mirror domain enums, exposed through Python `enum.Enum` classes to avoid duplicated literals.
- **Session Helpers**: `session.py` provides engine + scoped session creation for API processes, workers, and tests, consistent with DIP/composition guidelines.

## Testing & Quality

- `test_models.py` validates table registration and enum coverage against the SPEC.
- `test_migration_sql.py` runs the upgrade twice (idempotency) and the downgrade once using Postgres Testcontainers (or any DB passed via `TEST_DATABASE_URL`), ensuring schema round-trips cleanly.

## Next Steps

- Future migrations should append `V0002...` files rendered from the same spec, updating the ledger and documenting changes in this directory.
- Downstream REQs (campaigns, contacts, calling, events, admin, etc.) should import models from `app.infra.db.models` rather than redefining schemas.