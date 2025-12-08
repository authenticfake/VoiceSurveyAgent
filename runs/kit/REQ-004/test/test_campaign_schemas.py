"""Tests for campaign schemas."""

import pytest
from datetime import time
from uuid import uuid4

from pydantic import ValidationError

from app.campaigns.schemas import (
    CampaignCreate,
    CampaignUpdate,
    CampaignStatusUpdate,
    CampaignResponse,
    CampaignListResponse,
)
from app.shared.models.enums import CampaignStatus, LanguageCode, QuestionType


class TestCampaignCreate:
    """Tests for CampaignCreate schema."""
    
    def test_valid_campaign_create(self):
        """Test creating a valid campaign."""
        data = CampaignCreate(
            name="Test Campaign",
            intro_script="This is a test introduction script for the survey.",
            question_1_text="What is your favorite color?",
            question_1_type=QuestionType.FREE_TEXT,
            question_2_text="Rate your experience from 1-10",
            question_2_type=QuestionType.SCALE,
            question_3_text="How many times have you visited?",
            question_3_type=QuestionType.NUMERIC,
        )
        assert data.name == "Test Campaign"
        assert data.status is None  # Not set in create schema
        assert data.language == LanguageCode.EN  # Default
        assert data.max_attempts == 3  # Default
    
    def test_campaign_create_with_all_fields(self):
        """Test creating a campaign with all optional fields."""
        template_id = uuid4()
        data = CampaignCreate(
            name="Full Campaign",
            description="A complete campaign",
            language=LanguageCode.IT,
            intro_script="Benvenuto al nostro sondaggio.",
            question_1_text="Prima domanda?",
            question_1_type=QuestionType.FREE_TEXT,
            question_2_text="Seconda domanda?",
            question_2_type=QuestionType.NUMERIC,
            question_3_text="Terza domanda?",
            question_3_type=QuestionType.SCALE,
            max_attempts=5,
            retry_interval_minutes=120,
            allowed_call_start_local=time(10, 0),
            allowed_call_end_local=time(18, 0),
            email_completed_template_id=template_id,
        )
        assert data.language == LanguageCode.IT
        assert data.max_attempts == 5
        assert data.allowed_call_start_local == time(10, 0)
    
    def test_campaign_create_name_too_short(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CampaignCreate(
                name="",
                intro_script="Valid intro script here.",
                question_1_text="Question 1?",
                question_1_type=QuestionType.FREE_TEXT,
                question_2_text="Question 2?",
                question_2_type=QuestionType.FREE_TEXT,
                question_3_text="Question 3?",
                question_3_type=QuestionType.FREE_TEXT,
            )
        assert "String should have at least 1 character" in str(exc_info.value)
    
    def test_campaign_create_intro_script_too_short(self):
        """Test that short intro script is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CampaignCreate(
                name="Test",
                intro_script="Short",
                question_1_text="Question 1?",
                question_1_type=QuestionType.FREE_TEXT,
                question_2_text="Question 2?",
                question_2_type=QuestionType.FREE_TEXT,
                question_3_text="Question 3?",
                question_3_type=QuestionType.FREE_TEXT,
            )
        assert "String should have at least 10 characters" in str(exc_info.value)
    
    def test_campaign_create_max_attempts_out_of_range(self):
        """Test that max_attempts outside 1-5 is rejected."""
        with pytest.raises(ValidationError):
            CampaignCreate(
                name="Test",
                intro_script="Valid intro script here.",
                question_1_text="Question 1?",
                question_1_type=QuestionType.FREE_TEXT,
                question_2_text="Question 2?",
                question_2_type=QuestionType.FREE_TEXT,
                question_3_text="Question 3?",
                question_3_type=QuestionType.FREE_TEXT,
                max_attempts=6,
            )


class TestCampaignUpdate:
    """Tests for CampaignUpdate schema."""
    
    def test_partial_update(self):
        """Test partial update with only some fields."""
        data = CampaignUpdate(name="Updated Name")
        assert data.name == "Updated Name"
        assert data.description is None
        assert data.language is None
    
    def test_update_with_extra_fields_rejected(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            CampaignUpdate(name="Test", unknown_field="value")
    
    def test_empty_update(self):
        """Test that empty update is valid."""
        data = CampaignUpdate()
        assert data.model_dump(exclude_unset=True) == {}


class TestCampaignStatusUpdate:
    """Tests for CampaignStatusUpdate schema."""
    
    def test_valid_status_update(self):
        """Test valid status update."""
        data = CampaignStatusUpdate(status=CampaignStatus.RUNNING)
        assert data.status == CampaignStatus.RUNNING
    
    def test_invalid_status(self):
        """Test that invalid status is rejected."""
        with pytest.raises(ValidationError):
            CampaignStatusUpdate(status="invalid")


class TestCampaignResponse:
    """Tests for CampaignResponse schema."""
    
    def test_response_from_attributes(self):
        """Test creating response from ORM model attributes."""
        from datetime import datetime
        
        class MockCampaign:
            id = uuid4()
            name = "Test"
            description = None
            status = CampaignStatus.DRAFT
            language = LanguageCode.EN
            intro_script = "Test intro script"
            question_1_text = "Q1?"
            question_1_type = QuestionType.FREE_TEXT
            question_2_text = "Q2?"
            question_2_type = QuestionType.FREE_TEXT
            question_3_text = "Q3?"
            question_3_type = QuestionType.FREE_TEXT
            max_attempts = 3
            retry_interval_minutes = 60
            allowed_call_start_local = time(9, 0)
            allowed_call_end_local = time(20, 0)
            email_completed_template_id = None
            email_refused_template_id = None
            email_not_reached_template_id = None
            created_by_user_id = uuid4()
            created_at = datetime.utcnow()
            updated_at = datetime.utcnow()
        
        response = CampaignResponse.model_validate(MockCampaign())
        assert response.status == CampaignStatus.DRAFT


class TestCampaignListResponse:
    """Tests for CampaignListResponse schema."""
    
    def test_list_response(self):
        """Test list response structure."""
        response = CampaignListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            pages=0,
        )
        assert response.total == 0
        assert response.pages == 0