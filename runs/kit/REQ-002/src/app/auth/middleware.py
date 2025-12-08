"""
Authentication middleware.

JWT validation middleware for FastAPI requests.
"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.exceptions import InvalidTokenError, MissingTokenError
from app.auth.schemas import UserContext, UserRole
from app.auth.service import AuthService
from app.config import get_settings
from app.shared.database import DbSession
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """Middleware for JWT authentication."""

    def __init__(self) -> None:
        """Initialize auth middleware."""
        self._auth_service: AuthService | None = None

    async def _get_auth_service(self, db: DbSession) -> AuthService:
        """Get or create auth service instance."""
        if self._auth_service is None:
            self._auth_service = AuthService(settings=settings, db_session=db)
            await self._auth_service.initialize()
        return self._auth_service

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        db: DbSession = None,  # type: ignore[assignment]
    ) -> UserContext:
        """
        Validate JWT token and return user context.

        Args:
            request: FastAPI request
            credentials: HTTP Bearer credentials
            db: Database session

        Returns:
            Authenticated user context

        Raises:
            MissingTokenError: If no token provided
            InvalidTokenError: If token is invalid
        """
        if credentials is None:
            logger.warning(
                "Missing authentication token",
                extra={"path": request.url.path},
            )
            raise MissingTokenError()

        token = credentials.credentials
        auth_service = await self._get_auth_service(db)

        try:
            # Validate token
            token_payload = await auth_service.validate_token(token)

            # Get user from database
            user = await auth_service.get_or_create_user(token_payload)

            user_context = UserContext(
                id=user.id,
                oidc_sub=user.oidc_sub,
                email=user.email,
                name=user.name,
                role=UserRole(user.role),
            )

            # Add user context to request state for logging
            request.state.user_id = str(user.id)
            request.state.user_role = user.role

            logger.debug(
                "Request authenticated",
                extra={
                    "user_id": str(user.id),
                    "path": request.url.path,
                },
            )

            return user_context

        except Exception as e:
            logger.warning(
                "Authentication failed",
                extra={
                    "path": request.url.path,
                    "error": str(e),
                },
            )
            raise


# Create singleton middleware instance
_auth_middleware = AuthMiddleware()


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: DbSession,
) -> UserContext:
    """
    Dependency to get current authenticated user.

    Usage:
        @router.get("/protected")
        async def protected_route(user: CurrentUser):
            return {"user_id": str(user.id)}
    """
    return await _auth_middleware(request, credentials, db)


# Type alias for dependency injection
CurrentUser = Annotated[UserContext, Depends(get_current_user)]