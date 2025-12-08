# HOWTO — Execute REQ-007 Deliverables

## Prerequisites
- Python 3.12
- Virtual environment activated with `python -m venv .venv && source .venv/bin/activate`
- Dependencies from `runs/kit/REQ-007/requirements.txt` installed via `pip install -r runs/kit/REQ-007/requirements.txt`
- PostgreSQL URL configured via existing app settings for full integration (tests rely on SQLite in-memory)

## Local Execution
1. **Install deps**
   ```bash
   pip install -r runs/kit/REQ-007/requirements.txt
   ```
2. **Run tests**
   ```bash
   pytest -q runs/kit/REQ-007/test
   ```
3. **Run lint/type/security (optional)**
   ```bash
   ruff check runs/kit/REQ-007/src
   mypy runs/kit/REQ-007/src
   bandit -r runs/kit/REQ-007/src
   ```

## CI / Enterprise Runner
- Use Python toolchain with `PYTHONPATH=.`.
- Execute commands defined in `ci/LTC.json`.
- Publish test reports to `runs/kit/REQ-007/reports`.

## Environment Setup
- Ensure `PYTHONPATH` includes repository root.
- For FastAPI integration tests, no external services required thanks to in-memory SQLite fixture.

## Troubleshooting
- **Import errors**: verify `PYTHONPATH=.` so `app.*` modules resolve.
- **SQLite incompatibilities**: install `pysqlite3-binary` if system SQLite lacks required features.
- **RBAC dependency overrides in tests**: confirm FastAPI `dependency_overrides` cleared between runs to avoid bleed-over.