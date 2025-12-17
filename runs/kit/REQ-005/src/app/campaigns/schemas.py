from __future__ import annotations

from datetime import time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CampaignBase(BaseModel):
    name: str = Field(..., min_length=1)
    question_1_text: str = Field(..., min_length=1)
    question_2_text: str = Field(..., min_length=1)
    question_3_text: str = Field(..., min_length=1)
    max_attempts: int = Field(..., ge=1, le=5)
    allowed_call_start_local: Optional[time] = None
    allowed_call_end_local: Optional[time] = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    question_1_text: Optional[str] = Field(None, min_length=1)
    question_2_text: Optional[str] = Field(None, min_length=1)
    question_3_text: Optional[str] = Field(None, min_length=1)
    max_attempts: Optional[int] = Field(None, ge=1, le=5)
    allowed_call_start_local: Optional[time] = None
    allowed_call_end_local: Optional[time] = None


class CampaignStatusTransition(BaseModel):
    status: str


class CampaignResponse(CampaignBase):
    id: UUID
    status: str


class CampaignListItem(BaseModel):
    id: UUID
    name: str
    status: str


class PaginationMeta(BaseModel):
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    details: List[ErrorDetail] = Field(default_factory=list)


class CampaignListResponse(BaseModel):
    campaigns: List[CampaignResponse]
    total: int


class ValidationErrorDetail(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    error: str
    details: List[ValidationErrorDetail] = Field(default_factory=list)


class CampaignActivationResponse(BaseModel):
    id: UUID
    status: str
