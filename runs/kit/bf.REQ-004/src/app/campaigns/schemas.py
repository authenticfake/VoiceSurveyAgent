"""
Pydantic schemas for campaign API.

Defines request/response models for campaign CRUD operations.
"""

from datetime import datetime, time
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

class CampaignStatus(str, Enum):
    """Campaign status enumeration."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CampaignLanguage(str, Enum):
    """Campaign language enumeration."""

    EN = "en"
    IT = "it"

class QuestionType(str, Enum):
    """Question type enumeration."""

    FREE_TEXT = "free_text"
    NUMERIC = "numeric"
    SCALE = "scale"

class QuestionConfig(BaseModel):
    """Question configuration schema."""

    text: str = Field(..., min_length=1, max_length=2000, description="Question text")
    type: QuestionType = Field(..., description="Question type")

class CampaignBase(BaseModel):
    """Base campaign schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    description: str | None = Field(None, max_length=5000, description="Campaign description")
    language: CampaignLanguage = Field(
        default=CampaignLanguage.EN,
        description="Campaign language",
    )
    intro_script: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Introduction script with consent wording",
    )
    question_1: QuestionConfig = Field(..., description="First survey question")
    question_2: QuestionConfig = Field(..., description="Second survey question")
    question_3: QuestionConfig = Field(..., description="Third survey question")
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum call attempts per contact",
    )
    retry_interval_minutes: int = Field(
        default=60,
        ge=1,
        description="Minimum minutes between retry attempts",
    )
    allowed_call_start_local: time = Field(
        default=time(9, 0),
        description="Earliest allowed call time (local)",
    )
    allowed_call_end_local: time = Field(
        default=time(20, 0),
        description="Latest allowed call time (local)",
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

    @field_validator("allowed_call_end_local")
    @classmethod
    def validate_time_window(cls, v: time, info) -> time:
        """Validate that end time is after start time."""
        start = info.data.get("allowed_call_start_local")
        if start and v <= start:
            raise ValueError("allowed_call_end_local must be after allowed_call_start_local")
        return v

class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign."""

    pass

class CampaignUpdate(BaseModel):
    """Schema for updating an existing campaign."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    language: CampaignLanguage | None = None
    intro_script: str | None = Field(None, min_length=1, max_length=10000)
    question_1: QuestionConfig | None = None
    question_2: QuestionConfig | None = None
    question_3: QuestionConfig | None = None
    max_attempts: int | None = Field(None, ge=1, le=5)
    retry_interval_minutes: int | None = Field(None, ge=1)
    allowed_call_start_local: time | None = None
    allowed_call_end_local: time | None = None
    email_completed_template_id: UUID | None = None
    email_refused_template_id: UUID | None = None
    email_not_reached_template_id: UUID | None = None

class CampaignResponse(BaseModel):
    """Schema for campaign API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Campaign ID")
    name: str = Field(..., description="Campaign name")
    description: str | None = Field(None, description="Campaign description")
    status: CampaignStatus = Field(..., description="Campaign status")
    language: CampaignLanguage = Field(..., description="Campaign language")
    intro_script: str = Field(..., description="Introduction script")
    question_1_text: str = Field(..., description="First question text")
    question_1_type: QuestionType = Field(..., description="First question type")
    question_2_text: str = Field(..., description="Second question text")
    question_2_type: QuestionType = Field(..., description="Second question type")
    question_3_text: str = Field(..., description="Third question text")
    question_3_type: QuestionType = Field(..., description="Third question type")
    max_attempts: int = Field(..., description="Maximum call attempts")
    retry_interval_minutes: int = Field(..., description="Retry interval in minutes")
    allowed_call_start_local: time = Field(..., description="Call window start time")
    allowed_call_end_local: time = Field(..., description="Call window end time")
    email_completed_template_id: UUID | None = Field(None)
    email_refused_template_id: UUID | None = Field(None)
    email_not_reached_template_id: UUID | None = Field(None)
    created_by_user_id: UUID = Field(..., description="Creator user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list response."""

    items: list[CampaignResponse] = Field(..., description="List of campaigns")
    total: int = Field(..., description="Total number of campaigns")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")

class StatusTransitionRequest(BaseModel):
    """Schema for campaign status transition requests."""

    target_status: CampaignStatus = Field(..., description="Target status")