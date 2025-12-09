"""FastAPI dependencies for authentication."""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config import AuthConfig
from app.auth.models import TokenPayload
from app.auth.service import AuthService
from app.shared.database import get_db
from app.shared.models.user import User

logger = logging.getLogger(__name__)

def get_auth_config() -> AuthConfig:
    """Get authentication configuration.
    
    Returns:
        Authentication configuration from environment
    """
    return AuthConfig.from_env()

def get_auth_service(
    config: AuthConfig = Depends(get_auth_config)
) -> AuthService:
    """Get authentication service.
    
    Args:
        config: Authentication configuration
        
    Returns:
        Configured authentication service
    """
    return AuthService.create(config)

def get_token_payload(request: Request) -> TokenPayload:
    """Extract validated token payload from request.
    
    Args:
        request: FastAPI request
        
    Returns:
        Token payload from middleware
        
    Raises:
        HTTPException: If token payload not found
    """
    payload = getattr(request.state, "token_payload", None)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return payload

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current authenticated user.
    
    Args:
        request: FastAPI request
        db: Database session
        auth_service: Authentication service
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If user not found or not authenticated
    """
    payload = get_token_payload(request)
    
    user = await auth_service.get_user_by_sub(db, payload.sub)
    if not user:
        # User authenticated but not in database
        # This shouldn't happen if login flow is used
        logger.warning(
            "Authenticated user not found in database: %s",
            payload.sub
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user

async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise.
    
    Args:
        request: FastAPI request
        db: Database session
        auth_service: Authentication service
        
    Returns:
        Current user or None
    """
    payload = getattr(request.state, "token_payload", None)
    if not payload:
        return None
    
    return await auth_service.get_user_by_sub(db, payload.sub)