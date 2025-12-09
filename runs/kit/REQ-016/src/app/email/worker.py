"""
Email worker that polls SQS and processes survey events.

REQ-016: Email worker service
"""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from app.email.config import EmailConfig, SQSConfig
from app.email.service import EmailService
from app.email.sqs_consumer import SQSConsumer, SurveyEvent, SQSMessage
from app.email.interfaces import EmailResult

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Exponential backoff retry policy."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt number."""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    def should_retry(self, attempt: int) -> bool:
        """Check if should retry based on attempt count."""
        return attempt < self.max_retries


class EmailWorker:
    """
    Worker that continuously polls SQS for survey events
    and sends corresponding emails.
    
    Features:
    - Continuous polling with long-polling
    - Automatic retry with exponential backoff
    - Idempotent processing via event_id
    - Graceful shutdown
    """
    
    def __init__(
        self,
        email_service: EmailService,
        sqs_consumer: SQSConsumer,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        """
        Initialize email worker.
        
        Args:
            email_service: Service for processing events and sending emails.
            sqs_consumer: SQS message consumer.
            retry_policy: Retry policy for failed sends.
        """
        self._email_service = email_service
        self._sqs_consumer = sqs_consumer
        self._retry_policy = retry_policy or RetryPolicy()
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the worker."""
        if self._running:
            logger.warning("Worker already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Email worker started")
    
    async def stop(self) -> None:
        """Stop the worker gracefully."""
        if not self._running:
            return
        
        self._running = False
        self._sqs_consumer.stop()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Email worker stopped")
    
    async def _run(self) -> None:
        """Main worker loop."""
        async for sqs_message, event in self._sqs_consumer.consume():
            if not self._running:
                break
            
            try:
                await self._process_with_retry(sqs_message, event)
            except Exception as e:
                logger.exception(f"Unhandled error processing event: {e}")
    
    async def _process_with_retry(
        self,
        sqs_message: SQSMessage,
        event: SurveyEvent,
    ) -> None:
        """
        Process event with retry logic.
        
        Args:
            sqs_message: Original SQS message for acknowledgment.
            event: Parsed survey event.
        """
        event_id = UUID(sqs_message.message_id)
        attempt = 0
        
        while True:
            try:
                result = await self._email_service.process_event(event, event_id)
                
                if result is None:
                    # No email to send (no template configured, no email address, etc.)
                    logger.info(f"No email to send for event {event_id}")
                    await self._sqs_consumer.acknowledge(sqs_message.receipt_handle)
                    return
                
                if result.success:
                    logger.info(f"Successfully processed event {event_id}")
                    await self._sqs_consumer.acknowledge(sqs_message.receipt_handle)
                    return
                
                # Email send failed
                attempt += 1
                if not self._retry_policy.should_retry(attempt):
                    logger.error(
                        f"Failed to send email for event {event_id} after {attempt} attempts: "
                        f"{result.error_message}"
                    )
                    # Acknowledge to prevent infinite retry - error is logged
                    await self._sqs_consumer.acknowledge(sqs_message.receipt_handle)
                    return
                
                delay = self._retry_policy.get_delay(attempt)
                logger.warning(
                    f"Email send failed for event {event_id}, attempt {attempt}, "
                    f"retrying in {delay}s: {result.error_message}"
                )
                await asyncio.sleep(delay)
                
            except Exception as e:
                attempt += 1
                if not self._retry_policy.should_retry(attempt):
                    logger.exception(
                        f"Failed to process event {event_id} after {attempt} attempts: {e}"
                    )
                    await self._sqs_consumer.acknowledge(sqs_message.receipt_handle)
                    return
                
                delay = self._retry_policy.get_delay(attempt)
                logger.warning(
                    f"Error processing event {event_id}, attempt {attempt}, "
                    f"retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
    
    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running