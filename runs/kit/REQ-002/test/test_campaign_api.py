from __future__ import annotations

from typing import Dict
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.dependencies import get_current_user
from app.auth.domain.models import Role, UserPrincipal
from app.campaigns.domain.enums import CampaignStatus
from app.campaigns.persistence.repository import SqlAlchemyCampaignRepository
from app.campaigns.services.dependencies import get_campaign_service
from app.campaigns.services.interfaces import CampaignFilters, CampaignRepository, ContactStats, ContactStatsProvider
from app.campaigns.services.service import CampaignService
from app.infra.db.base import Base
from app.main import create_app

# Import models for metadata registration
from app.campaigns.persistence import models as campaign_models  # noqa: F401


class FakeContactStatsProvider(ContactStatsProvider):
    def __init__(self) -> None:
        self._stats: Dict[UUID, ContactStats] = {}

    def set_stats(self, campaign_id: UUID, stats: ContactStats) -> None:
        self._stats[campaign_id] = stats

    def get_stats(self, campaign_id: UUID) -> ContactStats:
        return self._stats.get(
            campaign_id,
            ContactStats(total_contacts=0, eligible_contacts=0, excluded_contacts=0),
        )


@pytest.fixture
def engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine) -> Session:
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def manager_user() -> UserPrincipal:
    return UserPrincipal(id=uuid4(), email="manager@example.com", role=Role.campaign_manager)


@pytest.fixture
def viewer_user() -> UserPrincipal:
    return UserPrincipal(id=uuid4(), email="viewer@example.com", role=Role.viewer)


@pytest.fixture
def app_bundle(db_session: Session, manager_user: UserPrincipal):
    fake_provider = FakeContactStatsProvider()
    repository = SqlAlchemyCampaignRepository(db_session)
    service = CampaignService(repository, fake_provider)
    app = create_app()
    app.dependency_overrides[get_campaign_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: manager_user
    yield {
        "app": app,
        "service": service,
        "provider": fake_provider,
        "manager": manager_user,
    }
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app_bundle):
    app = app_bundle["app"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8080") as client:
        yield client


def _build_payload(name: str = "Compliance Pilot"):
    return {
        "name": name,
        "description": "EU compliance survey",
        "language": "en",
        "intro_script": "Hello, we are conducting a survey.",
        "questions": [
            {"text": "How satisfied are you?", "answer_type": "scale"},
            {"text": "What can we improve?", "answer_type": "free_text"},
            {"text": "Would you recommend us?", "answer_type": "free_text"},
        ],
        "retry_policy": {"max_attempts": 3, "retry_interval_minutes": 10},
        "allowed_call_window": {"start_local": "09:00:00", "end_local": "18:00:00"},
        "email_templates": {
            "completed_template_id": None,
            "refused_template_id": None,
            "not_reached_template_id": None,
        },
    }


@pytest.mark.asyncio
async def test_create_campaign_success(client, app_bundle):
    response = await client.post("/api/campaigns", json=_build_payload())
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == CampaignStatus.draft.value
    assert len(payload["questions"]) == 3


@pytest.mark.asyncio
async def test_create_campaign_requires_role(client, app_bundle, viewer_user):
    app = app_bundle["app"]
    app.dependency_overrides[get_current_user] = lambda: viewer_user
    response = await client.post("/api/campaigns", json=_build_payload(name="Viewer Attempt"))
    assert response.status_code == 403
    app.dependency_overrides[get_current_user] = lambda: app_bundle["manager"]


@pytest.mark.asyncio
async def test_activate_campaign_requires_contacts(client, app_bundle):
    response = await client.post("/api/campaigns", json=_build_payload(name="No Contacts"))
    campaign_id = response.json()["id"]
    activation = await client.post(f"/api/campaigns/{campaign_id}/activate")
    assert activation.status_code == 400
    assert activation.json()["detail"]["code"] == "campaign_activation_error"


@pytest.mark.asyncio
async def test_activate_campaign_success(client, app_bundle):
    provider: FakeContactStatsProvider = app_bundle["provider"]
    response = await client.post("/api/campaigns", json=_build_payload(name="Ready Campaign"))
    campaign_id = UUID(response.json()["id"])
    provider.set_stats(
        campaign_id,
        ContactStats(total_contacts=5, eligible_contacts=5, excluded_contacts=0),
    )
    activation = await client.post(f"/api/campaigns/{campaign_id}/activate")
    assert activation.status_code == 200
    assert activation.json()["status"] == CampaignStatus.running.value


@pytest.mark.asyncio
async def test_list_campaigns_filters_by_status(client, app_bundle):
    provider: FakeContactStatsProvider = app_bundle["provider"]
    # create draft campaign
    await client.post("/api/campaigns", json=_build_payload(name="Draft Campaign"))
    # create another and activate
    response_running = await client.post("/api/campaigns", json=_build_payload(name="Running Campaign"))
    running_id = UUID(response_running.json()["id"])
    provider.set_stats(
        running_id,
        ContactStats(total_contacts=3, eligible_contacts=3, excluded_contacts=0),
    )
    await client.post(f"/api/campaigns/{running_id}/activate")
    listing = await client.get("/api/campaigns", params={"status": "running"})
    assert listing.status_code == 200
    body = listing.json()
    assert body["pagination"]["total_items"] == 1
    assert body["items"][0]["name"] == "Running Campaign"