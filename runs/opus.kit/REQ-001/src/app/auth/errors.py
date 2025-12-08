"""Authentication and authorization error definitions."""

from __future__ import annotations


class AuthError(Exception):
    """Base authentication/authorization error."""

    def __init__(self, message: str, code: str = "AUTH_ERROR") -> None:
        """Initialize auth error."""
        self.message = message
        self.code = code
        super().__init__(message)


class AuthenticationError(AuthError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize authentication error."""
        super().__init__(message, "AUTHENTICATION_FAILED")


class AuthorizationError(AuthError):
    """Authorization failed - insufficient permissions."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        """Initialize authorization error."""
        super().__init__(message, "AUTHORIZATION_FAILED")


class TokenValidationError(AuthError):
    """Token validation failed."""

    def __init__(self, message: str = "Invalid token") -> None:
        """Initialize token validation error."""
        super().__init__(message, "TOKEN_INVALID")


class TokenExpiredError(AuthError):
    """Token has expired."""

    def __init__(self, message: str = "Token expired") -> None:
        """Initialize token expired error."""
        super().__init__(message, "TOKEN_EXPIRED")


class OIDCConfigurationError(AuthError):
    """OIDC configuration error."""

    def __init__(self, message: str = "OIDC configuration error") -> None:
        """Initialize OIDC configuration error."""
        super().__init__(message, "OIDC_CONFIG_ERROR")


class UserNotFoundError(AuthError):
    """User not found."""

    def __init__(self, message: str = "User not found") -> None:
        """Initialize user not found error."""
        super().__init__(message, "USER_NOT_FOUND")