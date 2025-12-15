"""
Contact management module.

REQ-005: Campaign validation service (contact repository protocol)
REQ-006: Contact CSV upload and parsing (future)
"""

from app.contacts.repository import ContactRepository

__all__ = [
    "ContactRepository",
]