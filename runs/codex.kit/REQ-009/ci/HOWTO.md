# HOWTO — Execute REQ-009 Artifacts

## Prerequisites

- Python 3.12+
- Docker Desktop (for Testcontainers-driven tests). If Docker is unavailable, provide a running Postgres instance and set `TEST_DATABASE_URL`.
- `psql` CLI on PATH (required by migration scripts).
- Access to a Postgres database URL with sufficient privileges to create extensions, types, tables, and indexes.

## Environment Setup

```bash
cd /path/to/repo
python -m venv .venv
source .venv/bin/activate
pip install -r runs/kit/REQ-009/requirements.txt
export DATABASE_URL="postgresql://user:pass@localhost:5432/voicesurveyagent"
```

(For Windows PowerShell use `.\.venv\Scripts\Activate.ps1`.)

Optional overrides:

- `TEST_DATABASE_URL` — reuse an existing Postgres for tests instead of spinning up Docker.
- `PYTEST_ADDOPTS` — pass extra pytest flags.

## Running Migrations

Upgrade all versions:

```bash
DATABASE_URL=$DATABASE_URL bash runs/kit/REQ-009/scripts/db_upgrade.sh
```

Rollback in reverse order:

```bash
DATABASE_URL=$DATABASE_URL bash runs/kit/REQ-009/scripts/db_downgrade.sh
```

Both scripts maintain `schema_migrations` with deterministic SHA-256 checksums.

## Seeding Reference Data

After migrations:

```bash
psql "$DATABASE_URL" -f runs/kit/REQ-009/src/storage/seed/seed.sql
```

Seeds are idempotent and include 10 statements (admin user, provider config, bilingual templates, DNC entries).

## Tests

```bash
pytest -q runs/kit/REQ-009/test \
  --junitxml runs/kit/REQ-009/reports/junit.xml \
  --cov=app \
  --cov-report=xml:runs/kit/REQ-009/reports/coverage.xml
```

- With Docker available, tests launch a disposable Postgres 16 container.
- Without Docker, set `TEST_DATABASE_URL` to point to an existing database; tests auto-skip when neither option is available.

## Enterprise Runner Notes

- Jenkins/GitHub Actions: install dependencies via `pip install -r runs/kit/REQ-009/requirements.txt`.
- Ensure runners can access Docker daemon or pre-provision `TEST_DATABASE_URL`.
- Artifacts (`reports/junit.xml`, `reports/coverage.xml`) reside under `runs/kit/REQ-009/`.

## Troubleshooting

- `psql: could not connect`: verify network/firewall and that `DATABASE_URL` is reachable.
- `could not start Postgres container`: confirm Docker daemon is running, or set `TEST_DATABASE_URL`.
- Enum/type already exists errors: scripts are idempotent; ensure you are not manually editing installed types.