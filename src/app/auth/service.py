"""
Authentication service orchestrating OIDC and JWT operations.

REQ-002: OIDC authentication integration
"""

from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import JWTService, JWTServiceProtocol
from app.auth.models import User
from app.auth.oidc import OIDCClient, OIDCClientProtocol
from app.auth.repository import UserRepository, UserRepositoryProtocol
from app.auth.schemas import (
    AuthCallbackResponse,
    LoginResponse,
    RefreshTokenResponse,
    TokenPayload,
    UserProfile,
)
from app.config import Settings, get_settings
from app.shared.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    UserNotFoundError,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


class AuthServiceProtocol(Protocol):
    """Protocol for authentication service operations."""

    def initiate_login(self) -> LoginResponse: ...
    async def handle_callback(
        self,
        code: str,
        state: str,
        expected_state: str,
    ) -> AuthCallbackResponse: ...
    async def refresh_tokens(self, refresh_token: str) -> RefreshTokenResponse: ...
    def verify_access_token(self, token: str) -> TokenPayload: ...
    async def get_user_profile(self, user_id: UUID) -> UserProfile: ...


class AuthService:
    """Service for authentication operations."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        oidc_client: OIDCClientProtocol | None = None,
        jwt_service: JWTServiceProtocol | None = None,
        user_repository: UserRepositoryProtocol | None = None,
    ) -> None:
        """Initialize authentication service.

        Args:
            session: Database session.
            settings: Application settings.
            oidc_client: OIDC client for IdP integration.
            jwt_service: JWT service for token operations.
            user_repository: User repository for database operations.
        """
        self._settings = settings or get_settings()
        self._session = session
        self._oidc_client = oidc_client or OIDCClient(self._settings)
        self._jwt_service = jwt_service or JWTService(self._settings)
        self._user_repository = user_repository or UserRepository(session)

    def initiate_login(self) -> LoginResponse:
        """Initiate OIDC login flow.

        Returns:
            Login response with authorization URL and state.
        """
        state = self._oidc_client.generate_state()
        authorization_url = self._oidc_client.get_authorization_url(state)

        logger.info("Login initiated", extra={"state": state[:8] + "..."})

        return LoginResponse(
            authorization_url=authorization_url,
            state=state,
        )

    async def handle_callback(
        self,
        code: str,
        state: str,
        expected_state: str,
    ) -> AuthCallbackResponse:
        """Handle OIDC callback after user authentication.

        Args:
            code: Authorization code from IdP.
            state: State parameter from callback.
            expected_state: Expected state for CSRF validation.

        Returns:
            Callback response with tokens and user profile.

        Raises:
            AuthenticationError: If state validation fails.
            OIDCError: If OIDC operations fail.
        """
        # Validate state for CSRF protection
        if state != expected_state:
            logger.warning(
                "State mismatch in OIDC callback",
                extra={"received": state[:8] + "...", "expected": expected_state[:8] + "..."},
            )
            raise AuthenticationError(
                message="Invalid state parameter",
                code="INVALID_STATE",
            )

        # Exchange code for tokens
        token_response = await self._oidc_client.exchange_code(code)

        # Get user info from IdP
        userinfo = await self._oidc_client.get_userinfo(token_response.access_token)

        # Determine user name from available claims
        name = (
            userinfo.name
            or f"{userinfo.given_name or ''} {userinfo.family_name or ''}".strip()
            or userinfo.preferred_username
            or userinfo.email
            or userinfo.sub
        )

        # Create or update user in database
        user = await self._user_repository.upsert_from_oidc(
            oidc_sub=userinfo.sub,
            email=userinfo.email or f"{userinfo.sub}@unknown.local",
            name=name,
        )

        # Create session tokens
        access_token = self._jwt_service.create_access_token(
            user_id=user.id,
            oidc_sub=user.oidc_sub,
            email=user.email,
            role=user.role,
        )
        refresh_token = self._jwt_service.create_refresh_token(
            user_id=user.id,
            oidc_sub=user.oidc_sub,
        )

        logger.info(
            "User authenticated",
            extra={"user_id": str(user.id), "email": user.email},
        )

        return AuthCallbackResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._jwt_service.get_token_expiry_seconds(),
            user=UserProfile(
                id=user.id,
                oidc_sub=user.oidc_sub,
                email=user.email,
                name=user.name,
                role=user.role,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )

    async def refresh_tokens(self, refresh_token: str) -> RefreshTokenResponse:
        """Refresh access and refresh tokens.

        Args:
            refresh_token: Current refresh token.

        Returns:
            New token pair.

        Raises:
            InvalidTokenError: If refresh token is invalid.
            UserNotFoundError: If user no longer exists.
        """
        # Verify refresh token
        payload = self._jwt_service.verify_token(refresh_token)

        if payload.type != "refresh":
            raise InvalidTokenError(message="Invalid token type for refresh")

        if payload.user_id is None:
            raise InvalidTokenError(message="Token missing user_id")

        # Get user from database
        user = await self._user_repository.get_by_id(payload.user_id)
        if user is None:
            raise UserNotFoundError(
                message="User not found",
                details={"user_id": str(payload.user_id)},
            )

        # Create new tokens
        new_access_token = self._jwt_service.create_access_token(
            user_id=user.id,
            oidc_sub=user.oidc_sub,
            email=user.email,
            role=user.role,
        )
        new_refresh_token = self._jwt_service.create_refresh_token(
            user_id=user.id,
            oidc_sub=user.oidc_sub,
        )

        logger.info(
            "Tokens refreshed",
            extra={"user_id": str(user.id)},
        )

        return RefreshTokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=self._jwt_service.get_token_expiry_seconds(),
        )

    def verify_access_token(self, token: str) -> TokenPayload:
        """Verify an access token.

        Args:
            token: Access token to verify.

        Returns:
            Token payload if valid.

        Raises:
            InvalidTokenError: If token is invalid or not an access token.
        """
        payload = self._jwt_service.verify_token(token)

        if payload.type != "access":
            raise InvalidTokenError(message="Invalid token type")

        return payload

    async def get_user_profile(self, user_id: UUID) -> UserProfile:
        """Get user profile by ID.

        Args:
            user_id: User UUID.

        Returns:
            User profile.

        Raises:
            UserNotFoundError: If user not found.
        """
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(
                message="User not found",
                details={"user_id": str(user_id)},
            )

        return UserProfile(
            id=user.id,
            oidc_sub=user.oidc_sub,
            email=user.email,
            name=user.name,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )