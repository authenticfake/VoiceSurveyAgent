"""
Authentication middleware.

Provides JWT validation middleware for FastAPI.
"""

from typing import Annotated

import jwt
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenPayload, UserContext, UserRole
from app.campaigns.models import User
from app.config import Settings, get_settings
from app.shared.database import get_db_session
from app.shared.exceptions import AuthenticationError
from app.shared.logging import get_logger

logger = get_logger(__name__)


async def get_token_payload(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> TokenPayload:
    """Extract and validate JWT token from Authorization header.

    Args:
        authorization: Authorization header value
        settings: Application settings

    Returns:
        Validated token payload

    Raises:
        AuthenticationError: If token is missing, invalid, or expired
    """
    if not authorization:
        raise AuthenticationError(message="Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise AuthenticationError(message="Invalid authorization header format")

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
        )

        from datetime import datetime, timezone

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
        logger.warning("Token expired", error=str(e))
        raise AuthenticationError(message="Token has expired") from e
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        raise AuthenticationError(
            message="Invalid token",
            details={"error": str(e)},
        ) from e


async def get_current_user(
    token: Annotated[TokenPayload, Depends(get_token_payload)],
    db: AsyncSession = Depends(get_db_session),
) -> UserContext:
    """Get current authenticated user from token.

    Args:
        token: Validated token payload
        db: Database session

    Returns:
        Current user context

    Raises:
        AuthenticationError: If user not found
    """
    result = await db.execute(
        select(User).where(User.oidc_sub == token.sub)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create user on first login (should have been created during auth flow)
        logger.warning(
            "User not found for token, creating",
            oidc_sub=token.sub,
        )
        from app.campaigns.models import UserRoleEnum

        user = User(
            oidc_sub=token.sub,
            email=token.email or f"{token.sub}@unknown.local",
            name=token.name or "Unknown User",
            role=UserRoleEnum.VIEWER,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    return UserContext(
        id=user.id,
        oidc_sub=user.oidc_sub,
        email=user.email,
        name=user.name,
        role=UserRole(user.role.value),
    )


# Type alias for dependency injection
CurrentUser = Annotated[UserContext, Depends(get_current_user)]