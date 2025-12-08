"""Authentication service for OIDC and session management."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import JWTHandler
from app.auth.models import User
from app.auth.oidc import OIDCClient, OIDCTokens, OIDCUserInfo
from app.auth.repository import UserRepository
from app.auth.schemas import (
    AuthCallbackResponse,
    AuthLoginResponse,
    TokenResponse,
    UserProfile,
)
from app.config import Settings, get_settings
from app.shared.exceptions import AuthenticationError, TokenInvalidError
from app.shared.logging import get_logger

logger = get_logger(__name__)

class AuthService:
    """Service for handling authentication flows."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        oidc_client: OIDCClient | None = None,
        jwt_handler: JWTHandler | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._oidc_client = oidc_client or OIDCClient(self._settings)
        self._jwt_handler = jwt_handler or JWTHandler(self._settings)
        self._user_repo = UserRepository(session)

    async def initiate_login(self) -> AuthLoginResponse:
        """Initiate OIDC login flow."""
        state = self._oidc_client.generate_state()
        authorization_url = await self._oidc_client.get_authorization_url(state)

        logger.info("Initiated OIDC login flow")
        return AuthLoginResponse(
            authorization_url=authorization_url,
            state=state,
        )

    async def handle_callback(
        self,
        code: str,
        state: str,
        expected_state: str,
    ) -> AuthCallbackResponse:
        """Handle OIDC callback and create session."""
        # Validate state
        if state != expected_state:
            logger.warning("State mismatch in OIDC callback")
            raise AuthenticationError("Invalid state parameter")

        # Exchange code for tokens
        oidc_tokens = await self._oidc_client.exchange_code(code)

        # Get user info
        user_info = await self._oidc_client.get_userinfo(oidc_tokens.access_token)

        # Create or update user
        user = await self._user_repo.upsert_from_oidc(
            oidc_sub=user_info.sub,
            email=user_info.email,
            name=user_info.name,
        )

        # Create session tokens
        tokens = self._create_tokens(user)

        logger.info(f"User authenticated: {user.id}")
        return AuthCallbackResponse(
            user=UserProfile.model_validate(user),
            tokens=tokens,
        )

    async def refresh_session(self, refresh_token: str) -> TokenResponse:
        """Refresh session using refresh token."""
        # Validate refresh token
        payload = self._jwt_handler.validate_refresh_token(refresh_token)
        user_id = UUID(payload["sub"])

        # Get user
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise TokenInvalidError("User not found")

        # Create new tokens
        tokens = self._create_tokens(user)

        logger.info(f"Session refreshed for user: {user.id}")
        return tokens

    async def validate_token(self, token: str) -> User:
        """Validate access token and return user."""
        payload = self._jwt_handler.validate_access_token(token)
        user_id = UUID(payload["sub"])

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise TokenInvalidError("User not found")

        return user

    async def get_user_profile(self, user_id: UUID) -> UserProfile | None:
        """Get user profile by ID."""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            return None
        return UserProfile.model_validate(user)

    def _create_tokens(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for user."""
        access_token = self._jwt_handler.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value,
        )
        refresh_token = self._jwt_handler.create_refresh_token(user_id=user.id)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=self._jwt_handler.get_token_expiry(),
            refresh_token=refresh_token,
        )

    async def close(self) -> None:
        """Close resources."""
        await self._oidc_client.close()