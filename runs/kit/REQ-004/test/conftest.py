from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# KIT import-path / module-resolution fix
#
# In the KIT layout, pytest loads higher-level conftest.py first (e.g. REQ-002),
# which may import `app.main` and cache it in `sys.modules` BEFORE REQ-004 tests
# are imported. That makes REQ-004 API tests accidentally use the wrong FastAPI
# app (missing `/api/campaigns`), resulting in 404s.
#
# This conftest forces `from app.main import app` to resolve to REQ-004/src/app/main.py
# while still allowing imports from REQ-002/src for shared/auth code.
# ---------------------------------------------------------------------------

REQ4_ROOT = Path(__file__).resolve().parents[1]
REQ4_SRC = REQ4_ROOT / "src"

REQ2_ROOT = REQ4_ROOT.parent / "REQ-002"
REQ2_SRC = REQ2_ROOT / "src"

# sys.path: REQ-004 first; keep REQ-002 available as fallback.
if str(REQ4_SRC) not in sys.path:
    sys.path.insert(0, str(REQ4_SRC))
if REQ2_SRC.exists() and str(REQ2_SRC) not in sys.path:
    sys.path.insert(1, str(REQ2_SRC))

# If `app` was already imported from another REQ (common), ensure REQ-004 is
# first in the package search path and evict cached submodules.
try:
    app_pkg = importlib.import_module("app")
    req4_app_dir = str(REQ4_SRC / "app")

    if hasattr(app_pkg, "__path__"):
        # Put REQ-004/src/app first (avoid duplicates).
        try:
            while req4_app_dir in app_pkg.__path__:
                app_pkg.__path__.remove(req4_app_dir)
        except Exception:
            pass
        try:
            app_pkg.__path__.insert(0, req4_app_dir)
        except Exception:
            pass

    for name in list(sys.modules.keys()):
        if name == "app.main" or name.startswith("app.campaigns"):
            sys.modules.pop(name, None)

    # Preload app.main so test modules import the right FastAPI app instance.
    importlib.import_module("app.main")
except Exception:
    # If this fails, tests will surface it (typically via 404s).
    pass


# ---------------------------------------------------------------------------
# DB dependency override (avoid real DB connections in API tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session() -> AsyncMock:
    return AsyncMock(name="db_session")


@pytest.fixture(autouse=True)
def override_db_dependency(db_session: AsyncMock):
    """Override the DB session dependency used by the campaigns router."""
    try:
        from app.main import app  # import inside fixture
        from app.shared.database import get_db_session

        async def _override_get_db_session() -> AsyncMock:
            return db_session

        app.dependency_overrides[get_db_session] = _override_get_db_session
        yield
        app.dependency_overrides.pop(get_db_session, None)
    except Exception:
        # If the project structure differs, the tests will show it.
        yield
