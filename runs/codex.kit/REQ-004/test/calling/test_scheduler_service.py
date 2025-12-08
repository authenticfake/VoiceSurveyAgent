from __future__ import annotations

from datetime import datetime, time, timezone
from typing import List
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.calling.scheduler.models import SchedulerSettings
from app.calling.scheduler.service import SchedulerService
from app.calling.telephony.models import OutboundCallRequest, OutboundCallResponse
from app.calling.telephony.provider import TelephonyProvider, TelephonyProviderError
from app.infra.db.base import Base
from app.infra.db import models as db_models


class FakeTelephonyProvider(TelephonyProvider):
    def __init__(self) -> None:
        self.requests: List[OutboundCallRequest] = []
        self.should_fail = False

    def start_outbound_call(self, request: OutboundCallRequest) -> OutboundCallResponse:
        if self.should_fail:
            raise TelephonyProviderError("provider unavailable")
        self.requests.append(request)
        return OutboundCallResponse(
            provider_call_id=f"prov-{len(self.requests)}",
            provider_status="queued",
            raw_payload={"status": "queued"},
        )


@pytest.fixture()
def session_factory() -> sessionmaker:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _bootstrap_provider_config(session: Session) -> None:
    provider = db_models.ProviderConfiguration(
        provider_type=db_models.ProviderType.TELEPHONY_API,
        provider_name="twilio",
        outbound_number="+12065550100",
        max_concurrent_calls=5,
        llm_provider=db_models.LlmProvider.OPENAI,
        llm_model="gpt-4.1-mini",
        recording_retention_days=180,
        transcript_retention_days=180,
    )
    session.add(provider)


def _bootstrap_campaign(session: Session) -> db_models.Campaign:
    user = db_models.User(
        oidc_sub="sub",
        email="owner@example.com",
        name="Owner",
        role=db_models.UserRole.ADMIN,
    )
    session.add(user)
    campaign = db_models.Campaign(
        name="Test",
        description="desc",
        status=db_models.CampaignStatus.RUNNING,
        language=db_models.CampaignLanguage.EN,
        intro_script="Hello ...",
        question_1_text="Q1",
        question_1_type=db_models.QuestionType.FREE_TEXT,
        question_2_text="Q2",
        question_2_type=db_models.QuestionType.NUMERIC,
        question_3_text="Q3",
        question_3_type=db_models.QuestionType.SCALE,
        max_attempts=3,
        retry_interval_minutes=5,
        allowed_call_start_local=time(8, 0),
        allowed_call_end_local=time(20, 0),
        created_by_user_id=user.id,
    )
    session.add(campaign)
    return campaign


def _create_contact(session: Session, campaign: db_models.Campaign, phone: str) -> db_models.Contact:
    contact = db_models.Contact(
        campaign_id=campaign.id,
        external_contact_id=None,
        phone_number=phone,
        email=None,
        preferred_language=db_models.ContactLanguage.AUTO,
        has_prior_consent=True,
        do_not_call=False,
        state=db_models.ContactState.PENDING,
        attempts_count=0,
    )
    session.add(contact)
    return contact


def test_scheduler_dispatches_contacts(session_factory: sessionmaker) -> None:
    provider = FakeTelephonyProvider()
    settings = SchedulerSettings(callback_url="https://example.com/webhook", batch_size=2)
    service = SchedulerService(
        session_factory=session_factory,
        telephony_provider=provider,
        settings=settings,
        clock=lambda: datetime(2024, 6, 1, 9, 0, tzinfo=timezone.utc),
        call_id_factory=lambda: "call-1",
    )

    with session_factory.begin() as session:
        _bootstrap_provider_config(session)
        campaign = _bootstrap_campaign(session)
        contact = _create_contact(session, campaign, "+15555550100")
        session.flush()
        contact_id = contact.id

    result = service.run()
    assert len(result.scheduled) == 1
    assert result.scheduled[0].contact_id == contact_id
    assert provider.requests[0].call_id == "call-1"

    with session_factory() as session:
        refreshed = session.get(db_models.Contact, contact_id)
        assert refreshed.state == db_models.ContactState.IN_PROGRESS
        assert refreshed.attempts_count == 1
        attempts = session.query(db_models.CallAttempt).filter_by(contact_id=contact_id).all()
        assert len(attempts) == 1
        assert attempts[0].provider_call_id.startswith("prov-")


def test_scheduler_respects_retry_interval(session_factory: sessionmaker) -> None:
    provider = FakeTelephonyProvider()
    now = datetime(2024, 6, 1, 9, 0, tzinfo=timezone.utc)
    settings = SchedulerSettings(callback_url="https://example.com/cb", batch_size=1)
    service = SchedulerService(
        session_factory=session_factory,
        telephony_provider=provider,
        settings=settings,
        clock=lambda: now,
        call_id_factory=lambda: uuid4().hex,
    )

    with session_factory.begin() as session:
        _bootstrap_provider_config(session)
        campaign = _bootstrap_campaign(session)
        contact = _create_contact(session, campaign, "+15555550111")
        contact.state = db_models.ContactState.NOT_REACHED
        contact.attempts_count = 1
        contact.last_attempt_at = now - timedelta(minutes=2)
        session.flush()
        contact_id = contact.id

    result = service.run()
    assert len(result.scheduled) == 0
    assert contact_id not in [a.contact_id for a in result.scheduled]
    assert contact_id not in result.skipped_contacts  # filtered before scheduling
    assert provider.requests == []


def test_scheduler_obeys_concurrency_limit(session_factory: sessionmaker) -> None:
    provider = FakeTelephonyProvider()
    settings = SchedulerSettings(callback_url="https://example.com/cb", batch_size=5)
    service = SchedulerService(
        session_factory=session_factory,
        telephony_provider=provider,
        settings=settings,
        clock=lambda: datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc),
    )

    with session_factory.begin() as session:
        _bootstrap_provider_config(session)
        campaign = _bootstrap_campaign(session)
        # simulate all slots already in use by leaving ended_at NULL
        session.add(
            db_models.CallAttempt(
                contact_id=_create_contact(session, campaign, "+15555550222").id,
                campaign_id=campaign.id,
                attempt_number=1,
                call_id="preexisting",
                provider_call_id="prov-existing",
                started_at=datetime(2024, 6, 1, 8, 0, tzinfo=timezone.utc),
            )
        )

    result = service.run()
    assert len(result.scheduled) == 0
    assert result.capacity_exhausted is True or result.available_capacity == 0