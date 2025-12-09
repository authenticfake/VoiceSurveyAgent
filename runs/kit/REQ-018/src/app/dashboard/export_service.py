"""
Export service for generating campaign CSV exports.

REQ-018: Campaign CSV export
"""

import csv
import io
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dashboard.schemas import ContactExportRow, ExportJobResponse
from app.dashboard.storage import StorageProvider
from app.shared.config import get_settings
from app.shared.exceptions import ExportError, NotFoundError
from app.shared.models import (
    Campaign,
    Contact,
    ContactState,
    ExportJob,
    ExportJobStatus,
    SurveyResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class ExportService:
    """Service for managing campaign CSV exports."""

    def __init__(
        self,
        db: AsyncSession,
        storage: StorageProvider,
    ):
        self._db = db
        self._storage = storage

    async def create_export_job(
        self,
        campaign_id: UUID,
        user_id: UUID,
    ) -> ExportJob:
        """Create a new export job for a campaign."""
        # Verify campaign exists
        result = await self._db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundError("Campaign", campaign_id)

        # Create export job
        export_job = ExportJob(
            id=uuid4(),
            campaign_id=campaign_id,
            requested_by_user_id=user_id,
            status=ExportJobStatus.PENDING,
        )
        self._db.add(export_job)
        await self._db.flush()

        logger.info(
            "Export job created",
            extra={
                "job_id": str(export_job.id),
                "campaign_id": str(campaign_id),
                "user_id": str(user_id),
            },
        )

        return export_job

    async def process_export_job(self, job_id: UUID) -> ExportJob:
        """Process an export job - generate CSV and upload to storage."""
        # Get job
        result = await self._db.execute(
            select(ExportJob).where(ExportJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("ExportJob", job_id)

        # Update status to processing
        job.status = ExportJobStatus.PROCESSING
        await self._db.flush()

        try:
            # Generate CSV content
            csv_content, record_count = await self._generate_csv(job.campaign_id)

            # Generate S3 key
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            s3_key = f"{settings.s3_export_prefix}campaign_{job.campaign_id}_{timestamp}.csv"

            # Upload to storage
            await self._storage.upload_file(
                key=s3_key,
                content=csv_content.encode("utf-8"),
                content_type="text/csv",
            )

            # Generate presigned URL
            download_url, expires_at = await self._storage.generate_presigned_url(
                key=s3_key,
                expiration_seconds=settings.export_url_expiration_seconds,
            )

            # Update job with success
            job.status = ExportJobStatus.COMPLETED
            job.s3_key = s3_key
            job.download_url = download_url
            job.url_expires_at = expires_at
            job.total_records = record_count
            job.completed_at = datetime.utcnow()

            logger.info(
                "Export job completed",
                extra={
                    "job_id": str(job_id),
                    "campaign_id": str(job.campaign_id),
                    "total_records": record_count,
                    "s3_key": s3_key,
                },
            )

        except Exception as e:
            # Update job with failure
            job.status = ExportJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()

            logger.error(
                "Export job failed",
                extra={
                    "job_id": str(job_id),
                    "campaign_id": str(job.campaign_id),
                    "error": str(e),
                },
            )

            raise ExportError(
                message=f"Export failed: {str(e)}",
                job_id=job_id,
            )

        await self._db.flush()
        return job

    async def _generate_csv(self, campaign_id: UUID) -> tuple[str, int]:
        """Generate CSV content for a campaign."""
        # Query contacts with survey responses
        result = await self._db.execute(
            select(Contact)
            .options(selectinload(Contact.survey_response))
            .where(Contact.campaign_id == campaign_id)
            .order_by(Contact.created_at)
        )
        contacts = result.scalars().all()

        # Build CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        headers = [
            "campaign_id",
            "contact_id",
            "external_contact_id",
            "phone_number",
            "outcome",
            "attempt_count",
            "last_attempt_at",
            "completed_at",
            "q1_answer",
            "q2_answer",
            "q3_answer",
        ]
        writer.writerow(headers)

        # Write data rows
        record_count = 0
        for contact in contacts:
            # Only include contacts that reached a terminal state
            if contact.state not in [
                ContactState.COMPLETED,
                ContactState.REFUSED,
                ContactState.NOT_REACHED,
                ContactState.EXCLUDED,
            ]:
                continue

            row = ContactExportRow(
                campaign_id=campaign_id,
                contact_id=contact.id,
                external_contact_id=contact.external_contact_id,
                phone_number=contact.phone_number,
                outcome=contact.state,
                attempt_count=contact.attempts_count,
                last_attempt_at=contact.last_attempt_at,
                completed_at=(
                    contact.survey_response.completed_at
                    if contact.survey_response
                    else None
                ),
                q1_answer=(
                    contact.survey_response.q1_answer
                    if contact.survey_response
                    else None
                ),
                q2_answer=(
                    contact.survey_response.q2_answer
                    if contact.survey_response
                    else None
                ),
                q3_answer=(
                    contact.survey_response.q3_answer
                    if contact.survey_response
                    else None
                ),
            )

            writer.writerow([
                str(row.campaign_id),
                str(row.contact_id),
                row.external_contact_id or "",
                row.phone_number,
                row.outcome.value,
                row.attempt_count,
                row.last_attempt_at.isoformat() if row.last_attempt_at else "",
                row.completed_at.isoformat() if row.completed_at else "",
                row.q1_answer or "",
                row.q2_answer or "",
                row.q3_answer or "",
            ])
            record_count += 1

        return output.getvalue(), record_count

    async def get_export_job(self, job_id: UUID) -> Optional[ExportJob]:
        """Get export job by ID."""
        result = await self._db.execute(
            select(ExportJob).where(ExportJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_campaign_export_jobs(
        self,
        campaign_id: UUID,
        limit: int = 10,
    ) -> list[ExportJob]:
        """Get recent export jobs for a campaign."""
        result = await self._db.execute(
            select(ExportJob)
            .where(ExportJob.campaign_id == campaign_id)
            .order_by(ExportJob.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def refresh_download_url(self, job_id: UUID) -> ExportJob:
        """Refresh the download URL for a completed export job."""
        result = await self._db.execute(
            select(ExportJob).where(ExportJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("ExportJob", job_id)

        if job.status != ExportJobStatus.COMPLETED:
            raise ExportError(
                message="Cannot refresh URL for non-completed job",
                job_id=job_id,
            )

        if not job.s3_key:
            raise ExportError(
                message="Export job has no S3 key",
                job_id=job_id,
            )

        # Check if file still exists
        if not await self._storage.file_exists(job.s3_key):
            raise ExportError(
                message="Export file no longer exists",
                job_id=job_id,
            )

        # Generate new presigned URL
        download_url, expires_at = await self._storage.generate_presigned_url(
            key=job.s3_key,
            expiration_seconds=settings.export_url_expiration_seconds,
        )

        job.download_url = download_url
        job.url_expires_at = expires_at
        await self._db.flush()

        logger.info(
            "Export URL refreshed",
            extra={
                "job_id": str(job_id),
                "expires_at": expires_at.isoformat(),
            },
        )

        return job