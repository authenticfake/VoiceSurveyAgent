"""
Pydantic schemas for campaign API.

REQ-004: Campaign CRUD API
REQ-005: Campaign validation service (extended with validation error schema)
"""

from datetime import datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.campaigns.models import CampaignLanguage, CampaignStatus, QuestionType


class QuestionSchema(BaseModel):
    """Schema for a survey question."""

    text: str = Field(..., min_length=1, max_length=2000, description="Question text")
    type: QuestionType = Field(..., description="Answer type for the question")


class CampaignBase(BaseModel):
    """Base schema for campaign data."""

    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    description: str | None = Field(None, max_length=5000, description="Campaign description")
    language: CampaignLanguage = Field(
        default=CampaignLanguage.EN,
        description="Target language for the campaign",
    )
    intro_script: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Introduction script including identity, purpose, and consent",
    )
    question_1_text: str = Field(..., min_length=1, max_length=2000)
    question_1_type: QuestionType = Field(default=QuestionType.FREE_TEXT)
    question_2_text: str = Field(..., min_length=1, max_length=2000)
    question_2_type: QuestionType = Field(default=QuestionType.FREE_TEXT)
    question_3_text: str = Field(..., min_length=1, max_length=2000)
    question_3_type: QuestionType = Field(default=QuestionType.FREE_TEXT)
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum call attempts per contact (1-5)",
    )
    retry_interval_minutes: int = Field(
        default=60,
        ge=1,
        description="Minimum minutes between retry attempts",
    )
    allowed_call_start_local: time = Field(
        default=time(9, 0),
        description="Earliest local time to start calls",
    )
    allowed_call_end_local: time = Field(
        default=time(20, 0),
        description="Latest local time to start calls",
    )


class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign."""

    email_completed_template_id: UUID | None = Field(
        None,
        description="Email template for completed surveys",
    )
    email_refused_template_id: UUID | None = Field(
        None,
        description="Email template for refused surveys",
    )
    email_not_reached_template_id: UUID | None = Field(
        None,
        description="Email template for not reached contacts",
    )

    @model_validator(mode="after")
    def validate_time_window(self) -> "CampaignCreate":
        """Validate that call start time is before end time."""
        if self.allowed_call_start_local >= self.allowed_call_end_local:
            raise ValueError("Call start time must be before end time")
        return self


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    language: CampaignLanguage | None = None
    intro_script: str | None = Field(None, min_length=1, max_length=5000)
    question_1_text: str | None = Field(None, min_length=1, max_length=2000)
    question_1_type: QuestionType | None = None
    question_2_text: str | None = Field(None, min_length=1, max_length=2000)
    question_2_type: QuestionType | None = None
    question_3_text: str | None = Field(None, min_length=1, max_length=2000)
    question_3_type: QuestionType | None = None
    max_attempts: int | None = Field(None, ge=1, le=5)
    retry_interval_minutes: int | None = Field(None, ge=1)
    allowed_call_start_local: time | None = None
    allowed_call_end_local: time | None = None
    email_completed_template_id: UUID | None = None
    email_refused_template_id: UUID | None = None
    email_not_reached_template_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CampaignResponse(BaseModel):
    """Schema for campaign response."""

    id: UUID
    name: str
    description: str | None
    status: CampaignStatus
    language: CampaignLanguage
    intro_script: str
    question_1_text: str
    question_1_type: QuestionType
    question_2_text: str
    question_2_type: QuestionType
    question_3_text: str
    question_3_type: QuestionType
    max_attempts: int
    retry_interval_minutes: int
    allowed_call_start_local: time
    allowed_call_end_local: time
    email_completed_template_id: UUID | None
    email_refused_template_id: UUID | None
    email_not_reached_template_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list response."""

    items: list[CampaignResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class CampaignStatusTransition(BaseModel):
    """Schema for campaign status transition request."""

    status: CampaignStatus = Field(..., description="Target status")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: CampaignStatus) -> CampaignStatus:
        """Validate that status is a valid transition target."""
        # Actual transition validation happens in service layer
        return v


class ValidationErrorDetail(BaseModel):
    """Schema for a single validation error."""

    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Error message")


class ValidationErrorResponse(BaseModel):
    """Schema for validation error response."""

    code: str = Field(default="VALIDATION_FAILED", description="Error code")
    message: str = Field(..., description="Error message")
    errors: list[ValidationErrorDetail] = Field(
        default_factory=list,
        description="List of validation errors",
    )

    model_config = ConfigDict(from_attributes=True)