"""Tests for authentication API routes."""
from datetime import datetime, timedelta, timezone
from unittest import mock
import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.config import AuthConfig
from app.auth.models import LoginResponse, TokenResponse, UserProfileResponse
from app.auth.router import router as auth_router
from app.shared.models.enums import UserRole

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
        redirect_uri="http://localhost:8000/api/auth/callback",
        post_logout_redirect_uri="http://localhost:8000",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
        algorithm="RS256",
        scopes=["openid", "profile", "email"]
    )

@pytest.fixture
def app(auth_config):
    """Create FastAPI app with auth router."""
    app = FastAPI()
    app.include_router(auth_router)
    
    # Override dependencies
    from app.auth.dependencies import get_auth_config
    app.dependency_overrides[get_auth_config] = lambda: auth_config
    
    return app

class TestAuthRouter:
    """Tests for auth router endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_redirects_to_provider(self, app, auth_config):
        """Test that login redirects to OIDC provider."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False
        ) as client:
            response = await client.get("/api/auth/login")
            
            assert response.status_code == 302
            location = response.headers["location"]
            assert "https://idp.example.com/authorize" in location
            assert "client_id=test-client" in location
    
    @pytest.mark.asyncio
    async def test_login_not_configured(self, app):
        """Test login when OIDC not configured."""
        # Override with unconfigured config
        from app.auth.dependencies import get_auth_config
        app.dependency_overrides[get_auth_config] = lambda: AuthConfig(
            issuer_url="",
            authorization_endpoint="",
            token_endpoint="",
            userinfo_endpoint="",
            jwks_uri="",
            client_id="",
            client_secret="",
            redirect_uri="",
            post_logout_redirect_uri="",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
            algorithm="RS256",
            scopes=[]
        )
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/login")
            
            assert response.status_code == 503
    
    @pytest.mark.asyncio
    async def test_callback_with_error(self, app):
        """Test callback with error from provider."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/auth/callback",
                params={
                    "code": "test-code",
                    "state": "test-state",
                    "error": "access_denied",
                    "error_description": "User denied access"
                }
            )
            
            assert response.status_code == 400
            assert "User denied access" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_callback_with_invalid_state(self, app):
        """Test callback with invalid state."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/auth/callback",
                params={
                    "code": "test-code",
                    "state": "invalid-state"
                }
            )
            
            assert response.status_code == 400
            assert "Invalid state" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint(self, app):
        """Test refresh token endpoint."""
        # Mock the auth service
        from app.auth.dependencies import get_auth_service
        
        mock_service = mock.AsyncMock()
        mock_service.refresh_tokens.return_value = (
            "new-access-token",
            "new-refresh-token"
        )
        
        app.dependency_overrides[get_auth_service] = lambda: mock_service
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/refresh",
                json={"refresh_token": "old-refresh-token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new-access-token"
            assert data["refresh_token"] == "new-refresh-token"