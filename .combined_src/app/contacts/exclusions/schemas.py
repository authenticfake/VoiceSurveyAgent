"""
Pydantic schemas for exclusion list management.

REQ-007: Exclusion list management
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.contacts.exclusions.models import ExclusionSource


class ExclusionEntryResponse(BaseModel):
    """Response schema for a single exclusion entry."""

    id: UUID
    phone_number: str
    reason: str | None
    source: ExclusionSource
    created_at: datetime

    model_config = {"from_attributes": True}


class ExclusionListResponse(BaseModel):
    """Response schema for paginated exclusion list."""

    items: list[ExclusionEntryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExclusionCreateRequest(BaseModel):
    """Request schema for creating a single exclusion entry."""

    phone_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Phone number in E.164 format",
    )
    reason: str | None = Field(
        None,
        max_length=500,
        description="Optional reason for exclusion",
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate and normalize phone number."""
        v = v.strip()
        if not v:
            raise ValueError("Phone number cannot be empty")
        # Basic E.164 validation: starts with + and contains only digits after
        if v.startswith("+"):
            digits = v[1:]
            if not digits.isdigit():
                raise ValueError("Phone number must contain only digits after +")
            if len(digits) < 7 or len(digits) > 15:
                raise ValueError("Phone number must be 7-15 digits")
        else:
            # Allow numbers without + prefix for flexibility
            if not v.replace("-", "").replace(" ", "").isdigit():
                raise ValueError("Phone number must contain only digits")
        return v


class ExclusionImportError(BaseModel):
    """Error details for a single row during CSV import."""

    line_number: int
    phone_number: str | None
    error: str


class ExclusionImportResponse(BaseModel):
    """Response schema for CSV import operation."""

    accepted_count: int
    rejected_count: int
    duplicate_count: int
    errors: list[ExclusionImportError]