"""
Tests for authentication service.

REQ-002: OIDC authentication integration
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.schemas import OIDCTokenResponse, OIDCUserInfo
from app.auth.service import AuthService
from app.config import Settings
from app.shared.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    UserNotFoundError,
)


class TestAuthService:
    """Tests for AuthService."""

    def test_initiate_login(
        self,
        auth_service: AuthService,
        mock_oidc_client: MagicMock,
    ) -> None:
        """Test login initiation."""
        response = auth_service.initiate_login()

        assert response.state == "test-state-12345"
        assert "authorize" in response.authorization_url
        mock_oidc_client.generate_state.assert_called_once()
        mock_oidc_client.get_authorization_url.assert_called_once_with("test-state-12345")

    @pytest.mark.asyncio
    async def test_handle_callback_success(
        self,
        auth_service: AuthService,
        mock_oidc_client: MagicMock,
        mock_oidc_token_response: OIDCTokenResponse,
        mock_oidc_userinfo: OIDCUserInfo,
    ) -> None:
        """Test successful callback handling."""
        mock_oidc_client.exchange_code = AsyncMock(return_value=mock_oidc_token_response)
        mock_oidc_client.get_userinfo = AsyncMock(return_value=mock_oidc_userinfo)

        response = await auth_service.handle_callback(
            code="auth-code",
            state="test-state",
            expected_state="test-state",
        )

        assert response.access_token is not None
        assert response.refresh_token is not None
        assert response.token_type == "Bearer"
        assert response.expires_in > 0
        assert response.user.email == mock_oidc_userinfo.email
        assert response.user.name == mock_oidc_userinfo.name
        assert response.user.oidc_sub == mock_oidc_userinfo.sub

    @pytest.mark.asyncio
    async def test_handle_callback_state_mismatch(
        self,
        auth_service: AuthService,
    ) -> None:
        """Test callback with state mismatch."""
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.handle_callback(
                code="auth-code",
                state="wrong-state",
                expected_state="expected-state",
            )

        assert exc_info.value.code == "INVALID_STATE"

    @pytest.mark.asyncio
    async def test_handle_callback_creates_new_user(
        self,
        auth_service: AuthService,
        mock_oidc_client: MagicMock,
        mock_oidc_token_response: OIDCTokenResponse,
        db_session: AsyncSession,
    ) -> None:
        """Test callback creates new user when not found."""
        new_userinfo = OIDCUserInfo(
            sub="oidc|newuser456",
            email="newuser@example.com",
            name="New User",
        )
        mock_oidc_client.exchange_code = AsyncMock(return_value=mock_oidc_token_response)
        mock_oidc_client.get_userinfo = AsyncMock(return_value=new_userinfo)

        response = await auth_service.handle_callback(
            code="auth-code",
            state="test-state",
            expected_state="test-state",
        )

        assert response.user.oidc_sub == "oidc|newuser456"
        assert response.user.email == "newuser@example.com"
        assert response.user.role == "viewer"  # Default role

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(
        self,
        auth_service: AuthService,
        test_user: User,
        valid_refresh_token: str,
    ) -> None:
        """Test successful token refresh."""
        response = await auth_service.refresh_tokens(valid_refresh_token)

        assert response.access_token is not None
        assert response.refresh_token is not None
        assert response.expires_in > 0

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_type(
        self,
        auth_service: AuthService,
        valid_access_token: str,
    ) -> None:
        """Test refresh with access token fails."""
        with pytest.raises(InvalidTokenError) as exc_info:
            await auth_service.refresh_tokens(valid_access_token)

        assert "Invalid token type" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_refresh_tokens_user_not_found(
        self,
        db_session: AsyncSession,
        test_settings: Settings,
        mock_oidc_client: MagicMock,
    ) -> None:
        """Test refresh when user no longer exists."""
        from app.auth.jwt import JWTService

        jwt_service = JWTService(settings=test_settings)
        service = AuthService(
            session=db_session,
            settings=test_settings,
            oidc_client=mock_oidc_client,
        )

        # Create token for non-existent user
        refresh_token = jwt_service.create_refresh_token(
            user_id=uuid4(),
            oidc_sub="oidc|deleted",
        )

        with pytest.raises(UserNotFoundError):
            await service.refresh_tokens(refresh_token)

    def test_verify_access_token_success(
        self,
        auth_service: AuthService,
        valid_access_token: str,
        test_user_data: dict,
    ) -> None:
        """Test access token verification."""
        payload = auth_service.verify_access_token(valid_access_token)

        assert payload.sub == test_user_data["oidc_sub"]
        assert payload.type == "access"

    def test_verify_access_token_wrong_type(
        self,
        auth_service: AuthService,
        valid_refresh_token: str,
    ) -> None:
        """Test verification fails for refresh token."""
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.verify_access_token(valid_refresh_token)

        assert "Invalid token type" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_user_profile_success(
        self,
        auth_service: AuthService,
        test_user: User,
    ) -> None:
        """Test getting user profile."""
        profile = await auth_service.get_user_profile(test_user.id)

        assert profile.id == test_user.id
        assert profile.email == test_user.email
        assert profile.name == test_user.name
        assert profile.role == test_user.role

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(
        self,
        auth_service: AuthService,
    ) -> None:
        """Test getting non-existent user profile."""
        with pytest.raises(UserNotFoundError):
            await auth_service.get_user_profile(uuid4())