from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import httpx
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from jose import jwt

from app.api.http.auth.dependencies import (
    get_oidc_authenticator,
    get_user_repository,
)
from app.api.http.auth.dependencies import CurrentUser
from app.auth.domain import User, UserRepository, UserRole
from app.auth.oidc import OIDCAuthenticator
from app.main import create_app


class InMemoryUserRepo(UserRepository):
    def __init__(self) -> None:
        self._by_sub: Dict[str, User] = {}
        self._seq = 0

    def get_by_oidc_sub(self, oidc_sub: str) -> Optional[User]:
        return self._by_sub.get(oidc_sub)

    def upsert_from_oidc(
        self,
        oidc_sub: str,
        email: str,
        name: str,
        role: UserRole,
    ) -> User:
        existing = self._by_sub.get(oidc_sub)
        if existing:
            existing.email = email
            existing.name = name
            existing.role = role
            return existing
        self._seq += 1
        user = User(
            id=str(self._seq),
            oidc_sub=oidc_sub,
            email=email,
            name=name,
            role=role,
        )
        self._by_sub[oidc_sub] = user
        return user


class DummyAsyncClient(httpx.AsyncClient):
    """AsyncClient that fakes token and JWKS endpoints for tests."""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self._jwks: Dict[str, Dict] = {}

    async def get(self, url: str, *args, **kwargs) -> httpx.Response:  # type: ignore[override]
        if url.endswith("/jwks"):
            return httpx.Response(200, json=self._jwks)
        return await super().get(url, *args, **kwargs)

    async def post(self, url: str, *args, **kwargs) -> httpx.Response:  # type: ignore[override]
        if url.endswith("/token"):
            # Token endpoint: return a minimal response with id_token
            data = kwargs.get("data") or {}
            # generate a simple HS256 token for tests; the authenticator will
            # still call validate_id_token, which we'll patch to bypass real JWKS.
            now = datetime.now(timezone.utc)
            payload = {
                "sub": "sub-123",
                "email": "user@example.com",
                "name": "Test User",
                "role": "campaign_manager",
                "iss": "https://example-issuer",
                "aud": data.get("client_id"),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
            }
            # Use symmetric key just for testing
            secret = "test-secret"
            token = jwt.encode(payload, secret, algorithm="HS256")
            body = {"id_token": token, "access_token": "dummy", "token_type": "Bearer"}
            return httpx.Response(200, json=body)
        return await super().post(url, *args, **kwargs)


@pytest.fixture()
def test_env(monkeypatch):
    # Configure environment for Settings
    monkeypatch.setenv("OIDC_ISSUER", "https://example-issuer")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_AUTH_ENDPOINT", "https://idp.example.com/auth")
    monkeypatch.setenv("OIDC_TOKEN_ENDPOINT", "https://idp.example.com/token")
    monkeypatch.setenv("OIDC_JWKS_URI", "https://idp.example.com/jwks")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "https://app.example.com/callback")


@pytest.fixture()
def app_with_auth(test_env, monkeypatch):
    app = create_app()
    repo = InMemoryUserRepo()
    dummy_client = DummyAsyncClient()

    # Override user repository dependency
    from app.api.http.auth import dependencies as deps

    def _get_user_repo_override() -> UserRepository:
        return repo

    async def _get_oidc_authenticator_override(
        user_repo: UserRepository = Depends(_get_user_repo_override),
    ) -> OIDCAuthenticator:
        return OIDCAuthenticator(user_repository=user_repo, http_client=dummy_client)

    app.dependency_overrides[get_user_repository] = _get_user_repo_override
    app.dependency_overrides[get_oidc_authenticator] = _get_oidc_authenticator_override

    # Patch validate_id_token to use the same symmetric key as DummyAsyncClient
    async def _validate_id_token_override(self, id_token: str):  # type: ignore[no-untyped-def]
        return jwt.decode(id_token, "test-secret", algorithms=["HS256"], audience="client-id", issuer="https://example-issuer")

    monkeypatch.setattr(
        "app.auth.oidc.OIDCAuthenticator.validate_id_token",
        _validate_id_token_override,
        raising=True,
    )

    return app


def test_login_url_endpoint(app_with_auth):
    client = TestClient(app_with_auth)
    resp = client.get("/api/auth/login-url", params={"state": "xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "xyz"
    assert "authorization_url" in body
    assert "response_type=code" in body["authorization_url"]


def test_oidc_callback_and_me_flow(app_with_auth):
    client = TestClient(app_with_auth)

    # Simulate callback from IdP with code
    resp = client.get("/api/auth/callback", params={"code": "abc", "state": "xyz"})
    assert resp.status_code == 200
    payload = resp.json()
    assert "token" in payload
    assert payload["user"]["email"] == "user@example.com"
    assert payload["user"]["role"] == "campaign_manager"

    # Use returned token as Authorization bearer to call /me
    token = payload["token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp_me = client.get("/api/auth/me", headers=headers)
    assert resp_me.status_code == 200
    me = resp_me.json()
    assert me["email"] == "user@example.com"
    assert me["role"] == "campaign_manager"


def test_me_requires_authentication(app_with_auth):
    client = TestClient(app_with_auth)
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["error"] == "not_authenticated"