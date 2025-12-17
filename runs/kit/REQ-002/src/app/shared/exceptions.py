"""
Custom exception classes for the application.

REQ-002: OIDC authentication integration
"""

from typing import Any

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
