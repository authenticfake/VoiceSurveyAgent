# HOWTO — Execute REQ-003 artifacts

## Prerequisites
- Python 3.12
- `pip` or `uv` for dependency installation
- SQLite available for local tests (default)
- Network egress for downloading PyPI packages

## Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r runs/kit/REQ-003/requirements.txt
```

Environment variables:
- `DATABASE_URL` (optional). Defaults to in-memory SQLite for tests. To run against Postgres: `export DATABASE_URL=postgresql+psycopg://user:pass@host/dbname`.

## Running Tests
```bash
pytest -q runs/kit/REQ-003/test
```

## Local API Smoke (optional)
Run FastAPI app (ensure routers mounted):
```bash
uvicorn app.main:app --reload
```

## CI Integration
Use `ci/LTC.json` contract. Runner should:
1. Install deps from `runs/kit/REQ-003/requirements.txt`.
2. Execute `pytest -q runs/kit/REQ-003/test`.

## Troubleshooting
- **Import errors**: ensure `PYTHONPATH` includes repository root or install package editable (`pip install -e .`).
- **SQLite thread issues**: tests rely on in-memory database; when switching to Postgres ensure migrations applied (from REQ-009).
- **Phonenumbers parsing**: if parsing fails for valid local formats, include region prefix per E.164.

Logs default to stdout. Adjust `DATABASE_URL` for reproducible debugging.


KIT Iteration Log
-----------------
- **Targeted REQ-ID(s)**: REQ-003 (next open REQ per plan) — focused on contact CSV ingestion and listing prerequisites for downstream scheduler.
- **In/Out of scope**: Implemented CSV validator, persistence, FastAPI routes, DI wiring, and tests. Deferred FK hardening and extended filters pending REQ-009/REQ-007 alignment.
- **How to run tests**: `pip install -r runs/kit/REQ-003/requirements.txt && pytest -q runs/kit/REQ-003/test`
- **Prerequisites**: Python 3.12+, SQLite (default) or configure `DATABASE_URL`; internet access for PyPI packages.
- **Dependencies and mocks**: Tests use SQLite via SQLAlchemy; FastAPI dependency overrides supply authenticated principal per instructions.
- **Product Owner Notes**: Contact stats provider now returns real eligibility counts for campaign activation. Add richer reporting filters in REQ-007.
- **RAG citations**: Reused auth dependencies, campaign service scaffolding, and module layout derived from PLAN.md and snippets under `/runs/kit/REQ-002/src/app/...`.

```json
{
  "index": [
    {
      "req": "REQ-003",
      "src": [
        "runs/kit/REQ-003/src/app/contacts/*",
        "runs/kit/REQ-003/src/app/api/http/contacts/*",
        "runs/kit/REQ-003/src/app/campaigns/services/dependencies.py",
        "runs/kit/REQ-003/src/app/infra/db/*"
      ],
      "tests": [
        "runs/kit/REQ-003/test/contacts/test_service_csv_import.py",
        "runs/kit/REQ-003/test/api/test_contacts_api.py"
      ]
    }
  ]
}