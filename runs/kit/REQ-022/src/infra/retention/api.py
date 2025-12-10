"""
Admin API endpoints for retention management.

REQ-022: Data retention jobs

Provides REST endpoints for:
- Manual retention job triggering
- GDPR deletion request creation
- Retention status monitoring
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from infra.retention.service import RetentionService, RetentionResult
from infra.retention.gdpr import GDPRDeletionService, GDPRDeletionRequest
from infra.retention.scheduler import RetentionScheduler
from infra.retention.models import DeletionStatus, GDPRRequestStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/retention", tags=["retention"])


# Request/Response Models

class TriggerRetentionRequest(BaseModel):
    """Request to trigger manual retention job."""
    recording_retention_days: Optional[int] = Field(
        None, ge=1, le=3650, description="Override recording retention days"
    )
    transcript_retention_days: Optional[int] = Field(
        None, ge=1, le=3650, description="Override transcript retention days"
    )
    dry_run: bool = Field(False, description="If true, don't actually delete")


class RetentionJobResponse(BaseModel):
    """Response for retention job execution."""
    job_id: str
    status: str
    recordings_deleted: int
    recordings_failed: int
    transcripts_deleted: int
    transcripts_failed: int
    total_deleted: int
    total_failed: int
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]


class CreateGDPRRequestBody(BaseModel):
    """Request body for creating GDPR deletion request."""
    contact_id: UUID
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class GDPRRequestResponse(BaseModel):
    """Response for GDPR deletion request."""
    id: str
    contact_id: str
    status: str
    requested_at: datetime
    deadline: Optional[datetime]
    processed_at: Optional[datetime]
    items_deleted: int
    error_message: Optional[str]


class RetentionStatusResponse(BaseModel):
    """Response for retention status."""
    scheduler_running: bool
    last_job_id: Optional[str]
    last_job_status: Optional[str]
    last_job_completed_at: Optional[datetime]
    pending_gdpr_requests: int
    overdue_gdpr_requests: int


# Dependency injection placeholders
# In production, these would be injected via FastAPI's dependency system

_retention_service: Optional[RetentionService] = None
_gdpr_service: Optional[GDPRDeletionService] = None
_scheduler: Optional[RetentionScheduler] = None


def get_retention_service() -> RetentionService:
    """Get retention service instance."""
    if _retention_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retention service not initialized"
        )
    return _retention_service


def get_gdpr_service() -> GDPRDeletionService:
    """Get GDPR service instance."""
    if _gdpr_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GDPR service not initialized"
        )
    return _gdpr_service


def get_scheduler() -> RetentionScheduler:
    """Get scheduler instance."""
    if _scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )
    return _scheduler


def configure_services(
    retention_service: RetentionService,
    gdpr_service: GDPRDeletionService,
    scheduler: RetentionScheduler,
) -> None:
    """Configure service instances for the API."""
    global _retention_service, _gdpr_service, _scheduler
    _retention_service = retention_service
    _gdpr_service = gdpr_service
    _scheduler = scheduler


# Endpoints

@router.post("/trigger", response_model=RetentionJobResponse)
async def trigger_retention_job(
    request: TriggerRetentionRequest,
    service: RetentionService = Depends(get_retention_service),
) -> RetentionJobResponse:
    """
    Trigger a manual retention job.
    
    Requires admin role.
    """
    logger.info(
        "Manual retention job triggered via API",
        extra={
            "recording_retention_days": request.recording_retention_days,
            "transcript_retention_days": request.transcript_retention_days,
            "dry_run": request.dry_run,
        }
    )
    
    # For manual trigger with custom retention, we need to create a new config
    from infra.retention.models import RetentionConfig
    
    config = None
    if request.recording_retention_days or request.transcript_retention_days:
        base_config = await service._get_config()
        config = RetentionConfig(
            recording_retention_days=request.recording_retention_days or base_config.recording_retention_days,
            transcript_retention_days=request.transcript_retention_days or base_config.transcript_retention_days,
        )
        service._config = config
    
    result = await service.run_retention_job(dry_run=request.dry_run)
    
    return RetentionJobResponse(
        job_id=str(result.job_id),
        status=result.status.value,
        recordings_deleted=result.recordings_deleted,
        recordings_failed=result.recordings_failed,
        transcripts_deleted=result.transcripts_deleted,
        transcripts_failed=result.transcripts_failed,
        total_deleted=result.total_deleted,
        total_failed=result.total_failed,
        started_at=result.started_at,
        completed_at=result.completed_at,
        error_message=result.error_message,
    )


@router.post("/gdpr", response_model=GDPRRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_gdpr_request(
    body: CreateGDPRRequestBody,
    service: GDPRDeletionService = Depends(get_gdpr_service),
) -> GDPRRequestResponse:
    """
    Create a GDPR deletion request.
    
    The request will be processed within 72 hours.
    Requires admin role.
    """
    logger.info(
        "GDPR deletion request created via API",
        extra={"contact_id": str(body.contact_id)}
    )
    
    request = await service.create_deletion_request(
        contact_id=body.contact_id,
        contact_phone=body.contact_phone,
        contact_email=body.contact_email,
    )
    
    return GDPRRequestResponse(
        id=str(request.id),
        contact_id=str(request.contact_id),
        status=request.status.value,
        requested_at=request.requested_at,
        deadline=request.deadline,
        processed_at=request.processed_at,
        items_deleted=request.items_deleted,
        error_message=request.error_message,
    )


@router.get("/gdpr/{request_id}", response_model=GDPRRequestResponse)
async def get_gdpr_request_status(
    request_id: UUID,
    service: GDPRDeletionService = Depends(get_gdpr_service),
) -> GDPRRequestResponse:
    """
    Get the status of a GDPR deletion request.
    
    Requires admin role.
    """
    request = await service.get_request_status(request_id)
    
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GDPR request {request_id} not found"
        )
    
    return GDPRRequestResponse(
        id=str(request.id),
        contact_id=str(request.contact_id),
        status=request.status.value,
        requested_at=request.requested_at,
        deadline=request.deadline,
        processed_at=request.processed_at,
        items_deleted=request.items_deleted,
        error_message=request.error_message,
    )


@router.post("/gdpr/process")
async def process_gdpr_requests(
    service: GDPRDeletionService = Depends(get_gdpr_service),
) -> dict:
    """
    Trigger immediate processing of pending GDPR requests.
    
    Requires admin role.
    """
    logger.info("Manual GDPR processing triggered via API")
    
    processed = await service.process_pending_requests()
    
    return {
        "processed_count": len(processed),
        "requests": [
            {
                "id": str(r.id),
                "status": r.status.value,
                "items_deleted": r.items_deleted,
            }
            for r in processed
        ]
    }


@router.get("/status", response_model=RetentionStatusResponse)
async def get_retention_status(
    scheduler: RetentionScheduler = Depends(get_scheduler),
    gdpr_service: GDPRDeletionService = Depends(get_gdpr_service),
) -> RetentionStatusResponse:
    """
    Get current retention system status.
    
    Requires admin role.
    """
    pending = await gdpr_service._repository.get_pending_gdpr_requests()
    overdue = await gdpr_service.get_overdue_requests()
    
    return RetentionStatusResponse(
        scheduler_running=scheduler._running,
        last_job_id=None,  # Would need to track this in scheduler
        last_job_status=None,
        last_job_completed_at=None,
        pending_gdpr_requests=len(pending),
        overdue_gdpr_requests=len(overdue),
    )