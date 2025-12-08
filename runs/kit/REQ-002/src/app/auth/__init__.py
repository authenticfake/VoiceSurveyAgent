"""
Authentication module for OIDC integration.

This module provides OIDC authorization code flow authentication,
JWT token validation, and user session management.
"""

from app.auth.middleware import AuthMiddleware, get_current_user
from app.auth.router import router as auth_router
from app.auth.service import AuthService

__all__ = [
    "AuthMiddleware",
    "AuthService",
    "auth_router",
    "get_current_user",
]