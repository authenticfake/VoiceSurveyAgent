"""Tests for authentication models."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.auth.models import (
    AuthorizationCallback,
    LoginResponse,
    RefreshTokenRequest,
    TokenPayload,
    TokenResponse,
    UserInfo,
    UserProfileResponse,
)
from app.shared.models.enums import UserRole

class TestTokenPayload:
    """Tests for TokenPayload model."""
    
    def test_valid_payload(self):
        """Test creating valid token payload."""
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub="user-123",
            exp=now,
            iat=now,
            iss="https://idp.example.com",
            aud="test-client",
            email="user@example.com",
            name="Test User",
            roles=["admin"]
        )
        
        assert payload.sub == "user-123"
        assert payload.email == "user@example.com"
        assert payload.roles == ["admin"]
    
    def test_payload_with_list_audience(self):
        """Test payload with list audience."""
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub="user-123",
            exp=now,
            iat=now,
            iss="https://idp.example.com",
            aud=["client1", "client2"]
        )
        
        assert payload.aud == ["client1", "client2"]

class TestUserInfo:
    """Tests for UserInfo model."""
    
    def test_minimal_userinfo(self):
        """Test creating UserInfo with minimal fields."""
        info = UserInfo(sub="user-123")
        
        assert info.sub == "user-123"
        assert info.email is None
        assert info.email_verified is False
    
    def test_full_userinfo(self):
        """Test creating UserInfo with all fields."""
        info = UserInfo(
            sub="user-123",
            email="user@example.com",
            email_verified=True,
            name="Test User",
            preferred_username="testuser",
            given_name="Test",
            family_name="User"
        )
        
        assert info.email == "user@example.com"
        assert info.email_verified is True
        assert info.name == "Test User"

class TestTokenResponse:
    """Tests for TokenResponse model."""
    
    def test_minimal_response(self):
        """Test creating minimal token response."""
        response = TokenResponse(
            access_token="access-token-123",
            expires_in=3600
        )
        
        assert response.access_token == "access-token-123"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
        assert response.refresh_token is None
    
    def test_full_response(self):
        """Test creating full token response."""
        response = TokenResponse(
            access_token="access-token-123",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="refresh-token-456",
            id_token="id-token-789",
            scope="openid profile email"
        )
        
        assert response.refresh_token == "refresh-token-456"
        assert response.id_token == "id-token-789"

class TestRefreshTokenRequest:
    """Tests for RefreshTokenRequest model."""
    
    def test_valid_request(self):
        """Test creating valid refresh request."""
        request = RefreshTokenRequest(refresh_token="refresh-token-123")
        assert request.refresh_token == "refresh-token-123"
    
    def test_missing_token_raises(self):
        """Test that missing token raises validation error."""
        with pytest.raises(ValidationError):
            RefreshTokenRequest()