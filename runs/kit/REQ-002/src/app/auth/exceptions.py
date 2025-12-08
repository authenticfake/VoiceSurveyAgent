"""
Authentication exceptions.

Custom exceptions for authentication and authorization errors.
"""

from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """Base authentication error."""

    def __init__(
        self,
        detail: str = "Authentication failed",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers or {"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""

    def __init__(self, detail: str = "Invalid or malformed token") -> None:
        super().__init__(detail=detail)


class ExpiredTokenError(AuthenticationError):
    """Raised when JWT token has expired."""

    def __init__(self, detail: str = "Token has expired") -> None:
        super().__init__(detail=detail)


class MissingTokenError(AuthenticationError):
    """Raised when no token is provided."""

    def __init__(self, detail: str = "Authentication token required") -> None:
        super().__init__(detail=detail)


class OIDCError(AuthenticationError):
    """Raised when OIDC flow fails."""

    def __init__(self, detail: str = "OIDC authentication failed") -> None:
        super().__init__(detail=detail)


class InvalidStateError(AuthenticationError):
    """Raised when CSRF state validation fails."""

    def __init__(self, detail: str = "Invalid state parameter") -> None:
        super().__init__(detail=detail)