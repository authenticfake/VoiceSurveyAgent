import os
from typing import AsyncGenerator, Callable

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, MockTransport
from sqlalchemy.orm import Session

from app.config import get_settings
from app.main import create_app
from app.shared.database import get_session, session_factory


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("OIDC_ISSUER", "http://mock-idp")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-123")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "secret-abc")
    monkeypatch.setenv("OIDC_AUTHORIZATION_ENDPOINT", "http://mock-idp/authorize")
    monkeypatch.setenv("OIDC_TOKEN_ENDPOINT", "http://mock-idp/token")
    monkeypatch.setenv("OIDC_USERINFO_ENDPOINT", "http://mock-idp/userinfo")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("AUTH_TOKEN_SECRET", "supersecuresecretkeyvalue123456789")
    monkeypatch.setenv("ACCESS_TOKEN_TTL_SECONDS", "120")
    monkeypatch.setenv("REFRESH_TOKEN_TTL_SECONDS", "3600")


@pytest.fixture
def app(env_setup) -> FastAPI:
    return create_app()


@pytest.fixture
def mock_oidc_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(
                200,
                json={
                    "access_token": "provider-access",
                    "refresh_token": "provider-refresh",
                    "id_token": "id-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        if request.url.path.endswith("/userinfo"):
            return httpx.Response(
                200,
                json={
                    "sub": "oidc-sub-123",
                    "email": "agent@example.com",
                    "name": "Agent Smith",
                    "role": "campaign_manager",
                },
            )
        raise AssertionError(f"Unhandled path {request.url}")

    return MockTransport(handler)


@pytest.fixture
async def client(app: FastAPI, mock_oidc_transport: MockTransport):
    from app.auth.dependencies import get_oidc_client
    from app.config import get_settings
    from app.auth.oidc_client import OIDCClient

    def override_oidc():
        settings = get_settings()
        return OIDCClient(
            settings.oidc,
            http_client_factory=lambda: httpx.AsyncClient(transport=mock_oidc_transport),
        )

    app.dependency_overrides[get_oidc_client] = override_oidc

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as async_client:
        yield async_client

    app.dependency_overrides.pop(get_oidc_client, None)


@pytest.fixture
def db_session() -> Session:
    factory = session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()