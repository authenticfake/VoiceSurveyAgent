"""
Authentication module for OIDC integration and JWT handling.

REQ-002: OIDC authentication integration
"""
from __future__ import annotations

from pkgutil import extend_path

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

__path__ = extend_path(__path__, __name__)

__all__ = [
    "AuthCallbackRequest",
    "AuthCallbackResponse",
    "AuthService",
    "LoginResponse",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "TokenPayload",
    "UserProfile",
    "AuthMiddleware",
    "get_current_user",
]


def __getattr__(name: str):
    # Lazy re-export to avoid importing middleware on package import
    if name in {"AuthMiddleware", "get_current_user"}:
        from .middleware import AuthMiddleware, get_current_user

        return {"AuthMiddleware": AuthMiddleware, "get_current_user": get_current_user}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
