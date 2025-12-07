from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.campaigns.persistence.repository import SqlAlchemyCampaignRepository
from app.campaigns.services.interfaces import ContactStatsProvider
from app.campaigns.services.service import CampaignService
from app.contacts.persistence.repository import SqlAlchemyContactRepository
from app.contacts.services.stats import SqlContactStatsProvider
from app.infra.db.session import get_db_session


def get_contact_stats_provider(session: Session = Depends(get_db_session)) -> ContactStatsProvider:
    contact_repo = SqlAlchemyContactRepository(session)  # type: ignore[arg-type]
    return SqlContactStatsProvider(session)


def get_campaign_service(
    session: Session = Depends(get_db_session),
    stats_provider: ContactStatsProvider = Depends(get_contact_stats_provider),
) -> CampaignService:
    repository = SqlAlchemyCampaignRepository(session)
    return CampaignService(repository=repository, contact_stats_provider=stats_provider)