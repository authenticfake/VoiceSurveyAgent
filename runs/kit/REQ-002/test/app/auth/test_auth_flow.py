import asyncio

import httpx
import pytest
from sqlalchemy import select

from app.shared.models.user import User


@pytest.mark.anyio
async def test_login_redirect_returns_authorization_url(client):
    response = await client.get("/api/auth/login", params={"redirect_uri": "http://localhost/cb"})
    data = response.json()
    assert response.status_code == 200
    assert data["authorization_url"].startswith("http://mock-idp/authorize?")
    assert "client_id=client-123" in data["authorization_url"]
    assert data["state"]


@pytest.mark.anyio
async def test_callback_creates_user_and_returns_tokens(client, db_session):
    response = await client.post("/api/auth/callback", json={"code": "abc", "state": "xyz"})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "agent@example.com"
    assert body["user"]["role"] == "campaign_manager"
    assert body["access_token"]
    assert body["refresh_token"]

    user = db_session.scalars(select(User).where(User.oidc_sub == "oidc-sub-123")).one()
    assert user.email == "agent@example.com"


@pytest.mark.anyio
async def test_refresh_issues_new_tokens(client):
    login = await client.post("/api/auth/callback", json={"code": "abc"})
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    refresh_resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    refresh_body = refresh_resp.json()
    assert refresh_body["access_token"] != login.json()["access_token"]


@pytest.mark.anyio
async def test_protected_endpoint_requires_valid_token(client):
    no_token = await client.get("/api/protected")
    assert no_token.status_code == 401

    login = await client.post("/api/auth/callback", json={"code": "abc"})
    token = login.json()["access_token"]
    ok_resp = await client.get("/api/protected", headers={"Authorization": f"Bearer {token}"})
    assert ok_resp.status_code == 200