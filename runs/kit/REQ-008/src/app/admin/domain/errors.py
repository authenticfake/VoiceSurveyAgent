from __future__ import annotations


class AdminConfigError(Exception):
    """Base error for admin configuration operations."""


class ProviderConfigurationNotFoundError(AdminConfigError):
    """Raised when no provider configuration record exists."""


class EmailTemplateNotFoundError(AdminConfigError):
    """Raised when the requested email template cannot be found."""