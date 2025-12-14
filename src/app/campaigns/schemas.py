"""
Pydantic schemas for campaign API.

REQ-004: Campaign CRUD API
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
    question_1_text: str = Field(..., min_length=1, max_length=2000, description="First question text")
    question_1_type: QuestionType = Field(..., description="First question answer type")
    question_2_text: str = Field(..., min_length=1, max_length=2000, description="Second question text")
    question_2_type: QuestionType = Field(..., description="Second question answer type")
    question_3_text: str = Field(..., min_length=1, max_length=2000, description="Third question text")
    question_3_type: QuestionType = Field(..., description="Third question answer type")
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
        ...,
        description="Earliest local time to start calls (HH:MM:SS)",
    )
    allowed_call_end_local: time = Field(
        ...,
        description="Latest local time to end calls (HH:MM:SS)",
    )
    email_completed_template_id: UUID | None = Field(
        None,
        description="Email template ID for completed surveys",
    )
    email_refused_template_id: UUID | None = Field(
        None,
        description="Email template ID for refused surveys",
    )
    email_not_reached_template_id: UUID | None = Field(
        None,
        description="Email template ID for not reached contacts",
    )

    @model_validator(mode="after")
    def validate_time_window(self) -> "CampaignBase":
        """Validate that call start time is before end time."""
        if self.allowed_call_start_local >= self.allowed_call_end_local:
            raise ValueError("allowed_call_start_local must be before allowed_call_end_local")
        return self


class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign."""

    pass


class CampaignUpdate(BaseModel):
    """Schema for updating an existing campaign.
    
    All fields are optional to support partial updates.
    """

    name: str | None = Field(None, min_length=1, max_length=255, description="Campaign name")
    description: str | None = Field(None, max_length=5000, description="Campaign description")
    language: CampaignLanguage | None = Field(None, description="Target language")
    intro_script: str | None = Field(None, min_length=1, max_length=5000, description="Introduction script")
    question_1_text: str | None = Field(None, min_length=1, max_length=2000, description="First question text")
    question_1_type: QuestionType | None = Field(None, description="First question answer type")
    question_2_text: str | None = Field(None, min_length=1, max_length=2000, description="Second question text")
    question_2_type: QuestionType | None = Field(None, description="Second question answer type")
    question_3_text: str | None = Field(None, min_length=1, max_length=2000, description="Third question text")
    question_3_type: QuestionType | None = Field(None, description="Third question answer type")
    max_attempts: int | None = Field(None, ge=1, le=5, description="Maximum call attempts")
    retry_interval_minutes: int | None = Field(None, ge=1, description="Retry interval in minutes")
    allowed_call_start_local: time | None = Field(None, description="Call window start time")
    allowed_call_end_local: time | None = Field(None, description="Call window end time")
    email_completed_template_id: UUID | None = Field(None, description="Completed email template ID")
    email_refused_template_id: UUID | None = Field(None, description="Refused email template ID")
    email_not_reached_template_id: UUID | None = Field(None, description="Not reached email template ID")

    @model_validator(mode="after")
    def validate_time_window_if_both_present(self) -> "CampaignUpdate":
        """Validate time window if both times are provided."""
        if (
            self.allowed_call_start_local is not None
            and self.allowed_call_end_local is not None
            and self.allowed_call_start_local >= self.allowed_call_end_local
        ):
            raise ValueError("allowed_call_start_local must be before allowed_call_end_local")
        return self


class CampaignStatusTransition(BaseModel):
    """Schema for campaign status transition request."""

    status: CampaignStatus = Field(..., description="Target status to transition to")


class CampaignResponse(BaseModel):
    """Schema for campaign response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Campaign ID")
    name: str = Field(..., description="Campaign name")
    description: str | None = Field(None, description="Campaign description")
    status: CampaignStatus = Field(..., description="Current campaign status")
    language: CampaignLanguage = Field(..., description="Target language")
    intro_script: str = Field(..., description="Introduction script")
    question_1_text: str = Field(..., description="First question text")
    question_1_type: QuestionType = Field(..., description="First question answer type")
    question_2_text: str = Field(..., description="Second question text")
    question_2_type: QuestionType = Field(..., description="Second question answer type")
    question_3_text: str = Field(..., description="Third question text")
    question_3_type: QuestionType = Field(..., description="Third question answer type")
    max_attempts: int = Field(..., description="Maximum call attempts")
    retry_interval_minutes: int = Field(..., description="Retry interval in minutes")
    allowed_call_start_local: time = Field(..., description="Call window start time")
    allowed_call_end_local: time = Field(..., description="Call window end time")
    email_completed_template_id: UUID | None = Field(None, description="Completed email template ID")
    email_refused_template_id: UUID | None = Field(None, description="Refused email template ID")
    email_not_reached_template_id: UUID | None = Field(None, description="Not reached email template ID")
    created_by_user_id: UUID = Field(..., description="Creator user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class CampaignListItem(BaseModel):
    """Schema for campaign list item (summary view)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Campaign ID")
    name: str = Field(..., description="Campaign name")
    description: str | None = Field(None, description="Campaign description")
    status: CampaignStatus = Field(..., description="Current campaign status")
    language: CampaignLanguage = Field(..., description="Target language")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list response."""

    items: list[CampaignListItem] = Field(..., description="List of campaigns")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class ErrorDetail(BaseModel):
    """Schema for error detail."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: str | None = Field(None, description="Field that caused the error")


class ErrorResponse(BaseModel):
    """Schema for error response."""

    detail: ErrorDetail = Field(..., description="Error details")