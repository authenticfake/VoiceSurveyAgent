# HOWTO — REQ-002 Execution

## Prerequisites
- Python 3.12
- `uv` or `pip` for dependency installation
- SQLite (bundled with Python) or external Postgres reachable via `VSA_DATABASE_URL`
- Optional: `ruff`, `mypy`, `bandit` CLI binaries (installed via requirements)

## Environment Setup
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r runs/kit/REQ-002/requirements.txt
export PYTHONPATH="runs/kit/REQ-002/src"
export VSA_DATABASE_URL="sqlite+pysqlite:///./runs/kit/REQ-002/.local.db"
```

To use Postgres:
```bash
export VSA_DATABASE_URL="postgresql+psycopg://user:pass@host:5432/voicesurveyagent"
```

## Running Services
```bash
uvicorn app.main:app --reload --app-dir runs/kit/REQ-002/src
```

## Quality Gates
```
ruff check runs/kit/REQ-002/src
mypy runs/kit/REQ-002/src
bandit -q -r runs/kit/REQ-002/src
python -m compileall runs/kit/REQ-002/src
pytest -q runs/kit/REQ-002/test
```

## Enterprise Runner Notes
- Jenkins/GitHub runner should `pip install -r runs/kit/REQ-002/requirements.txt`.
- Set `PYTHONPATH` and `VSA_DATABASE_URL` env vars before invoking commands.
- Artifacts like JUnit output should be written under `runs/kit/REQ-002/reports/`.

## Troubleshooting
- **Missing auth context:** Replace `get_current_user` dependency override with REQ-001 implementation; tests override it automatically.
- **SQLite thread errors:** Ensure `check_same_thread=False` when crafting custom engines (tests already do).
- **Import errors:** Confirm `PYTHONPATH` points to `runs/kit/REQ-002/src`.
- **Database schema drift:** For now, tables auto-create via `Base.metadata.create_all` during tests; future migrations from REQ-009 will supersede this.

KIT Iteration Log
- Targeted REQ-IDs: REQ-002 (campaign CRUD & activation) per plan sequencing.
- In scope: Campaign domain models, SQLAlchemy repository, FastAPI router, RBAC hooks, activation logic, HTTP tests, docs, LTC/HOWTO.
- Out of scope: OIDC auth (REQ-001), contact ingestion/stats (REQ-003), comprehensive migrations (REQ-009).
- How to run tests: `pip install -r runs/kit/REQ-002/requirements.txt && pytest -q runs/kit/REQ-002/test`.
- Prerequisites: Python 3.12, SQLite or configured DATABASE_URL, ability to install listed Python deps.
- Dependencies and mocks: FastAPI `get_current_user` and contact stats provider overridden in tests to isolate REQ-002 behavior.
- Product Owner Notes: Activation currently depends on injected stats provider; wire concrete implementation once contacts module lands.
- RAG citations: SPEC.md, PLAN.md, plan.json, TECH_CONSTRAINTS.yaml.