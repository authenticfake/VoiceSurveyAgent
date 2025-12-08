from __future__ import annotations

from typing import BinaryIO
from uuid import UUID

from app.contacts.csv_import.importer import ContactCSVImporter
from app.contacts.domain.errors import ContactImportFailedError
from app.contacts.domain.models import ContactImportResult, ContactListPage
from app.contacts.persistence.repository import (
    ContactFilters,
    ContactRepository,
    Pagination,
)
from app.contacts.services.interfaces import ContactListParams
from app.contacts.services.stats import SqlContactStatsProvider


class ContactService:
    def __init__(
        self,
        repository: ContactRepository,
        importer: ContactCSVImporter,
    ) -> None:
        self.repository = repository
        self.importer = importer

    def import_contacts(self, campaign_id: UUID, payload: BinaryIO) -> ContactImportResult:
        try:
            return self.importer.import_contacts(campaign_id, payload)
        except Exception as exc:  # pragma: no cover
            raise ContactImportFailedError("Failed to import contacts") from exc

    def list_contacts(self, params: ContactListParams) -> ContactListPage:
        contacts = self.repository.list_contacts(params.campaign_id, params.filters, params.pagination)
        total = self.repository.count_contacts(params.campaign_id, params.filters)
        return ContactListPage(
            contacts=contacts,
            total=total,
            page=params.pagination.page,
            page_size=params.pagination.page_size,
        )

    def stats_provider(self) -> SqlContactStatsProvider:
        if not isinstance(self.repository, SqlContactStatsProvider.RepositoryCompatible):
            raise RuntimeError("Repository does not expose session for stats provider.")
        return SqlContactStatsProvider(self.repository.session, self.repository.__class__)  # type: ignore[attr-defined]