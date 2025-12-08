"""Authentication service for handling auth flows."""

from __future__ import annotations

import secrets
from typing import Optional

from app.auth.domain import User, UserRole
from app.auth.errors import AuthenticationError
from app.auth.oidc import OIDCClient, TokenPayload, TokenResponse
from app.auth.repository import UserRepository


class AuthService:
    """Service for authentication operations."""

    def __init__(
        self,
        oidc_client: OIDCClient,
        user_repository: UserRepository,
        default_role: UserRole = UserRole.VIEWER,
    ) -> None:
        """Initialize auth service."""
        self._oidc_client = oidc_client
        self._user_repo = user_repository
        self._default_role = default_role

    def generate_state(self) -> str:
        """Generate secure state parameter for OAuth flow."""
        return secrets.token_urlsafe(32)

    def generate_nonce(self) -> str:
        """Generate secure nonce for OIDC flow."""
        return secrets.token_urlsafe(32)

    def get_login_url(self, state: str, nonce: Optional[str] = None) -> str:
        """Get authorization URL for login redirect."""
        return self._oidc_client.get_authorization_url(state, nonce)

    async def handle_callback(
        self, code: str, expected_state: Optional[str] = None, received_state: Optional[str] = None
    ) -> tuple[User, TokenResponse]:
        """Handle OAuth callback and return authenticated user with tokens."""
        # State validation should be done by caller if needed
        if expected_state and received_state and expected_state != received_state:
            raise AuthenticationError("Invalid state parameter")

        # Exchange code for tokens
        tokens = await self._oidc_client.exchange_code(code)

        if not tokens.id_token:
            raise AuthenticationError("No ID token in response")

        # Validate ID token
        id_payload = await self._oidc_client.validate_id_token(tokens.id_token)

        # Extract user info
        email = id_payload.email
        name = id_payload.name or id_payload.preferred_username or id_payload.sub

        if not email:
            # Try userinfo endpoint
            userinfo = await self._oidc_client.get_userinfo(tokens.access_token)
            email = userinfo.get("email")
            name = userinfo.get("name") or userinfo.get("preferred_username") or name

        if not email:
            raise AuthenticationError("Email not available from OIDC provider")

        # Upsert user
        user = await self._user_repo.upsert_from_oidc(
            oidc_sub=id_payload.sub,
            email=email,
            name=name or "Unknown",
            default_role=self._default_role,
        )

        return user, tokens

    async def get_user_from_token(self, token_payload: TokenPayload) -> Optional[User]:
        """Get user from validated token payload."""
        return await self._user_repo.get_by_oidc_sub(token_payload.sub)