"""
Tests for email worker.

REQ-016: Email worker service
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.email.worker import EmailWorker, RetryPolicy
from app.email.interfaces import EmailResult
from app.email.sqs_consumer import SQSMessage, SurveyEvent


@pytest.fixture
def mock_email_service():
    """Create mock email service."""
    service = AsyncMock()
    service.process_event = AsyncMock(return_value=EmailResult(success=True, provider_message_id="msg-123"))
    return service


@pytest.fixture
def mock_sqs_consumer():
    """Create mock SQS consumer."""
    consumer = AsyncMock()
    consumer.acknowledge = AsyncMock()
    consumer.stop = MagicMock()
    return consumer


@pytest.fixture
def retry_policy():
    """Create retry policy."""
    return RetryPolicy(max_retries=3, base_delay=0.01, max_delay=0.1)


@pytest.fixture
def email_worker(mock_email_service, mock_sqs_consumer, retry_policy):
    """Create email worker with mocks."""
    return EmailWorker(
        email_service=mock_email_service,
        sqs_consumer=mock_sqs_consumer,
        retry_policy=retry_policy,
    )


@pytest.fixture
def sample_sqs_message():
    """Create sample SQS message."""
    return SQSMessage(
        receipt_handle="receipt-123",
        message_id=str(uuid4()),
        body={
            "event_type": "survey.completed",
            "campaign_id": str(uuid4()),
            "contact_id": str(uuid4()),
            "call_id": "call-123",
            "timestamp": "2024-01-15T10:00:00Z",
            "outcome": "completed",
            "answers": ["Answer 1", "Answer 2", "Answer 3"],
            "attempts": 1,
        },
        attributes={},
    )


@pytest.fixture
def sample_event():
    """Create sample survey event."""
    return SurveyEvent(
        event_type="survey.completed",
        campaign_id=uuid4(),
        contact_id=uuid4(),
        call_id="call-123",
        timestamp="2024-01-15T10:00:00Z",
        outcome="completed",
        answers=["Answer 1", "Answer 2", "Answer 3"],
        attempts=1,
        raw_payload={},
    )


class TestRetryPolicy:
    """Tests for RetryPolicy."""
    
    def test_get_delay_exponential(self):
        """Test exponential backoff calculation."""
        policy = RetryPolicy(base_delay=1.0, max_delay=60.0)
        
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 8.0
    
    def test_get_delay_max_cap(self):
        """Test delay is capped at max_delay."""
        policy = RetryPolicy(base_delay=1.0, max_delay=10.0)
        
        assert policy.get_delay(10) == 10.0  # Would be 1024 without cap
    
    def test_should_retry(self):
        """Test retry decision."""
        policy = RetryPolicy(max_retries=3)
        
        assert policy.should_retry(0) is True
        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False
        assert policy.should_retry(4) is False


class TestEmailWorker:
    """Tests for EmailWorker."""
    
    @pytest.mark.asyncio
    async def test_process_successful_event(
        self,
        email_worker,
        mock_email_service,
        mock_sqs_consumer,
        sample_sqs_message,
        sample_event,
    ):
        """Test successful event processing."""
        # Execute
        await email_worker._process_with_retry(sample_sqs_message, sample_event)
        
        # Verify
        mock_email_service.process_event.assert_called_once()
        mock_sqs_consumer.acknowledge.assert_called_once_with(sample_sqs_message.receipt_handle)
    
    @pytest.mark.asyncio
    async def test_process_no_email_to_send(
        self,
        email_worker,
        mock_email_service,
        mock_sqs_consumer,
        sample_sqs_message,
        sample_event,
    ):
        """Test processing when no email needs to be sent."""
        mock_email_service.process_event = AsyncMock(return_value=None)
        
        # Execute
        await email_worker._process_with_retry(sample_sqs_message, sample_event)
        
        # Verify - should still acknowledge
        mock_sqs_consumer.acknowledge.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_with_retry_on_failure(
        self,
        email_worker,
        mock_email_service,
        mock_sqs_consumer,
        sample_sqs_message,
        sample_event,
    ):
        """Test retry logic on email send failure."""
        # Setup - fail twice, then succeed
        mock_email_service.process_event = AsyncMock(
            side_effect=[
                EmailResult(success=False, error_message="Temporary error"),
                EmailResult(success=False, error_message="Temporary error"),
                EmailResult(success=True, provider_message_id="msg-123"),
            ]
        )
        
        # Execute
        await email_worker._process_with_retry(sample_sqs_message, sample_event)
        
        # Verify - should have retried and eventually succeeded
        assert mock_email_service.process_event.call_count == 3
        mock_sqs_consumer.acknowledge.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_max_retries_exceeded(
        self,
        email_worker,
        mock_email_service,
        mock_sqs_consumer,
        sample_sqs_message,
        sample_event,
    ):
        """Test behavior when max retries exceeded."""
        # Setup - always fail
        mock_email_service.process_event = AsyncMock(
            return_value=EmailResult(success=False, error_message="Persistent error")
        )
        
        # Execute
        await email_worker._process_with_retry(sample_sqs_message, sample_event)
        
        # Verify - should acknowledge after max retries to prevent infinite loop
        assert mock_email_service.process_event.call_count == 4  # Initial + 3 retries
        mock_sqs_consumer.acknowledge.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_exception_with_retry(
        self,
        email_worker,
        mock_email_service,
        mock_sqs_consumer,
        sample_sqs_message,
        sample_event,
    ):
        """Test retry on exception."""
        # Setup - exception then success
        mock_email_service.process_event = AsyncMock(
            side_effect=[
                Exception("Network error"),
                EmailResult(success=True, provider_message_id="msg-123"),
            ]
        )
        
        # Execute
        await email_worker._process_with_retry(sample_sqs_message, sample_event)
        
        # Verify
        assert mock_email_service.process_event.call_count == 2
        mock_sqs_consumer.acknowledge.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_stop(self, email_worker, mock_sqs_consumer):
        """Test worker start and stop."""
        # Setup - consumer that yields nothing
        async def empty_consume():
            while email_worker._running:
                await asyncio.sleep(0.01)
                return
            yield  # Make it a generator
        
        mock_sqs_consumer.consume = empty_consume
        
        # Start
        await email_worker.start()
        assert email_worker.is_running is True
        
        # Stop
        await email_worker.stop()
        assert email_worker.is_running is False
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, email_worker):
        """Test starting already running worker."""
        email_worker._running = True
        
        # Should not raise, just warn
        await email_worker.start()