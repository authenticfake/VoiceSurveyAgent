"""
Retention service implementation.

REQ-022: Data retention jobs

Provides the core retention logic for:
- Deleting expired recordings from storage
- Deleting expired transcripts from database
- Handling partial failures gracefully
- Audit logging of all operations
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from infra.retention.models import (
    RetentionConfig,
    RetentionResult,
    DeletionRecord,
    DeletionType,
    DeletionStatus,
)
from infra.retention.interfaces import (
    StorageBackend,
    RetentionRepository,
    AuditLogger,
)

logger = logging.getLogger(__name__)


class RetentionService:
    """
    Service for executing data retention policies.
    
    Handles deletion of expired recordings and transcripts
    with graceful partial failure handling.
    """
    
    def __init__(
        self,
        repository: RetentionRepository,
        storage: StorageBackend,
        audit_logger: AuditLogger,
        config: Optional[RetentionConfig] = None,
    ):
        """
        Initialize the retention service.
        
        Args:
            repository: Database repository for retention operations
            storage: Object storage backend for recordings
            audit_logger: Audit logger for tracking deletions
            config: Optional retention configuration (loaded from DB if not provided)
        """
        self._repository = repository
        self._storage = storage
        self._audit_logger = audit_logger
        self._config = config
    
    async def _get_config(self) -> RetentionConfig:
        """Get retention configuration, loading from DB if needed."""
        if self._config is not None:
            return self._config
        
        db_config = await self._repository.get_retention_config()
        if db_config is not None:
            return db_config
        
        # Fall back to defaults
        logger.warning("No retention config found, using defaults")
        return RetentionConfig()
    
    async def run_retention_job(
        self,
        now: Optional[datetime] = None,
        dry_run: bool = False,
    ) -> RetentionResult:
        """
        Execute the retention job.
        
        Args:
            now: Current time (for testing)
            dry_run: If True, don't actually delete anything
            
        Returns:
            RetentionResult with counts and status
        """
        now = now or datetime.utcnow()
        result = RetentionResult(started_at=now)
        
        logger.info(
            "Starting retention job",
            extra={
                "job_id": str(result.job_id),
                "dry_run": dry_run,
                "timestamp": now.isoformat(),
            }
        )
        
        try:
            config = await self._get_config()
            
            # Process recordings
            await self._process_recordings(result, config, now, dry_run)
            
            # Process transcripts
            await self._process_transcripts(result, config, now, dry_run)
            
            result.complete()
            
        except Exception as e:
            logger.exception(
                "Retention job failed",
                extra={"job_id": str(result.job_id), "error": str(e)}
            )
            result.complete(error=str(e))
        
        # Log the result
        await self._audit_logger.log_retention_job(result)
        
        # Save result to database
        if not dry_run:
            await self._repository.save_retention_result(result)
        
        logger.info(
            "Retention job completed",
            extra={
                "job_id": str(result.job_id),
                "status": result.status.value,
                "recordings_deleted": result.recordings_deleted,
                "recordings_failed": result.recordings_failed,
                "transcripts_deleted": result.transcripts_deleted,
                "transcripts_failed": result.transcripts_failed,
                "duration_seconds": (
                    (result.completed_at - result.started_at).total_seconds()
                    if result.completed_at else None
                ),
            }
        )
        
        return result
    
    async def _process_recordings(
        self,
        result: RetentionResult,
        config: RetentionConfig,
        now: datetime,
        dry_run: bool,
    ) -> None:
        """Process expired recordings for deletion."""
        cutoff = config.get_recording_cutoff(now)
        
        logger.info(
            "Processing expired recordings",
            extra={
                "cutoff_date": cutoff.isoformat(),
                "retention_days": config.recording_retention_days,
            }
        )
        
        processed = 0
        while True:
            # Get batch of expired recordings
            recordings = await self._repository.get_expired_recordings(
                cutoff_date=cutoff,
                limit=config.batch_size,
            )
            
            if not recordings:
                break
            
            for recording in recordings:
                record = DeletionRecord(
                    deletion_type=DeletionType.RECORDING,
                    resource_id=str(recording.get("call_attempt_id", "")),
                    resource_path=recording.get("recording_path"),
                )
                
                if dry_run:
                    record.mark_completed()
                    result.add_deletion(record)
                    continue
                
                try:
                    # Delete from storage if path exists
                    if record.resource_path:
                        deleted = await self._storage.delete_object(record.resource_path)
                        if not deleted:
                            logger.warning(
                                "Recording not found in storage",
                                extra={"path": record.resource_path}
                            )
                    
                    # Mark as deleted in database
                    call_attempt_id = recording.get("call_attempt_id")
                    if call_attempt_id:
                        await self._repository.mark_recording_deleted(
                            UUID(str(call_attempt_id))
                        )
                    
                    record.mark_completed()
                    
                    await self._audit_logger.log_deletion(
                        deletion_type="recording",
                        resource_id=record.resource_id,
                        user_id=None,
                        details={"path": record.resource_path},
                    )
                    
                except Exception as e:
                    logger.warning(
                        "Failed to delete recording",
                        extra={
                            "resource_id": record.resource_id,
                            "error": str(e),
                        }
                    )
                    record.mark_failed(str(e))
                
                result.add_deletion(record)
                processed += 1
            
            # Safety check to prevent infinite loops
            if processed >= 10000:
                logger.warning("Reached maximum processing limit for recordings")
                break
    
    async def _process_transcripts(
        self,
        result: RetentionResult,
        config: RetentionConfig,
        now: datetime,
        dry_run: bool,
    ) -> None:
        """Process expired transcripts for deletion."""
        cutoff = config.get_transcript_cutoff(now)
        
        logger.info(
            "Processing expired transcripts",
            extra={
                "cutoff_date": cutoff.isoformat(),
                "retention_days": config.transcript_retention_days,
            }
        )
        
        processed = 0
        while True:
            # Get batch of expired transcripts
            transcripts = await self._repository.get_expired_transcripts(
                cutoff_date=cutoff,
                limit=config.batch_size,
            )
            
            if not transcripts:
                break
            
            for transcript in transcripts:
                record = DeletionRecord(
                    deletion_type=DeletionType.TRANSCRIPT,
                    resource_id=str(transcript.get("id", "")),
                )
                
                if dry_run:
                    record.mark_completed()
                    result.add_deletion(record)
                    continue
                
                try:
                    transcript_id = transcript.get("id")
                    if transcript_id:
                        await self._repository.delete_transcript(
                            UUID(str(transcript_id))
                        )
                    
                    record.mark_completed()
                    
                    await self._audit_logger.log_deletion(
                        deletion_type="transcript",
                        resource_id=record.resource_id,
                        user_id=None,
                    )
                    
                except Exception as e:
                    logger.warning(
                        "Failed to delete transcript",
                        extra={
                            "resource_id": record.resource_id,
                            "error": str(e),
                        }
                    )
                    record.mark_failed(str(e))
                
                result.add_deletion(record)
                processed += 1
            
            # Safety check
            if processed >= 10000:
                logger.warning("Reached maximum processing limit for transcripts")
                break
    
    async def trigger_manual_cleanup(
        self,
        user_id: UUID,
        recording_retention_days: Optional[int] = None,
        transcript_retention_days: Optional[int] = None,
    ) -> RetentionResult:
        """
        Trigger a manual cleanup with optional custom retention periods.
        
        Args:
            user_id: ID of the admin user triggering the cleanup
            recording_retention_days: Optional override for recording retention
            transcript_retention_days: Optional override for transcript retention
            
        Returns:
            RetentionResult with cleanup details
        """
        config = await self._get_config()
        
        if recording_retention_days is not None:
            config.recording_retention_days = recording_retention_days
        if transcript_retention_days is not None:
            config.transcript_retention_days = transcript_retention_days
        
        logger.info(
            "Manual retention cleanup triggered",
            extra={
                "user_id": str(user_id),
                "recording_retention_days": config.recording_retention_days,
                "transcript_retention_days": config.transcript_retention_days,
            }
        )
        
        return await self.run_retention_job()