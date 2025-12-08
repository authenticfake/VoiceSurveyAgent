"""
Authentication service.

Implements OIDC authorization code flow and JWT token management.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
import jwt
from jwt import PyJWKClient
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    AuthenticatedResponse,
    OIDCConfig,
    TokenPayload,
    TokenResponse,
    UserContext,
    UserRole,
)
from app.campaigns.models import User, UserRoleEnum
from app.config import Settings
from app.shared.exceptions import AuthenticationError, ConfigurationError
from app.shared.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for OIDC authentication and JWT management."""

    def __init__(
        self,
        settings: Settings,
        db_session: AsyncSession,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize auth service with configuration."""
        self._settings = settings
        self._db = db_session
        self._http_client = http_client or httpx.AsyncClient(timeout=30.0)
        self._oidc_config: OIDCConfig | None = None
        self._jwks_client: PyJWKClient | None = None
        self._state_store: dict[str, dict[str, Any]] = {}  # In production, use Redis

    async def initialize(self) -> None:
        """Initialize OIDC configuration from discovery endpoint."""
        if not self._settings.oidc_issuer:
            raise ConfigurationError(
                message="OIDC issuer not configured",
                details={"setting": "OIDC_ISSUER"},
            )

        discovery_url = f"{self._settings.oidc_issuer}/.well-known/openid-configuration"

        try:
            response = await self._http_client.get(discovery_url)
            response.raise_for_status()
            config_data = response.json()

            self._oidc_config = OIDCConfig(
                issuer=config_data["issuer"],
                authorization_endpoint=config_data["authorization_endpoint"],
                token_endpoint=config_data["token_endpoint"],
                userinfo_endpoint=config_data["userinfo_endpoint"],
                jwks_uri=config_data["jwks_uri"],
                client_id=self._settings.oidc_client_id,
                client_secret=self._settings.oidc_client_secret,
                redirect_uri=self._settings.oidc_redirect_uri,
            )

            self._jwks_client = PyJWKClient(str(self._oidc_config.jwks_uri))

            logger.info(
                "OIDC configuration loaded",
                issuer=str(self._oidc_config.issuer),
            )

        except httpx.HTTPError as e:
            logger.error("Failed to fetch OIDC configuration", error=str(e))
            raise ConfigurationError(
                message="Failed to fetch OIDC configuration",
                details={"url": discovery_url, "error": str(e)},
            ) from e

    def generate_authorization_url(self, redirect_url: str | None = None) -> tuple[str, str]:
        """Generate OIDC authorization URL with state parameter.

        Returns:
            Tuple of (authorization_url, state)
        """
        if not self._oidc_config:
            raise ConfigurationError(message="OIDC not initialized")

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        # Store state for validation
        self._state_store[state] = {
            "nonce": nonce,
            "redirect_url": redirect_url,
            "created_at": datetime.now(timezone.utc),
        }

        params = {
            "client_id": self._oidc_config.client_id,
            "response_type": "code",
            "scope": " ".join(self._oidc_config.scopes),
            "redirect_uri": str(self._oidc_config.redirect_uri),
            "state": state,
            "nonce": nonce,
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{self._oidc_config.authorization_endpoint}?{query_string}"

        return auth_url, state

    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str,
    ) -> AuthenticatedResponse:
        """Exchange authorization code for tokens and create/update user.

        Args:
            code: Authorization code from callback
            state: State parameter for validation

        Returns:
            Authenticated response with tokens and user context
        """
        if not self._oidc_config:
            raise ConfigurationError(message="OIDC not initialized")

        # Validate state
        state_data = self._state_store.pop(state, None)
        if not state_data:
            raise AuthenticationError(
                message="Invalid or expired state parameter",
                details={"state": state},
            )

        # Check state expiration (5 minutes)
        created_at = state_data["created_at"]
        if datetime.now(timezone.utc) - created_at > timedelta(minutes=5):
            raise AuthenticationError(message="State parameter expired")

        # Exchange code for tokens
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": str(self._oidc_config.redirect_uri),
            "client_id": self._oidc_config.client_id,
            "client_secret": self._oidc_config.client_secret,
        }

        try:
            response = await self._http_client.post(
                str(self._oidc_config.token_endpoint),
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_response = TokenResponse(**response.json())

        except httpx.HTTPError as e:
            logger.error("Token exchange failed", error=str(e))
            raise AuthenticationError(
                message="Failed to exchange authorization code",
                details={"error": str(e)},
            ) from e

        # Validate and decode ID token
        if not token_response.id_token:
            raise AuthenticationError(message="No ID token in response")

        token_payload = self._validate_token(token_response.id_token)

        # Create or update user
        user = await self._get_or_create_user(token_payload)

        # Generate session token
        session_token, expires_in = self._generate_session_token(user)

        return AuthenticatedResponse(
            access_token=session_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=token_response.refresh_token,
            user=UserContext(
                id=user.id,
                oidc_sub=user.oidc_sub,
                email=user.email,
                name=user.name,
                role=UserRole(user.role.value),
            ),
        )

    async def refresh_tokens(self, refresh_token: str) -> AuthenticatedResponse:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New authenticated response with fresh tokens
        """
        if not self._oidc_config:
            raise ConfigurationError(message="OIDC not initialized")

        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._oidc_config.client_id,
            "client_secret": self._oidc_config.client_secret,
        }

        try:
            response = await self._http_client.post(
                str(self._oidc_config.token_endpoint),
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_response = TokenResponse(**response.json())

        except httpx.HTTPError as e:
            logger.error("Token refresh failed", error=str(e))
            raise AuthenticationError(
                message="Failed to refresh token",
                details={"error": str(e)},
            ) from e

        # Validate new ID token if present
        if token_response.id_token:
            token_payload = self._validate_token(token_response.id_token)
            user = await self._get_or_create_user(token_payload)
        else:
            # Use access token to get user info
            user = await self._get_user_from_access_token(token_response.access_token)

        # Generate new session token
        session_token, expires_in = self._generate_session_token(user)

        return AuthenticatedResponse(
            access_token=session_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=token_response.refresh_token or refresh_token,
            user=UserContext(
                id=user.id,
                oidc_sub=user.oidc_sub,
                email=user.email,
                name=user.name,
                role=UserRole(user.role.value),
            ),
        )

    def validate_session_token(self, token: str) -> TokenPayload:
        """Validate a session JWT token.

        Args:
            token: JWT token to validate

        Returns:
            Validated token payload

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
                audience=self._settings.jwt_audience,
            )

            return TokenPayload(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                iss=payload.get("iss"),
                aud=payload.get("aud"),
                email=payload.get("email"),
                name=payload.get("name"),
                role=UserRole(payload["role"]) if payload.get("role") else None,
            )

        except jwt.ExpiredSignatureError as e:
            raise AuthenticationError(message="Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(
                message="Invalid token",
                details={"error": str(e)},
            ) from e

    def _validate_token(self, token: str) -> TokenPayload:
        """Validate OIDC ID token using JWKS.

        Args:
            token: ID token to validate

        Returns:
            Validated token payload
        """
        if not self._jwks_client or not self._oidc_config:
            raise ConfigurationError(message="OIDC not initialized")

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self._oidc_config.client_id,
                issuer=str(self._oidc_config.issuer),
            )

            return TokenPayload(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                iss=payload.get("iss"),
                aud=payload.get("aud"),
                email=payload.get("email"),
                name=payload.get("name"),
            )

        except jwt.ExpiredSignatureError as e:
            raise AuthenticationError(message="ID token has expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(
                message="Invalid ID token",
                details={"error": str(e)},
            ) from e

    async def _get_or_create_user(self, token_payload: TokenPayload) -> User:
        """Get existing user or create new one from token payload.

        Args:
            token_payload: Validated token payload

        Returns:
            User entity
        """
        result = await self._db.execute(
            select(User).where(User.oidc_sub == token_payload.sub)
        )
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
                await self._db.flush()
                logger.info(
                    "Updated user from OIDC",
                    user_id=str(user.id),
                    oidc_sub=token_payload.sub,
                )
        else:
            # Create new user with default viewer role
            user = User(
                oidc_sub=token_payload.sub,
                email=token_payload.email or f"{token_payload.sub}@unknown.local",
                name=token_payload.name or "Unknown User",
                role=UserRoleEnum.VIEWER,
            )
            self._db.add(user)
            await self._db.flush()
            await self._db.refresh(user)

            logger.info(
                "Created new user from OIDC",
                user_id=str(user.id),
                oidc_sub=token_payload.sub,
            )

        return user

    async def _get_user_from_access_token(self, access_token: str) -> User:
        """Get user info using access token and userinfo endpoint.

        Args:
            access_token: Valid access token

        Returns:
            User entity
        """
        if not self._oidc_config:
            raise ConfigurationError(message="OIDC not initialized")

        try:
            response = await self._http_client.get(
                str(self._oidc_config.userinfo_endpoint),
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            userinfo = response.json()

        except httpx.HTTPError as e:
            logger.error("Failed to fetch user info", error=str(e))
            raise AuthenticationError(
                message="Failed to fetch user info",
                details={"error": str(e)},
            ) from e

        token_payload = TokenPayload(
            sub=userinfo["sub"],
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            email=userinfo.get("email"),
            name=userinfo.get("name"),
        )

        return await self._get_or_create_user(token_payload)

    def _generate_session_token(self, user: User) -> tuple[str, int]:
        """Generate a session JWT token for the user.

        Args:
            user: User entity

        Returns:
            Tuple of (token, expires_in_seconds)
        """
        expires_in = self._settings.jwt_expiration_minutes * 60
        now = datetime.now(timezone.utc)

        payload = {
            "sub": user.oidc_sub,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "user_id": str(user.id),
        }

        token = jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

        return token, expires_in

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User entity or None
        """
        result = await self._db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_oidc_sub(self, oidc_sub: str) -> User | None:
        """Get user by OIDC subject identifier.

        Args:
            oidc_sub: OIDC subject identifier

        Returns:
            User entity or None
        """
        result = await self._db.execute(
            select(User).where(User.oidc_sub == oidc_sub)
        )
        return result.scalar_one_or_none()