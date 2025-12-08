"""Tests for JWT token handling."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.auth.jwt import JWTHandler
from app.auth.models import UserRole
from app.config import Settings
from app.shared.exceptions import TokenExpiredError, TokenInvalidError

@pytest.fixture
def jwt_handler(test_settings: Settings) -> JWTHandler:
    """Create JWT handler with test settings."""
    return JWTHandler(test_settings)

class TestJWTHandler:
    """Tests for JWTHandler class."""

    def test_create_access_token(self, jwt_handler: JWTHandler) -> None:
        """Test creating an access token."""
        user_id = uuid4()
        token = jwt_handler.create_access_token(
            user_id=user_id,
            email="test@example.com",
            role=UserRole.CAMPAIGN_MANAGER.value,
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, jwt_handler: JWTHandler) -> None:
        """Test creating a refresh token."""
        user_id = uuid4()
        token = jwt_handler.create_refresh_token(user_id=user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_validate_access_token(self, jwt_handler: JWTHandler) -> None:
        """Test validating an access token."""
        user_id = uuid4()
        email = "test@example.com"
        role = UserRole.ADMIN.value

        token = jwt_handler.create_access_token(
            user_id=user_id,
            email=email,
            role=role,
        )

        payload = jwt_handler.validate_access_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["email"] == email
        assert payload["role"] == role
        assert payload["type"] == "access"

    def test_validate_refresh_token(self, jwt_handler: JWTHandler) -> None:
        """Test validating a refresh token."""
        user_id = uuid4()
        token = jwt_handler.create_refresh_token(user_id=user_id)

        payload = jwt_handler.validate_refresh_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_invalid_token_raises_error(self, jwt_handler: JWTHandler) -> None:
        """Test that invalid token raises TokenInvalidError."""
        with pytest.raises(TokenInvalidError):
            jwt_handler.decode_token("invalid-token")

    def test_access_token_as_refresh_raises_error(
        self, jwt_handler: JWTHandler
    ) -> None:
        """Test that using access token as refresh raises error."""
        user_id = uuid4()
        token = jwt_handler.create_access_token(
            user_id=user_id,
            email="test@example.com",
            role=UserRole.VIEWER.value,
        )

        with pytest.raises(TokenInvalidError, match="Not a refresh token"):
            jwt_handler.validate_refresh_token(token)

    def test_refresh_token_as_access_raises_error(
        self, jwt_handler: JWTHandler
    ) -> None:
        """Test that using refresh token as access raises error."""
        user_id = uuid4()
        token = jwt_handler.create_refresh_token(user_id=user_id)

        with pytest.raises(TokenInvalidError, match="Not an access token"):
            jwt_handler.validate_access_token(token)

    def test_additional_claims(self, jwt_handler: JWTHandler) -> None:
        """Test adding additional claims to access token."""
        user_id = uuid4()
        token = jwt_handler.create_access_token(
            user_id=user_id,
            email="test@example.com",
            role=UserRole.CAMPAIGN_MANAGER.value,
            additional_claims={"custom_claim": "custom_value"},
        )

        payload = jwt_handler.validate_access_token(token)
        assert payload["custom_claim"] == "custom_value"

    def test_get_token_expiry(
        self, jwt_handler: JWTHandler, test_settings: Settings
    ) -> None:
        """Test getting token expiry in seconds."""
        expiry = jwt_handler.get_token_expiry()
        expected = test_settings.jwt_access_token_expire_minutes * 60
        assert expiry == expected