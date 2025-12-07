import base64
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator
from uuid import UUID

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain.models import Role, UserORM
from app.auth.service import AppTokenEncoder, build_auth_service
from app.infra.config.settings import get_settings, reload_settings
from app.infra.db.session import AsyncSessionFactory, init_db
from app.main import create_app

pytestmark = pytest.mark.asyncio


def _b64(value: int) -> str:
    data = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@pytest.fixture(autouse=True)
def configure_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'auth.db'}")
    monkeypatch.setenv("APP_JWT_SECRET", "test-secret")
    monkeypatch.setenv("OIDC_CLIENT_ID", "cli-test")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "cli-secret")
    monkeypatch.setenv("OIDC_AUTHORIZATION_URL", "https://idp.test/authorize")
    monkeypatch.setenv("OIDC_TOKEN_URL", "https://idp.test/token")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://idp.test/jwks")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.test/")
    monkeypatch.setenv("RBAC_ROLE_PRIORITY", "admin,campaign_manager,viewer")
    reload_settings()


@pytest.fixture
async def app_instance() -> AsyncIterator[FastAPI]:
    await init_db()
    app = create_app()
    yield app


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    numbers = public_key.public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test-key",
        "use": "sig",
        "n": _b64(numbers.n),
        "e": _b64(numbers.e),
        "alg": "RS256",
    }
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return private_pem.decode("utf-8"), jwk


def build_id_token(private_key_pem: str, jwk: dict) -> str:
    settings = get_settings()
    payload = {
        "sub": "subject-123",
        "email": "manager@example.com",
        "name": "Cam Manager",
        "roles": ["campaign_manager"],
        "iss": settings.oidc_issuer,
        "aud": settings.oidc_client_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256", headers={"kid": jwk["kid"]})


async def exchange_and_get_app_token(client: httpx.AsyncClient) -> str:
    response = await client.post(
        "/api/auth/callback",
        json={"code": "abc", "redirect_uri": "https://app.test/cb"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return data["app_access_token"]


@respx.mock
async def test_oidc_callback_and_me_endpoint(app_instance: FastAPI, rsa_keypair):
    private_pem, jwk = rsa_keypair
    id_token = build_id_token(private_pem, jwk)
    respx.post("https://idp.test/token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "provider-access",
                "refresh_token": "provider-refresh",
                "id_token": id_token,
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
    )
    respx.get("https://idp.test/jwks").mock(
        return_value=httpx.Response(200, json={"keys": [jwk]})
    )

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app_instance),
        base_url="http://testserver",
    ) as client:
        app_token = await exchange_and_get_app_token(client)
        me_response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {app_token}"}
        )
        assert me_response.status_code == 200
        body = me_response.json()
        assert body["email"] == "manager@example.com"
        assert body["role"] == Role.CAMPAIGN_MANAGER.value

        manager_ping = await client.get(
            "/api/auth/manager/ping",
            headers={"Authorization": f"Bearer {app_token}"},
        )
        assert manager_ping.status_code == 200


@respx.mock
async def test_rbac_blocks_viewer_on_manager_route(app_instance: FastAPI, rsa_keypair):
    private_pem, jwk = rsa_keypair
    id_token = build_id_token(private_pem, jwk)
    respx.post("https://idp.test/token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "provider-access",
                "refresh_token": "provider-refresh",
                "id_token": id_token,
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
    )
    respx.get("https://idp.test/jwks").mock(
        return_value=httpx.Response(200, json={"keys": [jwk]})
    )

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app_instance),
        base_url="http://testserver",
    ) as client:
        app_token = await exchange_and_get_app_token(client)

    # downgrade user role to viewer to test RBAC
    async with AsyncSessionFactory() as session:
        await _downgrade_user_to_viewer(session)

    viewer_token = _build_viewer_token()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app_instance),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/auth/manager/ping",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "forbidden"


async def _downgrade_user_to_viewer(session: AsyncSession):
    user = (await session.execute(
        UserORM.__table__.select()
    )).first()
    if user:
        await session.execute(
            UserORM.__table__.update().values(role=Role.VIEWER.value)
        )
        await session.commit()


def _build_viewer_token() -> str:
    settings = get_settings()
    repository = SqlAlchemyUserRepository(AsyncSessionFactory())  # type: ignore[arg-type]
    encoder = AppTokenEncoder(settings)
    user = UserProfile(
        id=UUID(int=1),
        oidc_sub="subject-123",
        email="viewer@example.com",
        name="Viewer",
        role=Role.VIEWER,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return encoder.encode(user)