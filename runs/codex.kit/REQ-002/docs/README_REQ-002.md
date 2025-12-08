# REQ-002 — Campaign CRUD and Activation

## Modules
- `app/campaigns/domain`: enums, models, commands, validators.
- `app/campaigns/services`: repository interfaces, service orchestrator, FastAPI dependency wiring.
- `app/campaigns/persistence`: SQLAlchemy model + repository.
- `app/api/http/campaigns`: request/response schemas and router.
- `app/infra/config` & `app/infra/db`: minimal settings + session factory shared across REQs.

## Running Locally
```bash
export VSA_DATABASE_URL="sqlite+pysqlite:///./campaigns.db"
uv pip install -r runs/kit/REQ-002/requirements.txt
python -m uvicorn app.main:app --reload --app-dir runs/kit/REQ-002/src
```

## Tests
```bash
uv pip install -r runs/kit/REQ-002/requirements.txt
pytest -q runs/kit/REQ-002/test
```

## Key Behaviors
- Create/update restricted to `admin` or `campaign_manager` roles via `require_roles`.
- Viewer access allowed for fetch/list endpoints.
- Activation enforces: three questions, intro script present, eligible contacts > 0 (via injected stats provider).
- Pagination supports filters by status/date with deterministic metadata.

## Integration Notes
- Replace `get_current_user` in `app/auth/dependencies.py` with the OIDC implementation from REQ-001.
- Wire an actual `ContactStatsProvider` (likely from REQ-003 contact services) in `get_contact_stats_provider`.
- Include this module’s models when REQ-009 produces consolidated Alembic migrations.