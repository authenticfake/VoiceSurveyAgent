"""
Unit tests for export service.

REQ-018: Campaign CSV export
"""

import csv
import io
from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.export_service import ExportService
from app.dashboard.storage import InMemoryStorageProvider
from app.shared.exceptions import ExportError, NotFoundError
from app.shared.models import (
    Campaign,
    Contact,
    ExportJob,
    ExportJobStatus,
    User,
)


class TestExportService:
    """Tests for ExportService."""

    @pytest_asyncio.fixture
    async def storage(self) -> InMemoryStorageProvider:
        """Create in-memory storage for testing."""
        return InMemoryStorageProvider()

    @pytest_asyncio.fixture
    async def export_service(
        self,
        db_session: AsyncSession,
        storage: InMemoryStorageProvider,
    ) -> ExportService:
        """Create export service with test dependencies."""
        return ExportService(db=db_session, storage=storage)

    @pytest.mark.asyncio
    async def test_create_export_job_success(
        self,
        export_service: ExportService,
        test_campaign: Campaign,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test creating an export job successfully."""
        job = await export_service.create_export_job(
            campaign_id=test_campaign.id,
            user_id=test_user.id,
        )

        assert job is not None
        assert job.campaign_id == test_campaign.id
        assert job.requested_by_user_id == test_user.id
        assert job.status == ExportJobStatus.PENDING
        assert job.s3_key is None
        assert job.download_url is None

    @pytest.mark.asyncio
    async def test_create_export_job_campaign_not_found(
        self,
        export_service: ExportService,
        test_user: User,
    ):
        """Test creating export job for non-existent campaign."""
        with pytest.raises(NotFoundError) as exc_info:
            await export_service.create_export_job(
                campaign_id=uuid4(),
                user_id=test_user.id,
            )
        assert "Campaign" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_export_job_success(
        self,
        export_service: ExportService,
        storage: InMemoryStorageProvider,
        test_campaign: Campaign,
        test_user: User,
        test_contacts_with_responses: list[Contact],
        db_session: AsyncSession,
    ):
        """Test processing an export job successfully."""
        # Create job
        job = await export_service.create_export_job(
            campaign_id=test_campaign.id,
            user_id=test_user.id,
        )
        await db_session.flush()

        # Process job
        processed_job = await export_service.process_export_job(job.id)

        assert processed_job.status == ExportJobStatus.COMPLETED
        assert processed_job.s3_key is not None
        assert processed_job.download_url is not None
        assert processed_job.url_expires_at is not None
        assert processed_job.total_records == 3  # completed, refused, not_reached
        assert processed_job.completed_at is not None

        # Verify CSV content
        csv_content = storage.get_content(processed_job.s3_key)
        assert csv_content is not None

        reader = csv.DictReader(io.StringIO(csv_content.decode("utf-8")))
        rows = list(reader)

        assert len(rows) == 3
        outcomes = {row["outcome"] for row in rows}
        assert outcomes == {"completed", "refused", "not_reached"}

        # Verify completed contact has answers
        completed_row = next(r for r in rows if r["outcome"] == "completed")
        assert completed_row["q1_answer"] == "8"
        assert completed_row["q2_answer"] == "Better mobile app"
        assert completed_row["q3_answer"] == "9"

    @pytest.mark.asyncio
    async def test_process_export_job_not_found(
        self,
        export_service: ExportService,
    ):
        """Test processing non-existent export job."""
        with pytest.raises(NotFoundError) as exc_info:
            await export_service.process_export_job(uuid4())
        assert "ExportJob" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_export_job(
        self,
        export_service: ExportService,
        test_campaign: Campaign,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test getting an export job by ID."""
        job = await export_service.create_export_job(
            campaign_id=test_campaign.id,
            user_id=test_user.id,
        )
        await db_session.flush()

        retrieved_job = await export_service.get_export_job(job.id)

        assert retrieved_job is not None
        assert retrieved_job.id == job.id

    @pytest.mark.asyncio
    async def test_get_export_job_not_found(
        self,
        export_service: ExportService,
    ):
        """Test getting non-existent export job returns None."""
        job = await export_service.get_export_job(uuid4())
        assert job is None

    @pytest.mark.asyncio
    async def test_get_campaign_export_jobs(
        self,
        export_service: ExportService,
        test_campaign: Campaign,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test listing export jobs for a campaign."""
        # Create multiple jobs
        for _ in range(3):
            await export_service.create_export_job(
                campaign_id=test_campaign.id,
                user_id=test_user.id,
            )
        await db_session.flush()

        jobs = await export_service.get_campaign_export_jobs(
            campaign_id=test_campaign.id,
            limit=10,
        )

        assert len(jobs) == 3

    @pytest.mark.asyncio
    async def test_refresh_download_url_success(
        self,
        export_service: ExportService,
        storage: InMemoryStorageProvider,
        test_campaign: Campaign,
        test_user: User,
        test_contacts_with_responses: list[Contact],
        db_session: AsyncSession,
    ):
        """Test refreshing download URL for completed job."""
        # Create and process job
        job = await export_service.create_export_job(
            campaign_id=test_campaign.id,
            user_id=test_user.id,
        )
        await db_session.flush()
        processed_job = await export_service.process_export_job(job.id)

        original_url = processed_job.download_url

        # Refresh URL
        refreshed_job = await export_service.refresh_download_url(job.id)

        assert refreshed_job.download_url is not None
        assert refreshed_job.url_expires_at is not None
        # URL should be regenerated (may be same in mock)

    @pytest.mark.asyncio
    async def test_refresh_download_url_not_completed(
        self,
        export_service: ExportService,
        test_campaign: Campaign,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test refreshing URL for non-completed job fails."""
        job = await export_service.create_export_job(
            campaign_id=test_campaign.id,
            user_id=test_user.id,
        )
        await db_session.flush()

        with pytest.raises(ExportError) as exc_info:
            await export_service.refresh_download_url(job.id)
        assert "non-completed" in str(exc_info.value).lower()


class TestCSVGeneration:
    """Tests for CSV generation logic."""

    @pytest_asyncio.fixture
    async def storage(self) -> InMemoryStorageProvider:
        """Create in-memory storage for testing."""
        return InMemoryStorageProvider()

    @pytest_asyncio.fixture
    async def export_service(
        self,
        db_session: AsyncSession,
        storage: InMemoryStorageProvider,
    ) -> ExportService:
        """Create export service with test dependencies."""
        return ExportService(db=db_session, storage=storage)

    @pytest.mark.asyncio
    async def test_csv_headers(
        self,
        export_service: ExportService,
        storage: InMemoryStorageProvider,
        test_campaign: Campaign,
        test_user: User,
        test_contacts_with_responses: list[Contact],
        db_session: AsyncSession,
    ):
        """Test CSV has correct headers."""
        job = await export_service.create_export_job(
            campaign_id=test_campaign.id,
            user_id=test_user.id,
        )
        await db_session.flush()
        processed_job = await export_service.process_export_job(job.id)

        csv_content = storage.get_content(processed_job.s3_key)
        reader = csv.DictReader(io.StringIO(csv_content.decode("utf-8")))

        expected_headers = {
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
        }
        assert set(reader.fieldnames) == expected_headers

    @pytest.mark.asyncio
    async def test_csv_excludes_pending_contacts(
        self,
        export_service: ExportService,
        storage: InMemoryStorageProvider,
        test_campaign: Campaign,
        test_user: User,
        test_contacts_with_responses: list[Contact],
        db_session: AsyncSession,
    ):
        """Test CSV excludes pending and in-progress contacts."""
        job = await export_service.create_export_job(
            campaign_id=test_campaign.id,
            user_id=test_user.id,
        )
        await db_session.flush()
        processed_job = await export_service.process_export_job(job.id)

        csv_content = storage.get_content(processed_job.s3_key)
        reader = csv.DictReader(io.StringIO(csv_content.decode("utf-8")))
        rows = list(reader)

        outcomes = {row["outcome"] for row in rows}
        assert "pending" not in outcomes
        assert "in_progress" not in outcomes

    @pytest.mark.asyncio
    async def test_csv_no_duplicate_rows(
        self,
        export_service: ExportService,
        storage: InMemoryStorageProvider,
        test_campaign: Campaign,
        test_user: User,
        test_contacts_with_responses: list[Contact],
        db_session: AsyncSession,
    ):
        """Test CSV has no duplicate rows."""
        job = await export_service.create_export_job(
            campaign_id=test_campaign.id,
            user_id=test_user.id,
        )
        await db_session.flush()
        processed_job = await export_service.process_export_job(job.id)

        csv_content = storage.get_content(processed_job.s3_key)
        reader = csv.DictReader(io.StringIO(csv_content.decode("utf-8")))
        rows = list(reader)

        contact_ids = [row["contact_id"] for row in rows]
        assert len(contact_ids) == len(set(contact_ids))