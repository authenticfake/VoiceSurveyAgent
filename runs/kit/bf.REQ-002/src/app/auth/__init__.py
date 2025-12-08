"""Authentication module for OIDC and JWT handling."""

from app.auth.models import User, UserRole
from app.auth.schemas import (
    AuthCallbackRequest,
    AuthCallbackResponse,
    TokenResponse,
    UserProfile,
    UserCreate,
    UserUpdate,
)
from app.auth.service import AuthService
from app.auth.middleware import AuthMiddleware, get_current_user

__all__ = [
    "User",
    "UserRole",
    "AuthCallbackRequest",
    "AuthCallbackResponse",
    "TokenResponse",
    "UserProfile",
    "UserCreate",
    "UserUpdate",
    "AuthService",
    "AuthMiddleware",
    "get_current_user",
]