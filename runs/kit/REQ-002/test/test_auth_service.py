"""Tests for authentication service."""
import uuid
from datetime import datetime, timezone
from unittest import mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config import AuthConfig
from app.auth.models import TokenPayload, UserInfo
from app.auth.service import AuthService
from app.shared.models.enums import UserRole
from app.shared.models.user import User

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
        algorithm="RS256",
        scopes=["openid", "profile", "email"]
    )

class TestAuthService:
    """Tests for AuthService."""
    
    def test_generate_state(self, auth_config):
        """Test state generation."""
        service = AuthService.create(auth_config)
        
        state1 = service.generate_state()
        state2 = service.generate_state()
        
        # States should be unique
        assert state1 != state2
        # States should be URL-safe
        assert all(c.isalnum() or c in "-_" for c in state1)
    
    def test_get_authorization_url(self, auth_config):
        """Test authorization URL generation."""
        service = AuthService.create(auth_config)
        
        url = service.get_authorization_url("test-state")
        
        assert "https://idp.example.com/authorize" in url
        assert "client_id=test-client" in url
        assert "state=test-state" in url
        assert "response_type=code" in url
    
    def test_get_authorization_url_with_custom_redirect(self, auth_config):
        """Test authorization URL with custom redirect."""
        service = AuthService.create(auth_config)
        
        url = service.get_authorization_url(
            "test-state",
            redirect_uri="http://custom.example.com/callback"
        )
        
        assert "redirect_uri=http%3A%2F%2Fcustom.example.com%2Fcallback" in url