from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.contacts.domain.enums import ContactLanguage, ContactState
from app.contacts.domain.models import ContactRecord


class ContactUploadErrorModel(BaseModel):
    line_number: int
    message: str


class ContactUploadResponse(BaseModel):
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    errors: List[ContactUploadErrorModel]


class ContactListItem(BaseModel):
    id: UUID
    campaign_id: UUID
    external_contact_id: Optional[str] = None
    phone_number: str
    email: Optional[str] = None
    preferred_language: ContactLanguage
    state: ContactState
    attempts_count: int
    last_attempt_at: Optional[datetime] = None
    last_outcome: Optional[str] = None
    has_prior_consent: bool
    do_not_call: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, record: ContactRecord) -> "ContactListItem":
        return cls(**record.__dict__)


class PaginationMetadata(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)


class ContactListResponse(BaseModel):
    data: List[ContactListItem]
    pagination: PaginationMetadata