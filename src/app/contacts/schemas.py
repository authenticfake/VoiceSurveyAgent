"""
Pydantic schemas for contact management.

REQ-006: Contact CSV upload and parsing
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.contacts.models import ContactLanguage, ContactOutcome, ContactState


class ContactBase(BaseModel):
    """Base contact schema with common fields."""

    external_contact_id: str | None = Field(
        default=None,
        max_length=255,
        description="External reference ID for the contact",
    )
    name: str | None = Field(
        default=None,
        max_length=255,
        description="Optional display name (e.g., restaurant/owner)",
    )
    phone_number: str = Field(
        ...,
        max_length=50,
        description="Phone number in E.164 format",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Contact email address",
    )
    preferred_language: ContactLanguage = Field(
        default=ContactLanguage.AUTO,
        description="Preferred language for the contact",
    )
    has_prior_consent: bool = Field(
        default=False,
        description="Whether contact has prior consent",
    )
    do_not_call: bool = Field(
        default=False,
        description="Do not call flag",
    )


class ContactCreate(ContactBase):
    """Schema for creating a contact."""

    pass

class ContactUpdateFlags(BaseModel):
    """Schema for updating consent / do-not-call flags.

    This is intentionally minimal to keep PATCH semantics clear and stable.
    """

    has_prior_consent: bool | None = Field(
        default=None,
        description="Update prior consent flag (omit to leave unchanged)",
    )
    do_not_call: bool | None = Field(
        default=None,
        description="Update do-not-call flag (omit to leave unchanged)",
    )


class ContactResponse(BaseModel):
    """Schema for contact response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    external_contact_id: str | None
    phone_number: str
    email: str | None
    preferred_language: ContactLanguage
    has_prior_consent: bool
    do_not_call: bool
    state: ContactState
    attempts_count: int
    last_attempt_at: datetime | None
    last_outcome: ContactOutcome | None
    created_at: datetime
    updated_at: datetime


class ContactListResponse(BaseModel):
    """Schema for paginated contact list response."""

    items: list[ContactResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CSVRowError(BaseModel):
    """Schema for CSV row validation error."""

    line_number: int = Field(..., description="Line number in the CSV file (1-indexed)")
    field: str | None = Field(default=None, description="Field that caused the error")
    error: str = Field(..., description="Error description")
    value: str | None = Field(default=None, description="Invalid value")


class CSVUploadResponse(BaseModel):
    """Schema for CSV upload response."""

    accepted_count: int = Field(..., description="Number of valid rows accepted")
    rejected_count: int = Field(..., description="Number of invalid rows rejected")
    total_rows: int = Field(..., description="Total rows processed")
    errors: list[CSVRowError] = Field(
        default_factory=list,
        description="List of validation errors",
    )
    acceptance_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of rows accepted (0.0 to 1.0)",
    )

    @field_validator("acceptance_rate", mode="before")
    @classmethod
    def calculate_acceptance_rate(cls, v: float, info) -> float:
        """Ensure acceptance rate is properly bounded."""
        return max(0.0, min(1.0, v))


class CSVRowData(BaseModel):
    """Schema for parsed CSV row data."""

    external_contact_id: str | None = None
    name: str | None = None
    phone_number: str
    email: str | None = None
    language: ContactLanguage = ContactLanguage.AUTO
    has_prior_consent: bool = False
    do_not_call: bool = False