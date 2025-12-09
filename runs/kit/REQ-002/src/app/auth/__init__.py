"""Authentication module for OIDC integration and JWT validation."""
from app.auth.config import AuthConfig
from app.auth.dependencies import get_current_user, get_optional_user
from app.auth.middleware import JWTAuthMiddleware
from app.auth.models import TokenPayload, UserInfo
from app.auth.oidc_client import OIDCClient
from app.auth.router import router as auth_router
from app.auth.service import AuthService

__all__ = [
    "AuthConfig",
    "AuthService",
    "JWTAuthMiddleware",
    "OIDCClient",
    "TokenPayload",
    "UserInfo",
    "auth_router",
    "get_current_user",
    "get_optional_user",
]