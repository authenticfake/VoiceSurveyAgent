"""Authentication middleware for FastAPI."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import JWTHandler
from app.auth.models import User
from app.auth.repository import UserRepository
from app.config import get_settings
from app.shared.database import get_db_session
from app.shared.exceptions import TokenExpiredError, TokenInvalidError
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Security scheme for OpenAPI
security = HTTPBearer(auto_error=False)

class AuthMiddleware:
    """Middleware for validating JWT tokens."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._jwt_handler = JWTHandler(self._settings)

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        """Validate token and return current user."""
        if credentials is None:
            logger.warning("No authorization header provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = self._jwt_handler.validate_access_token(credentials.credentials)
            user_id = payload["sub"]

            # Get user from database
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if user is None:
                logger.warning(f"User not found: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user

        except TokenExpiredError:
            logger.warning("Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except TokenInvalidError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

# Dependency for getting current user
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Get the current authenticated user."""
    middleware = AuthMiddleware()
    # Create a mock request since we're using this as a dependency
    return await middleware(
        request=None,  # type: ignore[arg-type]
        credentials=credentials,
        session=session,
    )

# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]