"""Custom exceptions for the application."""


class AppException(Exception):
    """Base application exception."""
    pass


class NotFoundError(AppException):
    """Resource not found exception."""
    pass


class ValidationError(AppException):
    """Validation error exception."""
    pass


class StateTransitionError(AppException):
    """Invalid state transition exception."""
    pass


class AuthenticationError(AppException):
    """Authentication failed exception."""
    pass


class AuthorizationError(AppException):
    """Authorization failed exception."""
    pass


class ExternalServiceError(AppException):
    """External service error exception."""
    pass