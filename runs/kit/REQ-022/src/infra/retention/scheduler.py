"""
Retention job scheduler.

REQ-022: Data retention jobs

Provides scheduling infrastructure for:
- Daily retention job execution
- GDPR request processing
- Background task management
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional, Callable, Awaitable

from infra.retention.service import RetentionService
from infra.retention.gdpr import GDPRDeletionService
from infra.retention.models import RetentionResult

logger = logging.getLogger(__name__)


class RetentionScheduler:
    """
    Scheduler for retention jobs.
    
    Runs retention jobs daily at a configured time and
    processes GDPR requests periodically.
    """
    
    def __init__(
        self,
        retention_service: RetentionService,
        gdpr_service: GDPRDeletionService,
        daily_run_time: time = time(2, 0),  # 2 AM by default
        gdpr_check_interval_minutes: int = 60,
    ):
        """
        Initialize the scheduler.
        
        Args:
            retention_service: Service for retention operations
            gdpr_service: Service for GDPR deletions
            daily_run_time: Time of day to run retention job (UTC)
            gdpr_check_interval_minutes: Interval for GDPR request checks
        """
        self._retention_service = retention_service
        self._gdpr_service = gdpr_service
        self._daily_run_time = daily_run_time
        self._gdpr_check_interval = timedelta(minutes=gdpr_check_interval_minutes)
        self._running = False
        self._retention_task: Optional[asyncio.Task] = None
        self._gdpr_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        
        logger.info(
            "Starting retention scheduler",
            extra={
                "daily_run_time": self._daily_run_time.isoformat(),
                "gdpr_check_interval_minutes": self._gdpr_check_interval.total_seconds() / 60,
            }
        )
        
        self._retention_task = asyncio.create_task(self._run_retention_loop())
        self._gdpr_task = asyncio.create_task(self._run_gdpr_loop())
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        
        if self._retention_task:
            self._retention_task.cancel()
            try:
                await self._retention_task
            except asyncio.CancelledError:
                pass
        
        if self._gdpr_task:
            self._gdpr_task.cancel()
            try:
                await self._gdpr_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Retention scheduler stopped")
    
    async def _run_retention_loop(self) -> None:
        """Main loop for daily retention job."""
        while self._running:
            try:
                # Calculate time until next run
                now = datetime.utcnow()
                next_run = self._calculate_next_run(now)
                wait_seconds = (next_run - now).total_seconds()
                
                logger.info(
                    "Waiting for next retention job",
                    extra={
                        "next_run": next_run.isoformat(),
                        "wait_seconds": wait_seconds,
                    }
                )
                
                await asyncio.sleep(wait_seconds)
                
                if not self._running:
                    break
                
                # Run the retention job
                result = await self._retention_service.run_retention_job()
                
                logger.info(
                    "Daily retention job completed",
                    extra={
                        "job_id": str(result.job_id),
                        "status": result.status.value,
                        "total_deleted": result.total_deleted,
                        "total_failed": result.total_failed,
                    }
                )
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception(
                    "Error in retention loop",
                    extra={"error": str(e)}
                )
                # Wait before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def _run_gdpr_loop(self) -> None:
        """Loop for processing GDPR requests."""
        while self._running:
            try:
                await asyncio.sleep(self._gdpr_check_interval.total_seconds())
                
                if not self._running:
                    break
                
                # Process pending GDPR requests
                processed = await self._gdpr_service.process_pending_requests()
                
                if processed:
                    logger.info(
                        "GDPR requests processed",
                        extra={"count": len(processed)}
                    )
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception(
                    "Error in GDPR processing loop",
                    extra={"error": str(e)}
                )
                # Wait before retrying
                await asyncio.sleep(60)  # 1 minute
    
    def _calculate_next_run(self, now: datetime) -> datetime:
        """Calculate the next scheduled run time."""
        today_run = now.replace(
            hour=self._daily_run_time.hour,
            minute=self._daily_run_time.minute,
            second=0,
            microsecond=0,
        )
        
        if now >= today_run:
            # Already past today's run time, schedule for tomorrow
            return today_run + timedelta(days=1)
        
        return today_run
    
    async def run_now(self) -> RetentionResult:
        """
        Trigger an immediate retention job run.
        
        Returns:
            RetentionResult from the job
        """
        logger.info("Manual retention job triggered")
        return await self._retention_service.run_retention_job()
    
    async def process_gdpr_now(self) -> int:
        """
        Trigger immediate GDPR request processing.
        
        Returns:
            Number of requests processed
        """
        logger.info("Manual GDPR processing triggered")
        processed = await self._gdpr_service.process_pending_requests()
        return len(processed)