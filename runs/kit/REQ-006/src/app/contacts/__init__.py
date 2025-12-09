"""
Contact management module.

REQ-005: Campaign validation service (contact repository protocol)
REQ-006: Contact CSV upload and parsing
"""

from app.contacts.models import Contact, ContactState, ContactLanguage, ContactOutcome
from app.contacts.repository import ContactRepository
from app.contacts.schemas import (
    ContactResponse,
    ContactListResponse,
    CSVUploadResponse,
    CSVRowError,
)
from app.contacts.service import ContactService
from app.contacts.router import router

__all__ = [
    "Contact",
    "ContactState",
    "ContactLanguage",
    "ContactOutcome",
    "ContactRepository",
    "ContactService",
    "ContactResponse",
    "ContactListResponse",
    "CSVUploadResponse",
    "CSVRowError",
    "router",
]