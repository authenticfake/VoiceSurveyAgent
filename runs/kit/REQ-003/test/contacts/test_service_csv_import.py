from __future__ import annotations

import io
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.contacts.persistence.repository import (
    ContactFilters,
    Pagination,
    SqlAlchemyContactRepository,
    SqlAlchemyExclusionListRepository,
)
from app.contacts.services.service import ContactService
from app.contacts.csv_import.importer import ContactCSVImporter


CSV_TEMPLATE = """external_contact_id,phone_number,email,language,has_prior_consent,do_not_call
{external_contact_id},{phone},{email},{language},{consent},{dnc}
"""


def _service(session: Session) -> ContactService:
    repository = SqlAlchemyContactRepository(session)
    exclusion_repository = SqlAlchemyExclusionListRepository(session)
    importer = ContactCSVImporter(repository=repository, exclusion_repository=exclusion_repository)
    return ContactService(repository=repository, importer=importer)


def test_csv_import_persists_contacts(db_session: Session):
    campaign_id = uuid4()
    csv_data = "".join(
        [
            CSV_TEMPLATE.format(
                external_contact_id="ext-1",
                phone="+1 555-000-0001",
                email="a@example.com",
                language="en",
                consent="true",
                dnc="false",
            ),
            CSV_TEMPLATE.format(
                external_contact_id="ext-2",
                phone="+1 555-000-0002",
                email="b@example.com",
                language="it",
                consent="false",
                dnc="true",
            ),
        ]
    )
    service = _service(db_session)
    result = service.import_contacts(campaign_id, io.BytesIO(csv_data.encode("utf-8")))

    assert result.accepted_rows == 2
    records = service.repository.list_contacts(
        campaign_id,
        ContactFilters(),
        Pagination(page=1, page_size=10),
    )
    assert len(records) == 2
    excluded = [record for record in records if record.state.value == "excluded"]
    assert len(excluded) == 1


def test_csv_import_rejects_invalid_rows(db_session: Session):
    campaign_id = uuid4()
    csv_data = "".join(
        [
            CSV_TEMPLATE.format(
                external_contact_id="ext-1",
                phone="invalid-phone",
                email="not-an-email",
                language="es",
                consent="true",
                dnc="false",
            ),
        ]
    )
    service = _service(db_session)
    result = service.import_contacts(campaign_id, io.BytesIO(csv_data.encode("utf-8")))

    assert result.accepted_rows == 0
    assert result.rejected_rows == result.total_rows
    assert len(result.errors) >= 1