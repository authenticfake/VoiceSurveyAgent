"""
Authentication module for OIDC integration and JWT handling.

REQ-002: OIDC authentication integration
"""

from app.auth.schemas import (
    AuthCallbackRequest,
    AuthCallbackResponse,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TokenPayload,
    UserProfile,
)
from app.auth.service import AuthService
from app.auth.middleware import AuthMiddleware, get_current_user

__all__ = [
    "AuthCallbackRequest",
    "AuthCallbackResponse",
    "AuthMiddleware",
    "AuthService",
    "LoginResponse",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "TokenPayload",
    "UserProfile",
    "get_current_user",
]