"""
Contact service for business logic.

REQ-006: Contact CSV upload and parsing
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.campaigns.repository import CampaignRepository
from app.contacts.csv_parser import CSVParser
from app.contacts.models import Contact, ContactLanguage, ContactState
from app.contacts.repository import ContactRepository
from app.contacts.schemas import (
    ContactListResponse,
    ContactResponse,
    CSVRowError,
    CSVUploadResponse,
)
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.logging import get_logger

logger = get_logger(__name__)


class ContactService:
    """Service for contact management operations."""

    def __init__(
        self,
        session: AsyncSession,
        contact_repository: ContactRepository | None = None,
        campaign_repository: CampaignRepository | None = None,
    ) -> None:
        """Initialize contact service.

        Args:
            session: Async database session.
            contact_repository: Optional contact repository (for DI).
            campaign_repository: Optional campaign repository (for DI).
        """
        self._session = session
        self._contact_repo = contact_repository or ContactRepository(session)
        self._campaign_repo = campaign_repository or CampaignRepository(session)

    async def upload_csv(
        self,
        campaign_id: UUID,
        content: bytes,
        delimiter: str = ",",
        encoding: str = "utf-8",
    ) -> CSVUploadResponse:
        """Upload and process a CSV file of contacts.

        Args:
            campaign_id: Campaign UUID to add contacts to.
            content: Raw CSV file content.
            delimiter: CSV field delimiter.
            encoding: File encoding.

        Returns:
            Upload result with accepted/rejected counts and errors.

        Raises:
            NotFoundError: If campaign not found.
            ValidationError: If campaign is not in draft status.
        """
        # Verify campaign exists and is in draft status
        campaign = await self._campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign {campaign_id} not found")

        if campaign.status.value != "draft":
            raise ValidationError(
                f"Cannot upload contacts to campaign in '{campaign.status.value}' status. "
                "Campaign must be in 'draft' status."
            )

        # Parse CSV
        parser = CSVParser(delimiter=delimiter, encoding=encoding)

        valid_contacts: list[Contact] = []
        errors: list[CSVRowError] = []
        total_rows = 0
        seen_phones: set[str] = set()

        for line_num, parsed, error in parser.parse(content):
            if error:
                # Line 0 errors are file-level errors
                if error.line_number == 0:
                    errors.append(error)
                    continue
                errors.append(error)
                total_rows += 1
                continue

            if parsed:
                total_rows += 1

                # Check for duplicate phone numbers within the file
                if parsed.phone_number in seen_phones:
                    errors.append(
                        CSVRowError(
                            line_number=line_num,
                            field="phone_number",
                            error="Duplicate phone number in file",
                            value=parsed.phone_number,
                        )
                    )
                    continue

                seen_phones.add(parsed.phone_number)

                # Check for existing contact with same phone in campaign
                existing = await self._contact_repo.get_by_phone_and_campaign(
                    parsed.phone_number,
                    campaign_id,
                )
                if existing:
                    errors.append(
                        CSVRowError(
                            line_number=line_num,
                            field="phone_number",
                            error="Contact with this phone number already exists in campaign",
                            value=parsed.phone_number,
                        )
                    )
                    continue

                # Create contact entity
                contact = Contact(
                    campaign_id=campaign_id,
                    external_contact_id=parsed.external_contact_id,
                    phone_number=parsed.phone_number,
                    email=parsed.email,
                    preferred_language=parsed.language,
                    has_prior_consent=parsed.has_prior_consent,
                    do_not_call=parsed.do_not_call,
                    state=ContactState.PENDING,
                    attempts_count=0,
                )
                valid_contacts.append(contact)

        # Bulk insert valid contacts
        if valid_contacts:
            await self._contact_repo.create_bulk(valid_contacts)
            await self._session.commit()

            logger.info(
                "CSV upload completed",
                extra={
                    "campaign_id": str(campaign_id),
                    "accepted_count": len(valid_contacts),
                    "rejected_count": len(errors),
                    "total_rows": total_rows,
                },
            )

        # Calculate acceptance rate
        acceptance_rate = (
            len(valid_contacts) / total_rows if total_rows > 0 else 0.0
        )

        return CSVUploadResponse(
            accepted_count=len(valid_contacts),
            rejected_count=len(errors),
            total_rows=total_rows,
            errors=errors,
            acceptance_rate=acceptance_rate,
        )

    async def get_contacts(
        self,
        campaign_id: UUID,
        page: int = 1,
        page_size: int = 50,
        state: ContactState | None = None,
    ) -> ContactListResponse:
        """Get contacts for a campaign with pagination.

        Args:
            campaign_id: Campaign UUID.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            state: Optional state filter.

        Returns:
            Paginated contact list.

        Raises:
            NotFoundError: If campaign not found.
        """
        # Verify campaign exists
        campaign = await self._campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign {campaign_id} not found")

        contacts, total = await self._contact_repo.get_by_campaign(
            campaign_id=campaign_id,
            page=page,
            page_size=page_size,
            state=state,
        )

        pages = (total + page_size - 1) // page_size if total > 0 else 0

        return ContactListResponse(
            items=[ContactResponse.model_validate(c) for c in contacts],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_contact(self, contact_id: UUID) -> ContactResponse:
        """Get a single contact by ID.

        Args:
            contact_id: Contact UUID.

        Returns:
            Contact response.

        Raises:
            NotFoundError: If contact not found.
        """
        contact = await self._contact_repo.get_by_id(contact_id)
        if not contact:
            raise NotFoundError(f"Contact {contact_id} not found")

        return ContactResponse.model_validate(contact)