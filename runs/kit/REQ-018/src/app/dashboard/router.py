"""
Dashboard API router for stats and exports.

REQ-017: Campaign dashboard stats API
REQ-018: Campaign CSV export
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.export_service import ExportService
from app.dashboard.schemas import (
    ExportJobCreateResponse,
    ExportJobResponse,
)
from app.dashboard.storage import StorageProvider, get_storage_provider
from app.shared.auth import CurrentUser, require_campaign_manager
from app.shared.database import get_db_session
from app.shared.exceptions import ExportError, NotFoundError
from app.shared.models import ExportJobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["dashboard"])


async def get_export_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> ExportService:
    """Dependency for export service."""
    return ExportService(db=db, storage=storage)


async def process_export_background(
    job_id: UUID,
    db_url: str,
    storage_provider: StorageProvider,
):
    """Background task to process export job."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        service = ExportService(db=session, storage=storage_provider)
        try:
            await service.process_export_job(job_id)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(
                "Background export failed",
                extra={"job_id": str(job_id), "error": str(e)},
            )
        finally:
            await session.close()

    await engine.dispose()


@router.get(
    "/{campaign_id}/export",
    response_model=ExportJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def initiate_export(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Initiate a CSV export job for a campaign.

    Returns immediately with job ID. Export is processed asynchronously.
    Only campaign_manager and admin roles can export.
    """
    try:
        job = await export_service.create_export_job(
            campaign_id=campaign_id,
            user_id=current_user.id,
        )
        await db.commit()

        # Schedule background processing
        from app.shared.config import get_settings
        settings = get_settings()

        background_tasks.add_task(
            process_export_background,
            job.id,
            settings.database_url,
            storage,
        )

        logger.info(
            "Export initiated",
            extra={
                "job_id": str(job.id),
                "campaign_id": str(campaign_id),
                "user_id": str(current_user.id),
            },
        )

        return ExportJobCreateResponse(
            job_id=job.id,
            status=job.status,
            message="Export job created. Check status at /api/exports/{job_id}",
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except Exception as e:
        logger.error(
            "Failed to initiate export",
            extra={
                "campaign_id": str(campaign_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate export",
        )


@router.get(
    "/{campaign_id}/exports",
    response_model=list[ExportJobResponse],
)
async def list_campaign_exports(
    campaign_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
    limit: int = 10,
):
    """
    List recent export jobs for a campaign.

    Only campaign_manager and admin roles can view exports.
    """
    jobs = await export_service.get_campaign_export_jobs(
        campaign_id=campaign_id,
        limit=limit,
    )
    return [ExportJobResponse.model_validate(job) for job in jobs]


# Separate router for export job operations
export_router = APIRouter(prefix="/api/exports", tags=["exports"])


@export_router.get(
    "/{job_id}",
    response_model=ExportJobResponse,
)
async def get_export_job(
    job_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
):
    """
    Get export job status and download URL.

    Only campaign_manager and admin roles can view exports.
    """
    job = await export_service.get_export_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export job with id '{job_id}' not found",
        )
    return ExportJobResponse.model_validate(job)


@export_router.post(
    "/{job_id}/refresh-url",
    response_model=ExportJobResponse,
)
async def refresh_export_url(
    job_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_campaign_manager)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Refresh the download URL for a completed export job.

    Only campaign_manager and admin roles can refresh URLs.
    """
    try:
        job = await export_service.refresh_download_url(job_id)
        await db.commit()
        return ExportJobResponse.model_validate(job)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except ExportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )