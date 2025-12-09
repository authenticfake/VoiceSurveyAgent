"""
Contact management module.

REQ-005: Campaign validation service (contact repository protocol)
REQ-006: Contact CSV upload and parsing
REQ-010: Telephony webhook handler (Contact model with state)
"""

from app.contacts.models import Contact, ContactState
from app.contacts.repository import ContactRepository

__all__ = [
    "Contact",
    "ContactState",
    "ContactRepository",
]