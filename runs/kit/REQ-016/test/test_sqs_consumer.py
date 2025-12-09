"""
Tests for SQS consumer.

REQ-016: Email worker service
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.email.sqs_consumer import SQSConsumer, SQSMessage, SurveyEvent
from app.email.config import SQSConfig


@pytest.fixture
def sqs_config():
    """Create SQS config."""
    return SQSConfig(
        queue_url="https://sqs.eu-central-1.amazonaws.com/123456789/test-queue",
        region="eu-central-1",
        visibility_timeout=300,
        wait_time_seconds=1,
        max_messages=10,
    )


@pytest.fixture
def sqs_consumer(sqs_config):
    """Create SQS consumer."""
    return SQSConsumer(sqs_config)


class TestSQSConsumer:
    """Tests for SQSConsumer."""
    
    def test_parse_sqs_message(self, sqs_consumer):
        """Test parsing raw SQS message."""
        raw_message = {
            "MessageId": "msg-123",
            "ReceiptHandle": "receipt-456",
            "Body": json.dumps({
                "event_type": "survey.completed",
                "campaign_id": str(uuid4()),
                "contact_id": str(uuid4()),
            }),
            "Attributes": {"ApproximateReceiveCount": "1"},
        }
        
        result = sqs_consumer._parse_sqs_message(raw_message)
        
        assert isinstance(result, SQSMessage)
        assert result.message_id == "msg-123"
        assert result.receipt_handle == "receipt-456"
        assert result.body["event_type"] == "survey.completed"
    
    def test_parse_survey_event(self, sqs_consumer):
        """Test parsing survey event from message body."""
        campaign_id = uuid4()
        contact_id = uuid4()
        
        body = {
            "event_type": "survey.completed",
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
            "call_id": "call-123",
            "timestamp": "2024-01-15T10:00:00Z",
            "outcome": "completed",
            "answers": ["Answer 1", "Answer 2", "Answer 3"],
            "attempts": 1,
        }
        
        result = sqs_consumer._parse_survey_event(body)
        
        assert isinstance(result, SurveyEvent)
        assert result.event_type == "survey.completed"
        assert result.campaign_id == campaign_id
        assert result.contact_id == contact_id
        assert result.call_id == "call-123"
        assert result.answers == ["Answer 1", "Answer 2", "Answer 3"]
        assert result.attempts == 1
    
    def test_parse_survey_event_refused(self, sqs_consumer):
        """Test parsing refused event."""
        body = {
            "event_type": "survey.refused",
            "campaign_id": str(uuid4()),
            "contact_id": str(uuid4()),
            "call_id": "call-456",
            "timestamp": "2024-01-15T10:00:00Z",
            "outcome": "refused",
            "attempts": 1,
        }
        
        result = sqs_consumer._parse_survey_event(body)
        
        assert result.event_type == "survey.refused"
        assert result.answers is None
    
    def test_parse_survey_event_not_reached(self, sqs_consumer):
        """Test parsing not_reached event."""
        body = {
            "event_type": "survey.not_reached",
            "campaign_id": str(uuid4()),
            "contact_id": str(uuid4()),
            "timestamp": "2024-01-15T10:00:00Z",
            "outcome": "not_reached",
            "attempts": 5,
        }
        
        result = sqs_consumer._parse_survey_event(body)
        
        assert result.event_type == "survey.not_reached"
        assert result.attempts == 5
        assert result.call_id is None
    
    def test_stop(self, sqs_consumer):
        """Test stopping consumer."""
        sqs_consumer._running = True
        
        sqs_consumer.stop()
        
        assert sqs_consumer._running is False


class TestSQSConfig:
    """Tests for SQSConfig."""
    
    def test_from_env_missing_queue_url(self):
        """Test config creation fails without queue URL."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="SQS_QUEUE_URL"):
                SQSConfig.from_env()
    
    def test_from_env_with_defaults(self):
        """Test config creation with defaults."""
        with patch.dict("os.environ", {"SQS_QUEUE_URL": "https://sqs.example.com/queue"}):
            config = SQSConfig.from_env()
            
            assert config.queue_url == "https://sqs.example.com/queue"
            assert config.region == "eu-central-1"
            assert config.visibility_timeout == 300