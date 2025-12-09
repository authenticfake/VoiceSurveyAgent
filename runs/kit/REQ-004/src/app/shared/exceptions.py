"""
Custom exceptions for the application.

REQ-002: OIDC authentication integration
REQ-003: RBAC authorization middleware
REQ-004: Campaign CRUD API
"""

from typing import Any
from uuid import UUID


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

    def __init__(self, message: str) -> None:
        super().__init__(message, "VALIDATION_ERROR")