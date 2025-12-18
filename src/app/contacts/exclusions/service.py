"""
Service layer for exclusion list management.

REQ-007: Exclusion list management
"""

import csv
import io
import re
from typing import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.exclusions.models import ExclusionListEntry, ExclusionSource
from app.contacts.exclusions.repository import ExclusionRepository
from app.contacts.exclusions.schemas import (
    ExclusionCreateRequest,
    ExclusionImportError,
    ExclusionImportResponse,
)
from app.contacts.models import Contact, ContactState
from app.shared.logging import get_logger

logger = get_logger(__name__)

# E.164 phone number pattern
E164_PATTERN = re.compile(r"^\+[1-9]\d{6,14}$")


def normalize_phone_number(phone: str) -> str | None:
    """Normalize phone number to E.164 format.

    Args:
        phone: Raw phone number string.

    Returns:
        Normalized phone number or None if invalid.
    """
    if not phone:
        return None

    # Remove common formatting characters
    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone.strip())

    # If already in E.164 format
    if E164_PATTERN.match(cleaned):
        return cleaned

    # If starts with 00, replace with +
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
        if E164_PATTERN.match(cleaned):
            return cleaned

    # If it's just digits, we can't reliably determine country code
    # Return None to indicate validation failure
    return None


class ExclusionService:
    """Service for exclusion list management operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session.

        Args:
            session: Async database session.
        """
        self._session = session
        self._repository = ExclusionRepository(session)

    async def get_exclusion(self, exclusion_id: UUID) -> ExclusionListEntry | None:
        """Get exclusion entry by ID.

        Args:
            exclusion_id: Exclusion entry UUID.

        Returns:
            ExclusionListEntry if found, None otherwise.
        """
        return await self._repository.get_by_id(exclusion_id)

    async def is_excluded(self, phone_number: str) -> bool:
        """Check if a phone number is in the exclusion list.

        Args:
            phone_number: Phone number to check.

        Returns:
            True if excluded, False otherwise.
        """
        normalized = normalize_phone_number(phone_number)
        if not normalized:
            # If we can't normalize, check the raw value
            return await self._repository.exists(phone_number)
        return await self._repository.exists(normalized)

    async def get_excluded_phones(self, phone_numbers: list[str]) -> set[str]:
        """Get which phone numbers from a list are excluded.

        Args:
            phone_numbers: List of phone numbers to check.

        Returns:
            Set of excluded phone numbers (in their original format).
        """
        if not phone_numbers:
            return set()

        # Build mapping of normalized -> original
        normalized_map: dict[str, str] = {}
        for phone in phone_numbers:
            normalized = normalize_phone_number(phone)
            if normalized:
                normalized_map[normalized] = phone
            else:
                # Keep original for non-normalizable numbers
                normalized_map[phone] = phone

        # Check which normalized numbers are excluded
        excluded_normalized = await self._repository.exists_bulk(
            list(normalized_map.keys())
        )

        # Return original phone numbers
        return {normalized_map[n] for n in excluded_normalized if n in normalized_map}

    async def create_exclusion(
        self,
        request: ExclusionCreateRequest,
        source: ExclusionSource = ExclusionSource.API,
    ) -> ExclusionListEntry:
        """Create a new exclusion entry.

        Args:
            request: Exclusion creation request.
            source: Source of the exclusion.

        Returns:
            Created ExclusionListEntry.

        Raises:
            ValueError: If phone number is invalid or already excluded.
        """
        normalized = normalize_phone_number(request.phone_number)
        if not normalized:
            raise ValueError(f"Invalid phone number format: {request.phone_number}")

        # Check if already exists
        existing = await self._repository.get_by_phone(normalized)
        if existing:
            raise ValueError(f"Phone number already in exclusion list: {normalized}")

        entry = await self._repository.create(
            phone_number=normalized,
            source=source,
            reason=request.reason,
        )

        logger.info(
            "Created exclusion entry",
            extra={
                "exclusion_id": str(entry.id),
                "phone_number": normalized,
                "source": source.value,
            },
        )

        return entry

    async def delete_exclusion(self, exclusion_id: UUID) -> bool:
        """Delete an exclusion entry.

        Args:
            exclusion_id: Exclusion entry UUID.

        Returns:
            True if deleted, False if not found.
        """
        deleted = await self._repository.delete(exclusion_id)
        if deleted:
            logger.info(
                "Deleted exclusion entry",
                extra={"exclusion_id": str(exclusion_id)},
            )
        return deleted

    async def list_exclusions(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[Sequence[ExclusionListEntry], int]:
        """List all exclusion entries with pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Number of entries per page.

        Returns:
            Tuple of (entries, total_count).
        """
        return await self._repository.list_all(page=page, page_size=page_size)

    async def import_csv(
        self,
        csv_content: str | bytes,
        reason: str | None = None,
    ) -> ExclusionImportResponse:
        """Import exclusion entries from CSV content.

        CSV format: phone_number (required), reason (optional)

        Args:
            csv_content: CSV file content as string or bytes.
            reason: Default reason to apply if not in CSV.

        Returns:
            Import result with counts and errors.
        """
        if isinstance(csv_content, bytes):
            csv_content = csv_content.decode("utf-8-sig")

        errors: list[ExclusionImportError] = []
        valid_entries: list[tuple[str, ExclusionSource, str | None]] = []
        seen_phones: set[str] = set()

        reader = csv.DictReader(io.StringIO(csv_content))

        # Validate header
        if not reader.fieldnames:
            return ExclusionImportResponse(
                accepted_count=0,
                rejected_count=0,
                duplicate_count=0,
                errors=[
                    ExclusionImportError(
                        line_number=1,
                        phone_number=None,
                        error="CSV file is empty or has no header",
                    )
                ],
            )

        # Normalize field names
        fieldnames = [f.lower().strip() for f in reader.fieldnames]
        if "phone_number" not in fieldnames and "phone" not in fieldnames:
            return ExclusionImportResponse(
                accepted_count=0,
                rejected_count=0,
                duplicate_count=0,
                errors=[
                    ExclusionImportError(
                        line_number=1,
                        phone_number=None,
                        error="CSV must have 'phone_number' or 'phone' column",
                    )
                ],
            )

        phone_col = "phone_number" if "phone_number" in fieldnames else "phone"
        reason_col = "reason" if "reason" in fieldnames else None

        for line_num, row in enumerate(reader, start=2):
            # Normalize row keys
            row = {k.lower().strip(): v for k, v in row.items()}

            raw_phone = row.get(phone_col, "").strip()
            if not raw_phone:
                errors.append(
                    ExclusionImportError(
                        line_number=line_num,
                        phone_number=None,
                        error="Phone number is required",
                    )
                )
                continue

            normalized = normalize_phone_number(raw_phone)
            if not normalized:
                errors.append(
                    ExclusionImportError(
                        line_number=line_num,
                        phone_number=raw_phone,
                        error="Invalid phone number format (must be E.164)",
                    )
                )
                continue

            # Check for duplicates within the file
            if normalized in seen_phones:
                errors.append(
                    ExclusionImportError(
                        line_number=line_num,
                        phone_number=raw_phone,
                        error="Duplicate phone number in file",
                    )
                )
                continue

            seen_phones.add(normalized)

            # Get reason from row or use default
            row_reason = row.get(reason_col, "").strip() if reason_col else ""
            entry_reason = row_reason if row_reason else reason

            valid_entries.append((normalized, ExclusionSource.IMPORT, entry_reason))

        # Bulk insert valid entries
        inserted_count = 0
        if valid_entries:
            inserted_count = await self._repository.create_bulk(valid_entries)

        duplicate_count = len(valid_entries) - inserted_count

        logger.info(
            "CSV import completed",
            extra={
                "accepted_count": inserted_count,
                "rejected_count": len(errors),
                "duplicate_count": duplicate_count,
                "total_rows": len(valid_entries) + len(errors),
            },
        )

        return ExclusionImportResponse(
            accepted_count=inserted_count,
            rejected_count=len(errors),
            duplicate_count=duplicate_count,
            errors=errors,
        )

    async def mark_contacts_excluded(self, campaign_id: UUID | None = None) -> int:
        """Mark contacts as excluded if their phone is in exclusion list.

        Args:
            campaign_id: Optional campaign ID to limit scope.

        Returns:
            Number of contacts marked as excluded.
        """
        from sqlalchemy import select, update

        from app.contacts.models import Contact

        # Build query for contacts to check
        stmt = select(Contact.id, Contact.phone_number).where(
            Contact.state.in_([ContactState.PENDING, ContactState.NOT_REACHED]),
            Contact.do_not_call == False,  # noqa: E712
        )
        if campaign_id:
            stmt = stmt.where(Contact.campaign_id == campaign_id)

        result = await self._session.execute(stmt)
        contacts = result.fetchall()

        if not contacts:
            return 0

        # Get phone numbers and check exclusions
        phone_to_ids: dict[str, list[UUID]] = {}
        for contact_id, phone in contacts:
            normalized = normalize_phone_number(phone) or phone
            if normalized not in phone_to_ids:
                phone_to_ids[normalized] = []
            phone_to_ids[normalized].append(contact_id)

        excluded_phones = await self._repository.exists_bulk(list(phone_to_ids.keys()))

        if not excluded_phones:
            return 0

        # Collect contact IDs to update
        contact_ids_to_exclude: list[UUID] = []
        for phone in excluded_phones:
            contact_ids_to_exclude.extend(phone_to_ids.get(phone, []))

        if not contact_ids_to_exclude:
            return 0

        # Update contacts
        update_stmt = (
            update(Contact)
            .where(Contact.id.in_(contact_ids_to_exclude))
            .values(state=ContactState.EXCLUDED, do_not_call=True)
        )
        await self._session.execute(update_stmt)

        logger.info(
            "Marked contacts as excluded",
            extra={
                "count": len(contact_ids_to_exclude),
                "campaign_id": str(campaign_id) if campaign_id else "all",
            },
        )

        return len(contact_ids_to_exclude)