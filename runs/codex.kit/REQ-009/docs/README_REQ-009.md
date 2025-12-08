# REQ-009 — Database Schema & Migrations

This package delivers the canonical Postgres schema, ORM models, migrations, and supporting tooling for the voicesurveyagent platform.

## Contents

- `src/storage/schema/spec.yaml` — single source of truth for entities, enums, and constraints.
- `src/storage/sql/V0001.*.sql` — generated DDL for upgrade/downgrade.
- `src/storage/seed/seed.sql` — idempotent reference data (10 statements).
- `src/app/infra/db` — SQLAlchemy models, metadata, and session helpers.
- `scripts/db_upgrade.sh` / `scripts/db_downgrade.sh` — shell runners that also maintain the `schema_migrations` ledger.
- `test/` — shape tests for models and Postgres migrations.

## Quick Start

```bash
# install deps
pip install -r runs/kit/REQ-009/requirements.txt

# run migrations
DATABASE_URL=postgresql://user:pass@localhost:5432/voicesurveyagent \
  bash runs/kit/REQ-009/scripts/db_upgrade.sh

# seed reference data
psql "$DATABASE_URL" -f runs/kit/REQ-009/src/storage/seed/seed.sql

# run tests (spins up Postgres via testcontainers if no TEST_DATABASE_URL is set)
pytest -q runs/kit/REQ-009/test
```

## Notes

- All migrations are idempotent via `IF NOT EXISTS` and conditional enum creation.
- Ledger entries are updated automatically with SHA-256 checksums to guarantee deterministic diffs.
- Tests prefer Testcontainers; set `TEST_DATABASE_URL` to reuse an existing Postgres instance when Docker is unavailable.