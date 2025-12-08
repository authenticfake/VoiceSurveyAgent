"""
Authentication service.

Handles OIDC flow, JWT validation, and user management.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import (
    ExpiredTokenError,
    InvalidStateError,
    InvalidTokenError,
    OIDCError,
)
from app.auth.schemas import (
    AuthenticatedResponse,
    OIDCConfig,
    TokenPayload,
    UserContext,
    UserRole,
)
from app.config import Settings
from app.shared.logging import get_logger
from app.shared.models.user import User

logger = get_logger(__name__)


class AuthService:
    """Service for OIDC authentication and JWT management."""

    def __init__(self, settings: Settings, db_session: AsyncSession) -> None:
        """Initialize auth service with settings and database session."""
        self._settings = settings
        self._db = db_session
        self._jwks_client: httpx.AsyncClient | None = None
        self._jwks_cache: dict[str, Any] = {}
        self._jwks_cache_expiry: datetime | None = None
        self._state_store: dict[str, datetime] = {}  # In production, use Redis

    async def initialize(self) -> None:
        """Initialize JWKS client for token validation."""
        if self._jwks_client is None:
            self._jwks_client = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._jwks_client:
            await self._jwks_client.aclose()
            self._jwks_client = None

    def _get_oidc_config(self) -> OIDCConfig:
        """Get OIDC configuration from settings."""
        return OIDCConfig(
            issuer=HttpUrl(self._settings.oidc_issuer),
            authorization_endpoint=HttpUrl(self._settings.oidc_authorization_endpoint),
            token_endpoint=HttpUrl(self._settings.oidc_token_endpoint),
            userinfo_endpoint=HttpUrl(self._settings.oidc_userinfo_endpoint),
            jwks_uri=HttpUrl(self._settings.oidc_jwks_uri),
            client_id=self._settings.oidc_client_id,
            client_secret=self._settings.oidc_client_secret,
            redirect_uri=HttpUrl(self._settings.oidc_redirect_uri),
            scopes=self._settings.oidc_scopes,
        )

    def generate_authorization_url(self, redirect_url: str | None = None) -> tuple[str, str]:
        """
        Generate OIDC authorization URL with CSRF state.

        Returns:
            Tuple of (authorization_url, state)
        """
        config = self._get_oidc_config()
        state = secrets.token_urlsafe(32)

        # Store state with expiration (5 minutes)
        self._state_store[state] = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Clean expired states
        now = datetime.now(timezone.utc)
        self._state_store = {
            k: v for k, v in self._state_store.items() if v > now
        }

        params = {
            "client_id": config.client_id,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "redirect_uri": redirect_url or str(config.redirect_uri),
            "state": state,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        authorization_url = f"{config.authorization_endpoint}?{query}"

        logger.info(
            "Generated authorization URL",
            extra={"state": state[:8] + "..."},
        )

        return authorization_url, state

    def validate_state(self, state: str) -> bool:
        """Validate CSRF state parameter."""
        if state not in self._state_store:
            return False

        expiry = self._state_store.pop(state)
        return datetime.now(timezone.utc) < expiry

    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str,
        redirect_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from OIDC provider
            state: CSRF state parameter
            redirect_url: Optional redirect URL override

        Returns:
            Token response from OIDC provider

        Raises:
            InvalidStateError: If state validation fails
            OIDCError: If token exchange fails
        """
        if not self.validate_state(state):
            logger.warning("Invalid state parameter", extra={"state": state[:8] + "..."})
            raise InvalidStateError()

        config = self._get_oidc_config()

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_url or str(config.redirect_uri),
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }

        if self._jwks_client is None:
            await self.initialize()

        try:
            response = await self._jwks_client.post(  # type: ignore[union-attr]
                str(config.token_endpoint),
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Token exchange failed", extra={"error": str(e)})
            raise OIDCError(f"Token exchange failed: {e}") from e

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch and cache JWKS from OIDC provider."""
        config = self._get_oidc_config()

        # Check cache
        if (
            self._jwks_cache
            and self._jwks_cache_expiry
            and datetime.now(timezone.utc) < self._jwks_cache_expiry
        ):
            return self._jwks_cache

        if self._jwks_client is None:
            await self.initialize()

        try:
            response = await self._jwks_client.get(str(config.jwks_uri))  # type: ignore[union-attr]
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cache_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            return self._jwks_cache
        except httpx.HTTPError as e:
            logger.error("JWKS fetch failed", extra={"error": str(e)})
            raise OIDCError(f"Failed to fetch JWKS: {e}") from e

    async def validate_token(self, token: str) -> TokenPayload:
        """
        Validate JWT token and return payload.

        Args:
            token: JWT access token

        Returns:
            Validated token payload

        Raises:
            InvalidTokenError: If token is invalid
            ExpiredTokenError: If token has expired
        """
        config = self._get_oidc_config()
        jwks = await self._fetch_jwks()

        try:
            # Decode without verification first to get header
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            # Find matching key
            rsa_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break

            if not rsa_key:
                raise InvalidTokenError("Unable to find matching key")

            # Verify and decode token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=config.client_id,
                issuer=str(config.issuer),
            )

            return TokenPayload(
                sub=payload["sub"],
                email=payload.get("email"),
                name=payload.get("name"),
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                iss=payload["iss"],
                aud=payload["aud"],
            )

        except ExpiredSignatureError as e:
            logger.warning("Token expired")
            raise ExpiredTokenError() from e
        except JWTError as e:
            logger.warning("Token validation failed", extra={"error": str(e)})
            raise InvalidTokenError(f"Token validation failed: {e}") from e

    async def get_or_create_user(self, token_payload: TokenPayload) -> User:
        """
        Get existing user or create new one from OIDC token.

        Args:
            token_payload: Validated token payload

        Returns:
            User database record
        """
        # Try to find existing user
        stmt = select(User).where(User.oidc_sub == token_payload.sub)
        result = await self._db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Update user info if changed
            updated = False
            if token_payload.email and user.email != token_payload.email:
                user.email = token_payload.email
                updated = True
            if token_payload.name and user.name != token_payload.name:
                user.name = token_payload.name
                updated = True

            if updated:
                await self._db.commit()
                logger.info(
                    "Updated user from OIDC",
                    extra={"user_id": str(user.id), "oidc_sub": token_payload.sub},
                )

            return user

        # Create new user with default viewer role
        new_user = User(
            oidc_sub=token_payload.sub,
            email=token_payload.email or f"{token_payload.sub}@unknown.local",
            name=token_payload.name or "Unknown User",
            role="viewer",  # Default role for new users
        )
        self._db.add(new_user)
        await self._db.commit()
        await self._db.refresh(new_user)

        logger.info(
            "Created new user from OIDC",
            extra={"user_id": str(new_user.id), "oidc_sub": token_payload.sub},
        )

        return new_user

    async def authenticate(
        self,
        code: str,
        state: str,
        redirect_url: str | None = None,
    ) -> AuthenticatedResponse:
        """
        Complete OIDC authentication flow.

        Args:
            code: Authorization code
            state: CSRF state
            redirect_url: Optional redirect URL override

        Returns:
            Authentication response with tokens and user context
        """
        # Exchange code for tokens
        token_response = await self.exchange_code_for_tokens(code, state, redirect_url)

        access_token = token_response["access_token"]
        expires_in = token_response.get("expires_in", 3600)
        refresh_token = token_response.get("refresh_token")

        # Validate access token
        token_payload = await self.validate_token(access_token)

        # Get or create user
        user = await self.get_or_create_user(token_payload)

        user_context = UserContext(
            id=user.id,
            oidc_sub=user.oidc_sub,
            email=user.email,
            name=user.name,
            role=UserRole(user.role),
        )

        logger.info(
            "User authenticated",
            extra={"user_id": str(user.id), "role": user.role},
        )

        return AuthenticatedResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=refresh_token,
            user=user_context,
        )

    async def refresh_tokens(self, refresh_token: str) -> AuthenticatedResponse:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New authentication response with fresh tokens
        """
        config = self._get_oidc_config()

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }

        if self._jwks_client is None:
            await self.initialize()

        try:
            response = await self._jwks_client.post(  # type: ignore[union-attr]
                str(config.token_endpoint),
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_response = response.json()
        except httpx.HTTPError as e:
            logger.error("Token refresh failed", extra={"error": str(e)})
            raise OIDCError(f"Token refresh failed: {e}") from e

        access_token = token_response["access_token"]
        expires_in = token_response.get("expires_in", 3600)
        new_refresh_token = token_response.get("refresh_token", refresh_token)

        # Validate new access token
        token_payload = await self.validate_token(access_token)

        # Get user
        user = await self.get_or_create_user(token_payload)

        user_context = UserContext(
            id=user.id,
            oidc_sub=user.oidc_sub,
            email=user.email,
            name=user.name,
            role=UserRole(user.role),
        )

        logger.info(
            "Tokens refreshed",
            extra={"user_id": str(user.id)},
        )

        return AuthenticatedResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=new_refresh_token,
            user=user_context,
        )

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by internal ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()