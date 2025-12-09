"""Tests for JWT validation."""
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from jose import jwt

from app.auth.config import AuthConfig
from app.auth.exceptions import ExpiredTokenError, InvalidTokenError
from app.auth.jwt_validator import JWTValidator
from app.auth.jwks import JWKSClient

class MockJWKSClient:
    """Mock JWKS client for testing."""
    
    def __init__(self, keys: dict = None):
        self._keys = keys or {}
    
    async def get_signing_key(self, kid: str):
        return self._keys.get(kid)
    
    def clear_cache(self):
        pass

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
        algorithm="HS256",  # Use HS256 for simpler testing
        scopes=["openid", "profile", "email"]
    )

class TestJWTValidator:
    """Tests for JWTValidator."""
    
    @pytest.mark.asyncio
    async def test_validate_valid_token(self, auth_config):
        """Test validating a valid token."""
        # Create a test token
        secret = "test-secret-key-for-testing-purposes"
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user-123",
            "exp": (now + timedelta(hours=1)).timestamp(),
            "iat": now.timestamp(),
            "iss": "https://idp.example.com",
            "aud": "test-client",
            "email": "user@example.com",
            "name": "Test User"
        }
        token = jwt.encode(payload, secret, algorithm="HS256", headers={"kid": "test-key"})
        
        # Create mock JWKS client
        from jose import jwk
        mock_key = jwk.construct(secret, algorithm="HS256")
        jwks_client = MockJWKSClient({"test-key": mock_key})
        
        validator = JWTValidator(auth_config, jwks_client)
        result = await validator.validate_token(token)
        
        assert result.sub == "user-123"
        assert result.email == "user@example.com"
        assert result.name == "Test User"
    
    @pytest.mark.asyncio
    async def test_validate_expired_token(self, auth_config):
        """Test that expired token raises ExpiredTokenError."""
        secret = "test-secret-key-for-testing-purposes"
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user-123",
            "exp": (now - timedelta(hours=1)).timestamp(),  # Expired
            "iat": (now - timedelta(hours=2)).timestamp(),
            "iss": "https://idp.example.com",
            "aud": "test-client"
        }
        token = jwt.encode(payload, secret, algorithm="HS256", headers={"kid": "test-key"})
        
        from jose import jwk
        mock_key = jwk.construct(secret, algorithm="HS256")
        jwks_client = MockJWKSClient({"test-key": mock_key})
        
        validator = JWTValidator(auth_config, jwks_client)
        
        with pytest.raises(ExpiredTokenError):
            await validator.validate_token(token)
    
    @pytest.mark.asyncio
    async def test_validate_token_missing_kid(self, auth_config):
        """Test that token without kid raises InvalidTokenError."""
        secret = "test-secret-key-for-testing-purposes"
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user-123",
            "exp": (now + timedelta(hours=1)).timestamp(),
            "iat": now.timestamp(),
            "iss": "https://idp.example.com",
            "aud": "test-client"
        }
        # Create token without kid in header
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        jwks_client = MockJWKSClient()
        validator = JWTValidator(auth_config, jwks_client)
        
        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate_token(token)
        
        assert "missing key ID" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_token_unknown_key(self, auth_config):
        """Test that token with unknown key raises InvalidTokenError."""
        secret = "test-secret-key-for-testing-purposes"
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user-123",
            "exp": (now + timedelta(hours=1)).timestamp(),
            "iat": now.timestamp(),
            "iss": "https://idp.example.com",
            "aud": "test-client"
        }
        token = jwt.encode(payload, secret, algorithm="HS256", headers={"kid": "unknown-key"})
        
        jwks_client = MockJWKSClient()  # Empty keys
        validator = JWTValidator(auth_config, jwks_client)
        
        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate_token(token)
        
        assert "Unknown signing key" in str(exc_info.value)