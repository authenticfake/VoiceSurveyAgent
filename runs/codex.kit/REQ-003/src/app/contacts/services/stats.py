from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.campaigns.services.interfaces import ContactStats, ContactStatsProvider
from app.contacts.domain.enums import ContactState
from app.contacts.persistence.models import ContactModel


@dataclass
class SqlContactStatsProvider(ContactStatsProvider):
    session: Session

    def __init__(self, session: Session, *_: object) -> None:
        self.session = session

    def get_stats(self, campaign_id: UUID) -> ContactStats:
        total_stmt = select(func.count()).select_from(ContactModel).where(ContactModel.campaign_id == campaign_id)
        total = int(self.session.execute(total_stmt).scalar_one())

        eligible_stmt = select(func.count()).select_from(ContactModel).where(
            ContactModel.campaign_id == campaign_id,
            ContactModel.state.notin_([ContactState.excluded]),
        )
        eligible = int(self.session.execute(eligible_stmt).scalar_one())

        excluded_stmt = select(func.count()).select_from(ContactModel).where(
            ContactModel.campaign_id == campaign_id,
            ContactModel.state == ContactState.excluded,
        )
        excluded = int(self.session.execute(excluded_stmt).scalar_one())

        return ContactStats(total_contacts=total, eligible_contacts=eligible, excluded_contacts=excluded)