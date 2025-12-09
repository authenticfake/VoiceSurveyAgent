"""Tests for JWT authentication middleware."""
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.auth.config import AuthConfig
from app.auth.middleware import JWTAuthMiddleware

@pytest.fixture
def auth_config():
    """Create test auth config."""
    return AuthConfig(
        issuer_url="https://idp.example.com",
        authorization_endpoint="https://idp.example.com/authorize",
        token_endpoint="https://idp.example.com/token",
        userinfo_endpoint="https://idp.example.com/userinfo",
        jwks_uri="https://idp.example.com/.well-known/jwks.json",
        client_id="test-client",
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/callback",
        post_logout_redirect_uri="http://localhost:8000",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
        algorithm="HS256",
        scopes=["openid", "profile", "email"]
    )

@pytest.fixture
def app_with_middleware(auth_config):
    """Create FastAPI app with auth middleware."""
    app = FastAPI()
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    @app.get("/api/protected")
    async def protected():
        return {"message": "protected"}
    
    @app.get("/api/auth/login")
    async def login():
        return {"message": "login"}
    
    # Create mock JWT validator
    class MockJWTValidator:
        async def validate_token(self, token):
            from app.auth.models import TokenPayload
            if token == "valid-token":
                now = datetime.now(timezone.utc)
                return TokenPayload(
                    sub="user-123",
                    exp=now + timedelta(hours=1),
                    iat=now,
                    iss="https://idp.example.com",
                    aud="test-client"
                )
            elif token == "expired-token":
                from app.auth.exceptions import ExpiredTokenError
                raise ExpiredTokenError()
            else:
                from app.auth.exceptions import InvalidTokenError
                raise InvalidTokenError("Invalid token")
    
    app.add_middleware(
        JWTAuthMiddleware,
        config=auth_config,
        jwt_validator=MockJWTValidator()
    )
    
    return app

class TestJWTAuthMiddleware:
    """Tests for JWTAuthMiddleware."""
    
    @pytest.mark.asyncio
    async def test_public_path_no_auth_required(self, app_with_middleware):
        """Test that public paths don't require authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test"
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_auth_path_no_auth_required(self, app_with_middleware):
        """Test that auth paths don't require authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/login")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_protected_path_requires_auth(self, app_with_middleware):
        """Test that protected paths require authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/protected")
            assert response.status_code == 401
            assert response.json()["error"] == "missing_token"
    
    @pytest.mark.asyncio
    async def test_protected_path_with_valid_token(self, app_with_middleware):
        """Test that protected paths work with valid token."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/protected",
                headers={"Authorization": "Bearer valid-token"}
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_protected_path_with_expired_token(self, app_with_middleware):
        """Test that expired tokens return 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/protected",
                headers={"Authorization": "Bearer expired-token"}
            )
            assert response.status_code == 401
            assert response.json()["error"] == "token_expired"
    
    @pytest.mark.asyncio
    async def test_protected_path_with_invalid_token(self, app_with_middleware):
        """Test that invalid tokens return 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/protected",
                headers={"Authorization": "Bearer invalid-token"}
            )
            assert response.status_code == 401
            assert response.json()["error"] == "invalid_token"
    
    @pytest.mark.asyncio
    async def test_invalid_auth_header_format(self, app_with_middleware):
        """Test that invalid auth header format returns 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/protected",
                headers={"Authorization": "InvalidFormat token"}
            )
            assert response.status_code == 401
            assert response.json()["error"] == "invalid_header"