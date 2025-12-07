from __future__ import annotations

from enum import Enum


class AuthErrorCode(str, Enum):
    INVALID_TOKEN = "invalid_token"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    OIDC_EXCHANGE_FAILED = "oidc_exchange_failed"
    INVALID_CONFIGURATION = "invalid_configuration"


class AuthError(Exception):
    """Domain-level exception for auth failures."""

    def __init__(self, code: AuthErrorCode, description: str):
        self.code = code
        self.description = description
        super().__init__(description)