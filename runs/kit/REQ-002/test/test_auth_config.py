"""Tests for authentication configuration."""
import os
from unittest import mock

import pytest

from app.auth.config import AuthConfig

class TestAuthConfig:
    """Tests for AuthConfig."""
    
    def test_from_env_with_defaults(self):
        """Test loading config with default values."""
        with mock.patch.dict(os.environ, {}, clear=True):
            config = AuthConfig.from_env()
            
            assert config.issuer_url == ""
            assert config.client_id == ""
            assert config.algorithm == "RS256"
            assert config.access_token_expire_minutes == 30
            assert config.refresh_token_expire_days == 7
            assert config.scopes == ["openid", "profile", "email"]
    
    def test_from_env_with_values(self):
        """Test loading config from environment variables."""
        env = {
            "OIDC_ISSUER_URL": "https://idp.example.com",
            "OIDC_AUTHORIZATION_ENDPOINT": "https://idp.example.com/authorize",
            "OIDC_TOKEN_ENDPOINT": "https://idp.example.com/token",
            "OIDC_USERINFO_ENDPOINT": "https://idp.example.com/userinfo",
            "OIDC_JWKS_URI": "https://idp.example.com/.well-known/jwks.json",
            "OIDC_CLIENT_ID": "test-client",
            "OIDC_CLIENT_SECRET": "test-secret",
            "OIDC_REDIRECT_URI": "http://localhost:8000/callback",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
            "REFRESH_TOKEN_EXPIRE_DAYS": "14",
            "JWT_ALGORITHM": "RS256",
            "OIDC_SCOPES": "openid profile email custom",
        }
        
        with mock.patch.dict(os.environ, env, clear=True):
            config = AuthConfig.from_env()
            
            assert config.issuer_url == "https://idp.example.com"
            assert config.client_id == "test-client"
            assert config.client_secret == "test-secret"
            assert config.access_token_expire_minutes == 60
            assert config.refresh_token_expire_days == 14
            assert config.scopes == ["openid", "profile", "email", "custom"]
    
    def test_is_configured_false_when_empty(self):
        """Test is_configured returns False when not configured."""
        with mock.patch.dict(os.environ, {}, clear=True):
            config = AuthConfig.from_env()
            assert config.is_configured() is False
    
    def test_is_configured_true_when_set(self):
        """Test is_configured returns True when properly configured."""
        env = {
            "OIDC_ISSUER_URL": "https://idp.example.com",
            "OIDC_CLIENT_ID": "test-client",
            "OIDC_JWKS_URI": "https://idp.example.com/.well-known/jwks.json",
        }
        
        with mock.patch.dict(os.environ, env, clear=True):
            config = AuthConfig.from_env()
            assert config.is_configured() is True