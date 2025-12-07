from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.contacts.domain.enums import ContactLanguage, ContactState


@dataclass(frozen=True)
class ContactCsvRow:
    external_contact_id: Optional[str]
    phone_number: str
    email: Optional[str]
    preferred_language: ContactLanguage
    has_prior_consent: bool
    do_not_call: bool


@dataclass(frozen=True)
class ContactCandidate:
    external_contact_id: Optional[str]
    phone_number: str
    email: Optional[str]
    preferred_language: ContactLanguage
    has_prior_consent: bool
    do_not_call: bool
    state: ContactState