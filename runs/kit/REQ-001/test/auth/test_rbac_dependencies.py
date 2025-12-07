from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.http.auth.dependencies import (
    AuthenticatedUser,
    require_roles,
)
from app.auth.domain import UserRole


def test_require_roles_allows_authorized_user():
    async def fake_dep() -> AuthenticatedUser:
        return AuthenticatedUser(
            id="u1",
            email="u@example.com",
            name="User",
            role=UserRole.ADMIN,
        )

    async def protected_route(
        _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN))
    ):
        return {"ok": True}

    app = FastAPI()
    app.dependency_overrides = {
        # Override get_current_user inside require_roles path
        "app.api.http.auth.dependencies.get_current_user": fake_dep  # type: ignore[assignment]
    }
    # Since dependency_overrides by string is not supported, we instead
    # mount the route with a dependency that directly uses fake_dep.
    app = FastAPI()

    @app.get("/protected")
    async def _route(
        user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN))
    ):
        return {"role": user.role.value}

    # Monkeypatch FastAPI dependency injection by overriding the global
    # get_current_user function.
    from app.api.http import auth as auth_pkg  # type: ignore[import-not-found]
    from app.api.http.auth import dependencies as deps

    original_get_current_user = deps.get_current_user  # type: ignore[assignment]
    deps.get_current_user = fake_dep  # type: ignore[assignment]

    client = TestClient(app)
    try:
        resp = client.get("/protected")
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"
    finally:
        deps.get_current_user = original_get_current_user  # type: ignore[assignment]


def test_require_roles_blocks_unauthorized_user():
    async def fake_dep() -> AuthenticatedUser:
        return AuthenticatedUser(
            id="u2",
            email="viewer@example.com",
            name="Viewer",
            role=UserRole.VIEWER,
        )

    app = FastAPI()

    @app.get("/protected")
    async def _route(
        _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN))
    ):
        return {"ok": True}

    from app.api.http.auth import dependencies as deps

    original_get_current_user = deps.get_current_user  # type: ignore[assignment]
    deps.get_current_user = fake_dep  # type: ignore[assignment]

    client = TestClient(app)
    try:
        resp = client.get("/protected")
        assert resp.status_code == 403
        body = resp.json()
        assert body["detail"]["error"] == "forbidden"
    finally:
        deps.get_current_user = original_get_current_user  # type: ignore[assignment]