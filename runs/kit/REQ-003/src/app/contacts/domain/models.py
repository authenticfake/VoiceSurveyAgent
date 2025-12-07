from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.contacts.domain.enums import ContactLanguage, ContactState


@dataclass(frozen=True)
class ContactRecord:
    id: UUID
    campaign_id: UUID
    external_contact_id: Optional[str]
    phone_number: str
    email: Optional[str]
    preferred_language: ContactLanguage
    state: ContactState
    attempts_count: int
    last_attempt_at: Optional[datetime]
    last_outcome: Optional[str]
    has_prior_consent: bool
    do_not_call: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ContactListPage:
    contacts: List[ContactRecord]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class ContactImportErrorDetail:
    line_number: int
    message: str


@dataclass(frozen=True)
class ContactImportResult:
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    errors: List[ContactImportErrorDetail]