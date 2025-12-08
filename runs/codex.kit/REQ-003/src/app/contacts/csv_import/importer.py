from __future__ import annotations

import csv
import io
from typing import BinaryIO, Iterable, List, Sequence, Tuple
from uuid import UUID

from app.contacts.csv_import.models import ContactCandidate, ContactCsvRow
from app.contacts.csv_import.validator import ContactRowValidator
from app.contacts.domain.enums import ContactState
from app.contacts.domain.errors import ContactCsvValidationError
from app.contacts.domain.models import ContactImportErrorDetail, ContactImportResult
from app.contacts.persistence.repository import (
    ContactRepository,
    ExclusionListRepository,
)


class ContactCSVImporter:
    def __init__(
        self,
        repository: ContactRepository,
        exclusion_repository: ExclusionListRepository,
        *,
        chunk_size: int = 500,
    ) -> None:
        self.repository = repository
        self.exclusion_repository = exclusion_repository
        self.validator = ContactRowValidator()
        self.chunk_size = chunk_size

    def import_contacts(self, campaign_id: UUID, payload: BinaryIO) -> ContactImportResult:
        reader = self._build_reader(payload)
        self.validator.ensure_headers(reader.fieldnames or [])
        parsed_rows, errors = self._parse_rows(reader)
        accepted_rows = self._filter_and_persist(campaign_id, parsed_rows, errors)
        total = len(parsed_rows) + len(errors)
        rejected = len(errors) + (len(parsed_rows) - accepted_rows)
        return ContactImportResult(
            total_rows=total,
            accepted_rows=accepted_rows,
            rejected_rows=rejected,
            errors=errors,
        )

    def _build_reader(self, payload: BinaryIO) -> csv.DictReader:
        payload.seek(0)
        text_stream = io.TextIOWrapper(payload, encoding="utf-8", newline="")
        return csv.DictReader(text_stream)

    def _parse_rows(
        self, reader: csv.DictReader
    ) -> Tuple[List[ContactCsvRow], List[ContactImportErrorDetail]]:
        parsed: List[ContactCsvRow] = []
        errors: List[ContactImportErrorDetail] = []
        for index, row in enumerate(reader, start=2):
            model, error = self.validator.parse_row(row)
            if error:
                errors.append(ContactImportErrorDetail(line_number=index, message=error))
                continue
            parsed.append(model)
        if not parsed and not errors:
            raise ContactCsvValidationError("CSV file does not contain any data rows.")
        return parsed, errors

    def _filter_and_persist(
        self,
        campaign_id: UUID,
        rows: Sequence[ContactCsvRow],
        errors: List[ContactImportErrorDetail],
    ) -> int:
        deduped: List[ContactCsvRow] = []
        seen: set[str] = set()
        for row in rows:
            if row.phone_number in seen:
                errors.append(
                    ContactImportErrorDetail(
                        line_number=-1,
                        message=f"Duplicate phone number {row.phone_number} within upload.",
                    )
                )
                continue
            seen.add(row.phone_number)
            deduped.append(row)

        existing = self.repository.find_existing_numbers(campaign_id, seen)
        if existing:
            for phone in sorted(existing):
                errors.append(
                    ContactImportErrorDetail(
                        line_number=-1, message=f"Phone number {phone} already exists."
                    )
                )
        valid_rows = [row for row in deduped if row.phone_number not in existing]
        if not valid_rows:
            return 0

        globally_excluded = self.exclusion_repository.find_numbers(row.phone_number for row in valid_rows)

        candidates = [
            ContactCandidate(
                external_contact_id=row.external_contact_id,
                phone_number=row.phone_number,
                email=row.email,
                preferred_language=row.preferred_language,
                has_prior_consent=row.has_prior_consent,
                do_not_call=row.do_not_call,
                state=ContactState.excluded
                if row.do_not_call or row.phone_number in globally_excluded
                else ContactState.pending,
            )
            for row in valid_rows
        ]

        inserted = 0
        for chunk in _chunks(candidates, self.chunk_size):
            inserted += self.repository.bulk_insert_contacts(campaign_id, chunk)
        return inserted


def _chunks(items: Sequence[ContactCandidate], chunk_size: int) -> Iterable[Sequence[ContactCandidate]]:
    for index in range(0, len(items), chunk_size):
        yield items[index : index + chunk_size]