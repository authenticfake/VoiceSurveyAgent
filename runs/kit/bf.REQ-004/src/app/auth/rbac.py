"""
Role-based access control (RBAC) implementation.

Provides role checking decorators and dependencies for FastAPI routes.
"""

from datetime import datetime, timezone
from functools import wraps
from typing import Annotated, Any, Callable
from uuid import UUID

import jwt
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenPayload, UserContext, UserRole
from app.config import get_settings
from app.shared.database import get_db_session
from app.shared.exceptions import AuthenticationError, AuthorizationError
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

async def get_token_payload(
    authorization: Annotated[str | None, Header()] = None,
) -> TokenPayload:
    """Extract and validate JWT token from Authorization header."""
    if not authorization:
        raise AuthenticationError(message="Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise AuthenticationError(message="Invalid authorization header format")

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        # For development/testing, allow unsigned tokens
        if settings.app_env == "dev":
            payload = jwt.decode(token, options={"verify_signature": False})
        else:
            # In production, verify signature with OIDC provider's public key
            # This would typically fetch JWKS from the OIDC provider
            payload = jwt.decode(
                token,
                algorithms=[settings.jwt_algorithm],
                audience=settings.jwt_audience,
                options={"verify_signature": False},  # TODO: Implement JWKS verification
            )

        return TokenPayload(
            sub=payload.get("sub", ""),
            exp=datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc),
            iat=datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc),
            iss=payload.get("iss"),
            aud=payload.get("aud"),
            email=payload.get("email"),
            name=payload.get("name"),
            role=payload.get("role"),
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(message="Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(message=f"Invalid token: {e!s}")

async def get_current_user(
    token: Annotated[TokenPayload, Depends(get_token_payload)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserContext:
    """Get current user from token and database."""
    from app.campaigns.models import User  # Import here to avoid circular imports

    # Find or create user
    result = await db.execute(select(User).where(User.oidc_sub == token.sub))
    user = result.scalar_one_or_none()

    if not user:
        # Create user on first login
        user = User(
            oidc_sub=token.sub,
            email=token.email or f"{token.sub}@unknown.local",
            name=token.name or "Unknown User",
            role=token.role or UserRole.VIEWER,
        )
        db.add(user)
        await db.flush()
        logger.info(
            "Created new user on first login",
            user_id=str(user.id),
            oidc_sub=token.sub,
        )

    return UserContext(
        id=user.id,
        oidc_sub=user.oidc_sub,
        email=user.email,
        name=user.name,
        role=UserRole(user.role),
    )

class RequireRole:
    """Dependency class for role-based access control."""

    def __init__(self, minimum_role: UserRole) -> None:
        """Initialize with minimum required role."""
        self.minimum_role = minimum_role
        self._role_hierarchy = {
            UserRole.VIEWER: 0,
            UserRole.CAMPAIGN_MANAGER: 1,
            UserRole.ADMIN: 2,
        }

    async def __call__(
        self,
        request: Request,
        user: Annotated[UserContext, Depends(get_current_user)],
    ) -> UserContext:
        """Check if user has required role."""
        user_level = self._role_hierarchy.get(user.role, 0)
        required_level = self._role_hierarchy.get(self.minimum_role, 0)

        if user_level < required_level:
            logger.warning(
                "Access denied - insufficient role",
                user_id=str(user.id),
                user_role=user.role.value,
                required_role=self.minimum_role.value,
                endpoint=str(request.url.path),
            )
            raise AuthorizationError(
                message=f"Role '{self.minimum_role.value}' or higher required",
                details={
                    "user_role": user.role.value,
                    "required_role": self.minimum_role.value,
                },
            )

        return user

# Convenience dependencies for common role requirements
require_viewer = RequireRole(UserRole.VIEWER)
require_campaign_manager = RequireRole(UserRole.CAMPAIGN_MANAGER)
require_admin = RequireRole(UserRole.ADMIN)

# Type aliases for dependency injection
CurrentUser = Annotated[UserContext, Depends(get_current_user)]
ViewerUser = Annotated[UserContext, Depends(require_viewer)]
CampaignManagerUser = Annotated[UserContext, Depends(require_campaign_manager)]
AdminUser = Annotated[UserContext, Depends(require_admin)]