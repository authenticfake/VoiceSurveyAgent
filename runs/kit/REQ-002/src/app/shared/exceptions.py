"""
Custom exception classes for the application.

REQ-002: OIDC authentication integration
"""

from typing import Any


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize application exception.

        Args:
            message: Human-readable error message.
            code: Machine-readable error code.
            details: Additional error details.
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTH_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details)


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, "TOKEN_EXPIRED", details)


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid."""

    def __init__(
        self,
        message: str = "Invalid token",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, "INVALID_TOKEN", details)


class OIDCError(AuthenticationError):
    """Raised when OIDC operations fail."""

    def __init__(
        self,
        message: str = "OIDC operation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, "OIDC_ERROR", details)


class UserNotFoundError(AppException):
    """Raised when a user is not found."""

    def __init__(
        self,
        message: str = "User not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, "USER_NOT_FOUND", details)