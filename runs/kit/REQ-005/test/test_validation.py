"""Tests for campaign validation service."""

from datetime import time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.campaigns.validation import (
    CampaignValidationService,
    CampaignDataProvider,
    ValidationResult,
)
from app.shared.models.enums import CampaignStatus

class MockDataProvider:
    """Mock implementation of CampaignDataProvider for testing."""
    
    def __init__(
        self,
        contact_count: int = 10,
        questions: tuple[str, str, str] = ("Q1?", "Q2?", "Q3?"),
        retry_policy: tuple[int, int] = (3, 60),
        time_window: tuple[time, time] = (time(9, 0), time(20, 0)),
        status: CampaignStatus = CampaignStatus.DRAFT,
    ):
        self.contact_count = contact_count
        self.questions = questions
        self.retry_policy = retry_policy
        self.time_window = time_window
        self.status = status
    
    async def get_contact_count(self, campaign_id) -> int:
        return self.contact_count
    
    async def get_campaign_questions(self, campaign_id) -> tuple[str, str, str]:
        return self.questions
    
    async def get_retry_policy(self, campaign_id) -> tuple[int, int]:
        return self.retry_policy
    
    async def get_time_window(self, campaign_id) -> tuple[time, time]:
        return self.time_window
    
    async def get_campaign_status(self, campaign_id) -> CampaignStatus:
        return self.status

@pytest.fixture
def campaign_id():
    """Generate a test campaign ID."""
    return uuid4()

@pytest.mark.asyncio
async def test_validation_passes_with_valid_campaign(campaign_id):
    """Test that validation passes for a valid campaign."""
    provider = MockDataProvider()
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is True
    assert len(result.errors) == 0

@pytest.mark.asyncio
async def test_validation_fails_with_zero_contacts(campaign_id):
    """Test that validation fails when campaign has no contacts."""
    provider = MockDataProvider(contact_count=0)
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.code == "NO_CONTACTS" for e in result.errors)
    assert any(e.field == "contacts" for e in result.errors)

@pytest.mark.asyncio
async def test_validation_fails_with_empty_question_1(campaign_id):
    """Test that validation fails when question 1 is empty."""
    provider = MockDataProvider(questions=("", "Q2?", "Q3?"))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.field == "question_1_text" for e in result.errors)
    assert any(e.code == "EMPTY_QUESTION" for e in result.errors)

@pytest.mark.asyncio
async def test_validation_fails_with_empty_question_2(campaign_id):
    """Test that validation fails when question 2 is empty."""
    provider = MockDataProvider(questions=("Q1?", "", "Q3?"))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.field == "question_2_text" for e in result.errors)

@pytest.mark.asyncio
async def test_validation_fails_with_empty_question_3(campaign_id):
    """Test that validation fails when question 3 is empty."""
    provider = MockDataProvider(questions=("Q1?", "Q2?", ""))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.field == "question_3_text" for e in result.errors)

@pytest.mark.asyncio
async def test_validation_fails_with_whitespace_only_question(campaign_id):
    """Test that validation fails when question is whitespace only."""
    provider = MockDataProvider(questions=("   ", "Q2?", "Q3?"))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.field == "question_1_text" for e in result.errors)

@pytest.mark.asyncio
async def test_validation_fails_with_max_attempts_zero(campaign_id):
    """Test that validation fails when max_attempts is 0."""
    provider = MockDataProvider(retry_policy=(0, 60))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.code == "INVALID_RETRY_POLICY" for e in result.errors)
    assert any(e.field == "max_attempts" for e in result.errors)

@pytest.mark.asyncio
async def test_validation_fails_with_max_attempts_over_five(campaign_id):
    """Test that validation fails when max_attempts exceeds 5."""
    provider = MockDataProvider(retry_policy=(6, 60))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.code == "INVALID_RETRY_POLICY" for e in result.errors)

@pytest.mark.asyncio
async def test_validation_passes_with_max_attempts_one(campaign_id):
    """Test that validation passes with max_attempts = 1."""
    provider = MockDataProvider(retry_policy=(1, 60))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is True

@pytest.mark.asyncio
async def test_validation_passes_with_max_attempts_five(campaign_id):
    """Test that validation passes with max_attempts = 5."""
    provider = MockDataProvider(retry_policy=(5, 60))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is True

@pytest.mark.asyncio
async def test_validation_fails_with_invalid_time_window(campaign_id):
    """Test that validation fails when start time >= end time."""
    provider = MockDataProvider(time_window=(time(20, 0), time(9, 0)))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.code == "INVALID_TIME_WINDOW" for e in result.errors)

@pytest.mark.asyncio
async def test_validation_fails_with_equal_time_window(campaign_id):
    """Test that validation fails when start time equals end time."""
    provider = MockDataProvider(time_window=(time(12, 0), time(12, 0)))
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.code == "INVALID_TIME_WINDOW" for e in result.errors)

@pytest.mark.asyncio
async def test_validation_fails_with_non_draft_status(campaign_id):
    """Test that validation fails when campaign is not in draft status."""
    provider = MockDataProvider(status=CampaignStatus.RUNNING)
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    assert any(e.code == "INVALID_STATUS" for e in result.errors)
    # Should return early with only status error
    assert len(result.errors) == 1

@pytest.mark.asyncio
async def test_validation_collects_multiple_errors(campaign_id):
    """Test that validation collects all errors when multiple issues exist."""
    provider = MockDataProvider(
        contact_count=0,
        questions=("", "", ""),
        retry_policy=(10, 60),
        time_window=(time(20, 0), time(9, 0)),
    )
    service = CampaignValidationService(provider)
    
    result = await service.validate_for_activation(campaign_id)
    
    assert result.is_valid is False
    # Should have errors for: contacts, q1, q2, q3, retry policy, time window
    assert len(result.errors) >= 5

@pytest.mark.asyncio
async def test_validation_result_add_error():
    """Test ValidationResult.add_error method."""
    result = ValidationResult(is_valid=True)
    
    result.add_error("test_field", "Test message", "TEST_CODE")
    
    assert result.is_valid is False
    assert len(result.errors) == 1
    assert result.errors[0].field == "test_field"
    assert result.errors[0].message == "Test message"
    assert result.errors[0].code == "TEST_CODE"