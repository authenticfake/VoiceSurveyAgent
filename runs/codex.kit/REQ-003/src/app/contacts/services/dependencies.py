from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.contacts.csv_import.importer import ContactCSVImporter
from app.contacts.persistence.repository import (
    ContactRepository,
    Pagination,
    SqlAlchemyContactRepository,
    SqlAlchemyExclusionListRepository,
)
from app.contacts.services.service import ContactService
from app.infra.db.session import get_db_session


def get_contact_repository(session: Session = Depends(get_db_session)) -> ContactRepository:
    return SqlAlchemyContactRepository(session)


def get_exclusion_repository(session: Session = Depends(get_db_session)) -> SqlAlchemyExclusionListRepository:
    return SqlAlchemyExclusionListRepository(session)


def get_contact_service(
    repository: ContactRepository = Depends(get_contact_repository),
    exclusion_repository: SqlAlchemyExclusionListRepository = Depends(get_exclusion_repository),
) -> ContactService:
    importer = ContactCSVImporter(repository=repository, exclusion_repository=exclusion_repository)
    return ContactService(repository=repository, importer=importer)