from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol, Sequence, Set
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.contacts.csv_import.models import ContactCandidate
from app.contacts.domain.enums import ContactState
from app.contacts.domain.models import ContactRecord
from app.contacts.persistence.models import ContactModel, ExclusionListEntryModel


@dataclass(frozen=True)
class ContactFilters:
    state: ContactState | None = None


@dataclass(frozen=True)
class Pagination:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class ContactRepository(Protocol):
    def bulk_insert_contacts(self, campaign_id: UUID, rows: Sequence[ContactCandidate]) -> int: ...

    def find_existing_numbers(self, campaign_id: UUID, phones: Iterable[str]) -> Set[str]: ...

    def list_contacts(self, campaign_id: UUID, filters: ContactFilters, pagination: Pagination) -> Sequence[ContactRecord]: ...

    def count_contacts(self, campaign_id: UUID, filters: ContactFilters | None = None) -> int: ...

    def count_state(self, campaign_id: UUID, state: ContactState) -> int: ...


class ExclusionListRepository(Protocol):
    def find_numbers(self, phones: Iterable[str]) -> Set[str]: ...


class SqlAlchemyContactRepository(ContactRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def bulk_insert_contacts(self, campaign_id: UUID, rows: Sequence[ContactCandidate]) -> int:
        now = datetime.utcnow()
        models = [
            ContactModel(
                campaign_id=campaign_id,
                external_contact_id=row.external_contact_id,
                phone_number=row.phone_number,
                email=row.email,
                preferred_language=row.preferred_language,
                has_prior_consent=int(row.has_prior_consent),
                do_not_call=int(row.do_not_call),
                state=row.state,
                created_at=now,
                updated_at=now,
            )
            for row in rows
        ]
        self.session.bulk_save_objects(models)
        self.session.commit()
        return len(models)

    def find_existing_numbers(self, campaign_id: UUID, phones: Iterable[str]) -> Set[str]:
        phone_list = list(phones)
        if not phone_list:
            return set()
        stmt = select(ContactModel.phone_number).where(
            ContactModel.campaign_id == campaign_id,
            ContactModel.phone_number.in_(phone_list),
        )
        result = self.session.execute(stmt).scalars().all()
        return set(result)

    def list_contacts(
        self, campaign_id: UUID, filters: ContactFilters, pagination: Pagination
    ) -> Sequence[ContactRecord]:
        stmt = (
            select(ContactModel)
            .where(ContactModel.campaign_id == campaign_id)
            .order_by(ContactModel.created_at.asc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        if filters.state:
            stmt = stmt.where(ContactModel.state == filters.state)
        models = self.session.execute(stmt).scalars().all()
        return [self._to_domain(model) for model in models]

    def count_contacts(self, campaign_id: UUID, filters: ContactFilters | None = None) -> int:
        stmt = select(func.count()).select_from(ContactModel).where(ContactModel.campaign_id == campaign_id)
        if filters and filters.state:
            stmt = stmt.where(ContactModel.state == filters.state)
        return int(self.session.execute(stmt).scalar_one())

    def count_state(self, campaign_id: UUID, state: ContactState) -> int:
        stmt = select(func.count()).select_from(ContactModel).where(
            ContactModel.campaign_id == campaign_id, ContactModel.state == state
        )
        return int(self.session.execute(stmt).scalar_one())

    def _to_domain(self, model: ContactModel) -> ContactRecord:
        return ContactRecord(
            id=model.id,
            campaign_id=model.campaign_id,
            external_contact_id=model.external_contact_id,
            phone_number=model.phone_number,
            email=model.email,
            preferred_language=model.preferred_language,
            state=model.state,
            attempts_count=model.attempts_count,
            last_attempt_at=model.last_attempt_at,
            last_outcome=model.last_outcome,
            has_prior_consent=bool(model.has_prior_consent),
            do_not_call=bool(model.do_not_call),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyExclusionListRepository(ExclusionListRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_numbers(self, phones: Iterable[str]) -> Set[str]:
        phone_list = list(phones)
        if not phone_list:
            return set()
        stmt = select(ExclusionListEntryModel.phone_number).where(
            ExclusionListEntryModel.phone_number.in_(phone_list)
        )
        result = self.session.execute(stmt).scalars().all()
        return set(result)