from fastapi import Depends
from sqlalchemy.orm import Session

from app.campaigns.persistence.repository import SqlAlchemyCampaignRepository
from app.campaigns.services.interfaces import ContactStats, ContactStatsProvider
from app.campaigns.services.service import CampaignService
from app.infra.db.session import get_db_session


class NullContactStatsProvider(ContactStatsProvider):
    def get_stats(self, campaign_id):
        raise RuntimeError(
            "Contact statistics provider is not configured. "
            "Wire an implementation once REQ-003 is available."
        )


def get_contact_stats_provider() -> ContactStatsProvider:
    return NullContactStatsProvider()


def get_campaign_service(
    session: Session = Depends(get_db_session),
    stats_provider: ContactStatsProvider = Depends(get_contact_stats_provider),
) -> CampaignService:
    repository = SqlAlchemyCampaignRepository(session)
    return CampaignService(repository=repository, contact_stats_provider=stats_provider)