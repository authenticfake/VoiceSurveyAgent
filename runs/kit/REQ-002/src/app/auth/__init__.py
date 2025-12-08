"""
Authentication module for OIDC integration.

Provides OIDC authorization code flow, JWT validation, and user management.
"""

from app.auth.schemas import (
    OIDCConfig,
    TokenPayload,
    TokenResponse,
    UserContext,
    UserRole,
)
from app.auth.service import AuthService

__all__ = [
    "AuthService",
    "OIDCConfig",
    "TokenPayload",
    "TokenResponse",
    "UserContext",
    "UserRole",
]