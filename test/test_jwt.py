"""
Tests for JWT service.

REQ-002: OIDC authentication integration
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.auth.jwt import JWTService
from app.config import Settings
from app.shared.exceptions import InvalidTokenError, TokenExpiredError


class TestJWTService:
    """Tests for JWTService."""

    def test_create_access_token(
        self,
        jwt_service: JWTService,
        test_user_data: dict,
    ) -> None:
        """Test access token creation."""
        token = jwt_service.create_access_token(
            user_id=test_user_data["id"],
            oidc_sub=test_user_data["oidc_sub"],
            email=test_user_data["email"],
            role=test_user_data["role"],
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(
        self,
        jwt_service: JWTService,
        test_user_data: dict,
    ) -> None:
        """Test refresh token creation."""
        token = jwt_service.create_refresh_token(
            user_id=test_user_data["id"],
            oidc_sub=test_user_data["oidc_sub"],
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_access_token(
        self,
        jwt_service: JWTService,
        valid_access_token: str,
        test_user_data: dict,
    ) -> None:
        """Test verification of valid access token."""
        payload = jwt_service.verify_token(valid_access_token)

        assert payload.sub == test_user_data["oidc_sub"]
        assert payload.type == "access"
        assert payload.user_id == test_user_data["id"]
        assert payload.email == test_user_data["email"]
        assert payload.role == test_user_data["role"]

    def test_verify_valid_refresh_token(
        self,
        jwt_service: JWTService,
        valid_refresh_token: str,
        test_user_data: dict,
    ) -> None:
        """Test verification of valid refresh token."""
        payload = jwt_service.verify_token(valid_refresh_token)

        assert payload.sub == test_user_data["oidc_sub"]
        assert payload.type == "refresh"
        assert payload.user_id == test_user_data["id"]

    def test_verify_expired_token(
        self,
        jwt_service: JWTService,
        expired_access_token: str,
    ) -> None:
        """Test that expired tokens raise TokenExpiredError."""
        with pytest.raises(TokenExpiredError):
            jwt_service.verify_token(expired_access_token)

    def test_verify_invalid_token(
        self,
        jwt_service: JWTService,
    ) -> None:
        """Test that invalid tokens raise InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            jwt_service.verify_token("invalid-token")

    def test_verify_token_wrong_secret(
        self,
        test_settings: Settings,
        test_user_data: dict,
    ) -> None:
        """Test that tokens signed with wrong secret are rejected."""
        # Create token with different secret
        wrong_settings = Settings(
            jwt_secret_key="wrong-secret-key",
            jwt_algorithm=test_settings.jwt_algorithm,
        )
        wrong_service = JWTService(settings=wrong_settings)
        token = wrong_service.create_access_token(
            user_id=test_user_data["id"],
            oidc_sub=test_user_data["oidc_sub"],
            email=test_user_data["email"],
            role=test_user_data["role"],
        )

        # Verify with correct secret should fail
        correct_service = JWTService(settings=test_settings)
        with pytest.raises(InvalidTokenError):
            correct_service.verify_token(token)

    def test_get_token_expiry_seconds(
        self,
        jwt_service: JWTService,
        test_settings: Settings,
    ) -> None:
        """Test token expiry calculation."""
        expected = test_settings.jwt_access_token_expire_minutes * 60
        assert jwt_service.get_token_expiry_seconds() == expected

    def test_token_contains_correct_timestamps(
        self,
        jwt_service: JWTService,
        test_user_data: dict,
    ) -> None:
        """Test that tokens contain correct iat and exp timestamps."""
        before = datetime.now(timezone.utc)
        token = jwt_service.create_access_token(
            user_id=test_user_data["id"],
            oidc_sub=test_user_data["oidc_sub"],
            email=test_user_data["email"],
            role=test_user_data["role"],
        )
        after = datetime.now(timezone.utc)

        payload = jwt_service.verify_token(token)

        # iat should be between before and after
        assert before <= payload.iat <= after

        # exp should be iat + configured minutes
        expected_exp = payload.iat + timedelta(minutes=60)
        assert abs((payload.exp - expected_exp).total_seconds()) < 2