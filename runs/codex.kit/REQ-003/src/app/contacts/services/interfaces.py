from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

from app.contacts.domain.models import ContactImportResult, ContactListPage, ContactRecord
from app.contacts.persistence.repository import ContactFilters, Pagination


@dataclass(frozen=True)
class ContactListParams:
    campaign_id: UUID
    filters: ContactFilters
    pagination: Pagination


class ContactServiceProtocol(Protocol):
    def import_contacts(self, campaign_id: UUID, payload: BinaryIO) -> ContactImportResult: ...

    def list_contacts(self, params: ContactListParams) -> ContactListPage: ...

    def get_contact(self, campaign_id: UUID, contact_id: UUID) -> ContactRecord: ...