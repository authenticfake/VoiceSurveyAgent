from __future__ import annotations


class ContactCsvValidationError(Exception):
    """Raised when the uploaded CSV is malformed."""


class ContactImportFailedError(Exception):
    """Raised when contacts cannot be persisted."""