"""
Role-based access control (RBAC) implementation.

Provides role checking decorators and dependencies for FastAPI routes.
Extends the authentication module from REQ-002.
"""

from datetime import datetime, timezone
from functools import wraps
from typing import Annotated, Any, Callable
from uuid import UUID

import structlog
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenPayload, UserContext, UserRole
from app.auth.service import AuthService
from app.campaigns.models import User
from app.config import get_settings
from app.shared.database import get_db_session
from app.shared.exceptions import AuthenticationError, AuthorizationError

logger = structlog.get_logger(__name__)
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
    auth_service = AuthService()
    
    return await auth_service.validate_token(token)


async def get_current_user(
    token: Annotated[TokenPayload, Depends(get_token_payload)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserContext:
    """Get current user from token, creating user record on first login."""
    # Look up user by OIDC subject
    result = await db.execute(
        select(User).where(User.oidc_sub == token.sub)
    )
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
        user_level = self._role_hierarchy.get(user.role, -1)
        required_level = self._role_hierarchy.get(self.minimum_role, 999)

        if user_level < required_level:
            # Log denied access attempt
            logger.warning(
                "Access denied - insufficient role",
                user_id=str(user.id),
                user_role=user.role.value,
                required_role=self.minimum_role.value,
                endpoint=str(request.url.path),
                method=request.method,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            raise AuthorizationError(
                message=f"Role '{self.minimum_role.value}' or higher required",
                required_role=self.minimum_role.value,
            )

        return user


# Pre-configured role dependencies for common use cases
require_viewer = RequireRole(UserRole.VIEWER)
require_campaign_manager = RequireRole(UserRole.CAMPAIGN_MANAGER)
require_admin = RequireRole(UserRole.ADMIN)

# Type aliases for cleaner route signatures
ViewerUser = Annotated[UserContext, Depends(require_viewer)]
CampaignManagerUser = Annotated[UserContext, Depends(require_campaign_manager)]
AdminUser = Annotated[UserContext, Depends(require_admin)]


def log_access_attempt(
    user: UserContext,
    endpoint: str,
    method: str,
    granted: bool,
    required_role: UserRole | None = None,
) -> None:
    """Log access attempt for audit trail."""
    log_data = {
        "user_id": str(user.id),
        "oidc_sub": user.oidc_sub,
        "user_role": user.role.value,
        "endpoint": endpoint,
        "method": method,
        "access_granted": granted,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if required_role:
        log_data["required_role"] = required_role.value

    if granted:
        logger.info("Access granted", **log_data)
    else:
        logger.warning("Access denied", **log_data)