"""
Custom exception classes for the application.
"""

from typing import Any, Optional

from uuid import UUID

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

# =============================================================================
# REQ-004: Campaign domain exceptions (promotion-safe: live in shared)
# =============================================================================

class CampaignNotFoundError(AppException):
    """Raised when a campaign is not found."""

    def __init__(self, campaign_id: UUID, message: str | None = None) -> None:
        self.campaign_id = campaign_id
        super().__init__(
            message or f"Campaign not found: {campaign_id}",
            "CAMPAIGN_NOT_FOUND",
            {"campaign_id": str(campaign_id)},
        )


class InvalidStatusTransitionError(AppException):
    """Raised when a campaign status transition is invalid."""

    def __init__(
        self,
        current_status: Any,
        target_status: Any,
        valid_transitions: set[Any],
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status
        self.valid_transitions = valid_transitions

        def _val(x: Any) -> str:
            return getattr(x, "value", str(x))

        valid_list = sorted({_val(v) for v in valid_transitions})
        msg = (
            f"Cannot transition from '{_val(current_status)}' to '{_val(target_status)}'. "
            f"Valid transitions: {', '.join(valid_list)}"
        )

        super().__init__(
            msg,
            "INVALID_STATUS_TRANSITION",
            {
                "current_status": _val(current_status),
                "target_status": _val(target_status),
                "valid_transitions": valid_list,
            },
        )


class ValidationError(AppException):
    """Raised when business validation fails (distinct from pydantic ValidationError)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, "VALIDATION_ERROR", details)


class AppError(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, code: str = "APP_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


# Authentication errors
class AuthenticationError(AppError):
    """Base authentication error."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, "AUTHENTICATION_ERROR")


class InvalidTokenError(AuthenticationError):
    """Invalid or malformed token."""

    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message)
        self.code = "INVALID_TOKEN"


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    def __init__(self, message: str = "Token has expired") -> None:
        super().__init__(message)
        self.code = "TOKEN_EXPIRED"


class OIDCError(AuthenticationError):
    """OIDC provider error."""

    def __init__(self, message: str = "OIDC error") -> None:
        super().__init__(message)
        self.code = "OIDC_ERROR"


class UserNotFoundError(AppError):
    """User not found."""

    def __init__(self, identifier: str | UUID) -> None:
        super().__init__(f"User not found: {identifier}", "USER_NOT_FOUND")
        self.identifier = identifier


# Authorization errors
class AuthorizationError(AppError):
    """Base authorization error."""

    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message, "AUTHORIZATION_ERROR")


class InsufficientPermissionsError(AuthorizationError):
    """User lacks required permissions."""

    def __init__(
        self,
        required_role: str,
        current_role: str,
        message: str | None = None,
    ) -> None:
        msg = message or f"Role '{required_role}' or higher required, current role: '{current_role}'"
        super().__init__(msg)
        self.code = "INSUFFICIENT_PERMISSIONS"
        self.required_role = required_role
        self.current_role = current_role


# Campaign errors
class CampaignNotFoundError(AppError):
    """Campaign not found."""

    def __init__(self, campaign_id: UUID) -> None:
        super().__init__(
            f"Campaign with ID {campaign_id} not found",
            "CAMPAIGN_NOT_FOUND",
        )
        self.campaign_id = campaign_id


class InvalidStatusTransitionError(AppError):
    """Invalid campaign status transition."""

    def __init__(
        self,
        current_status: Any,
        target_status: Any,
        valid_transitions: set[Any],
    ) -> None:
        valid_str = ", ".join(s.value for s in valid_transitions) if valid_transitions else "none"
        super().__init__(
            f"Cannot transition from '{current_status.value}' to '{target_status.value}'. "
            f"Valid transitions: {valid_str}",
            "INVALID_STATUS_TRANSITION",
        )
        self.current_status = current_status
        self.target_status = target_status
        self.valid_transitions = valid_transitions


class ValidationError(AppError):
    """Validation error."""
    def __init__(
        self,
        message: str = "Validation failed",
        field: str | None = None,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message, "VALIDATION_ERROR")
        
        self.field = field

        self.details = details or []

class InvalidTokenError(AppError):
    # compat: accetta keyword args
    def __init__(self, message: str = "Invalid token", details: Optional[dict[str, Any]] = None, **_: Any) -> None:
        super().__init__(message=message, code=details)

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

class TokenExpiredError(AppError):
    def __init__(self, message: str = "Token expired", details: Optional[dict[str, Any]] = None, **_: Any) -> None:
        super().__init__(message=message, code=details)