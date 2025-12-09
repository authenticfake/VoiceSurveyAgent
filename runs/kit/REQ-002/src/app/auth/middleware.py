"""
Authentication middleware for FastAPI.

REQ-002: OIDC authentication integration
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import JWTService
from app.auth.schemas import TokenPayload
from app.shared.exceptions import InvalidTokenError, TokenExpiredError
from app.shared.logging import correlation_id_var, get_logger

logger = get_logger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """Middleware for JWT authentication."""

    def __init__(self) -> None:
        """Initialize auth middleware."""
        self._jwt_service = JWTService()

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> TokenPayload:
        """Validate JWT token from Authorization header.

        Args:
            request: FastAPI request object.
            credentials: Bearer token credentials.

        Returns:
            Validated token payload.

        Raises:
            HTTPException: If authentication fails.
        """
        if credentials is None:
            logger.warning(
                "Missing authorization header",
                extra={"path": request.url.path},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "MISSING_TOKEN",
                    "message": "Authorization header required",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = self._jwt_service.verify_token(credentials.credentials)

            if payload.type != "access":
                raise InvalidTokenError(message="Invalid token type")

            # Set correlation context for logging
            if payload.user_id:
                correlation_id_var.set(str(payload.user_id))

            return payload

        except TokenExpiredError:
            logger.warning(
                "Token expired",
                extra={"path": request.url.path},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "TOKEN_EXPIRED",
                    "message": "Token has expired",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        except InvalidTokenError as e:
            logger.warning(
                "Invalid token",
                extra={"path": request.url.path, "error": e.message},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "INVALID_TOKEN",
                    "message": e.message,
                },
                headers={"WWW-Authenticate": "Bearer"},
            )


# Dependency for getting current user from token
auth_middleware = AuthMiddleware()


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ] = None,
) -> TokenPayload:
    """FastAPI dependency for authenticated routes.

    Args:
        request: FastAPI request object.
        credentials: Bearer token credentials.

    Returns:
        Validated token payload with user information.

    Raises:
        HTTPException: If authentication fails.
    """
    return await auth_middleware(request, credentials)


# Type alias for dependency injection
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]