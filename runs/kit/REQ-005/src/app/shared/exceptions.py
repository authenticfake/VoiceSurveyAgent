"""
Custom exceptions for the application.

REQ-002: OIDC authentication integration
REQ-005: Campaign validation service (ValidationError extended)
"""

from typing import Any


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "APP_ERROR") -> None:
        """Initialize error.

        Args:
            message: Error message.
            code: Error code.
        """
        self.message = message
        self.code = code
        super().__init__(message)


class AuthenticationError(AppError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize error."""
        super().__init__(message, "AUTHENTICATION_ERROR")


class InvalidTokenError(AppError):
    """Invalid token provided."""

    def __init__(self, message: str = "Invalid token") -> None:
        """Initialize error."""
        super().__init__(message, "INVALID_TOKEN")


class TokenExpiredError(AppError):
    """Token has expired."""

    def __init__(self, message: str = "Token expired") -> None:
        """Initialize error."""
        super().__init__(message, "TOKEN_EXPIRED")


class OIDCError(AppError):
    """OIDC provider error."""

    def __init__(self, message: str = "OIDC error") -> None:
        """Initialize error."""
        super().__init__(message, "OIDC_ERROR")


class UserNotFoundError(AppError):
    """User not found."""

    def __init__(self, message: str = "User not found") -> None:
        """Initialize error."""
        super().__init__(message, "USER_NOT_FOUND")


class ValidationError(AppError):
    """Validation error with field-level details."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: str | None = None,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message.
            field: Field that failed validation.
            details: List of validation error details.
        """
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
        self.details = details or []


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        """Initialize error."""
        super().__init__(message, "NOT_FOUND")


class ConflictError(AppError):
    """Resource conflict."""

    def __init__(self, message: str = "Resource conflict") -> None:
        """Initialize error."""
        super().__init__(message, "CONFLICT")


class ForbiddenError(AppError):
    """Access forbidden."""

    def __init__(self, message: str = "Access forbidden") -> None:
        """Initialize error."""
        super().__init__(message, "FORBIDDEN")