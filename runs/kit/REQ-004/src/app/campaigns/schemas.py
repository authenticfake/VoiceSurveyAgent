"""Campaign schemas for API validation and serialization."""

from datetime import datetime, time
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType


class CampaignBase(BaseModel):
    """Base campaign schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    language: LanguageCode = Field(LanguageCode.EN, description="Campaign language")
    intro_script: str = Field(..., min_length=10, description="Introduction script")
    question_1_text: str = Field(..., min_length=5, description="First question text")
    question_1_type: QuestionType = Field(..., description="First question type")
    question_2_text: str = Field(..., min_length=5, description="Second question text")
    question_2_type: QuestionType = Field(..., description="Second question type")
    question_3_text: str = Field(..., min_length=5, description="Third question text")
    question_3_type: QuestionType = Field(..., description="Third question type")
    max_attempts: int = Field(3, ge=1, le=5, description="Maximum call attempts")
    retry_interval_minutes: int = Field(60, ge=1, description="Minutes between retries")
    allowed_call_start_local: time = Field(
        default=time(9, 0), description="Earliest call time (local)"
    )
    allowed_call_end_local: time = Field(
        default=time(20, 0), description="Latest call time (local)"
    )
    email_completed_template_id: Optional[UUID] = Field(
        None, description="Email template for completed surveys"
    )
    email_refused_template_id: Optional[UUID] = Field(
        None, description="Email template for refused surveys"
    )
    email_not_reached_template_id: Optional[UUID] = Field(
        None, description="Email template for not reached contacts"
    )


class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign."""
    pass


class CampaignUpdate(BaseModel):
    """Schema for updating an existing campaign."""
    
    model_config = ConfigDict(extra="forbid")
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    language: Optional[LanguageCode] = None
    intro_script: Optional[str] = Field(None, min_length=10)
    question_1_text: Optional[str] = Field(None, min_length=5)
    question_1_type: Optional[QuestionType] = None
    question_2_text: Optional[str] = Field(None, min_length=5)
    question_2_type: Optional[QuestionType] = None
    question_3_text: Optional[str] = Field(None, min_length=5)
    question_3_type: Optional[QuestionType] = None
    max_attempts: Optional[int] = Field(None, ge=1, le=5)
    retry_interval_minutes: Optional[int] = Field(None, ge=1)
    allowed_call_start_local: Optional[time] = None
    allowed_call_end_local: Optional[time] = None
    email_completed_template_id: Optional[UUID] = None
    email_refused_template_id: Optional[UUID] = None
    email_not_reached_template_id: Optional[UUID] = None


class CampaignStatusUpdate(BaseModel):
    """Schema for updating campaign status."""
    
    status: CampaignStatus = Field(..., description="New campaign status")


class CampaignResponse(CampaignBase):
    """Schema for campaign response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: CampaignStatus
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list response."""
    
    items: list[CampaignResponse]
    total: int
    page: int
    page_size: int
    pages: int