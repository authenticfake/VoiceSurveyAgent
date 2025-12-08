from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.calling.dialogue.enums import ConsentDecision, TelephonyEventName
from app.calling.dialogue.models import DialoguePayload, SurveyAnswerPayload, TelephonyEventPayload
from app.calling.dialogue.processor import TelephonyEventProcessor
from app.events.bus.publisher import DbSurveyEventPublisher
from app.infra.db.models import (
    Base,
    CallAttempt,
    CallOutcome,
    Campaign,
    CampaignLanguage,
    CampaignStatus,
    Contact,
    ContactLanguage,
    ContactState,
    Event,
    EventType,
    SurveyResponse,
)


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    return SessionLocal()


def seed_entities(session: Session) -> tuple[Campaign, Contact, CallAttempt]:
    campaign = Campaign(
        id=uuid4(),
        name="Test Campaign",
        status=CampaignStatus.RUNNING,
        language=CampaignLanguage.EN,
        intro_script="Intro",
        question_1_text="Q1",
        question_1_type="free_text",
        question_2_text="Q2",
        question_2_type="free_text",
        question_3_text="Q3",
        question_3_type="free_text",
        max_attempts=3,
        retry_interval_minutes=10,
        allowed_call_start_local=time(9, 0),
        allowed_call_end_local=time(18, 0),
    )
    contact = Contact(
        id=uuid4(),
        campaign_id=campaign.id,
        phone_number="+1555000001",
        preferred_language=ContactLanguage.EN,
        has_prior_consent=False,
        do_not_call=False,
        state=ContactState.IN_PROGRESS,
        attempts_count=1,
    )
    call_attempt = CallAttempt(
        id=uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        attempt_number=1,
        call_id="call-123",
        provider_call_id="prov-123",
        started_at=datetime.now(timezone.utc),
    )
    session.add_all([campaign, contact, call_attempt])
    session.commit()
    return campaign, contact, call_attempt


def build_processor(session: Session) -> TelephonyEventProcessor:
    publisher = DbSurveyEventPublisher(session)
    return TelephonyEventProcessor(session=session, event_publisher=publisher)


def test_completed_consent_creates_survey_response(session: Session) -> None:
    _, contact, attempt = seed_entities(session)
    processor = build_processor(session)

    payload = TelephonyEventPayload(
        event=TelephonyEventName.CALL_COMPLETED,
        campaign_id=attempt.campaign_id,
        contact_id=contact.id,
        call_id=attempt.call_id,
        provider_call_id=attempt.provider_call_id,
        occurred_at=datetime.now(timezone.utc),
        dialogue=DialoguePayload(
            consent_status=ConsentDecision.ACCEPTED,
            consent_timestamp=datetime.now(timezone.utc),
            answers=[
                SurveyAnswerPayload(question_number=1, answer_text="Ans1", confidence=0.9),
                SurveyAnswerPayload(question_number=2, answer_text="Ans2", confidence=0.8),
                SurveyAnswerPayload(question_number=3, answer_text="Ans3", confidence=0.7),
            ],
        ),
    )

    processor.process(payload)

    refreshed_contact = session.get(Contact, contact.id)
    assert refreshed_contact.state == ContactState.COMPLETED
    response = session.query(SurveyResponse).filter_by(contact_id=contact.id).one()
    assert response.q1_answer == "Ans1"
    event_entry = session.query(Event).filter_by(event_type=EventType.SURVEY_COMPLETED).one()
    assert event_entry.payload["call_id"] == attempt.call_id


def test_refused_consent_marks_contact_and_publishes_event(session: Session) -> None:
    _, contact, attempt = seed_entities(session)
    processor = build_processor(session)

    payload = TelephonyEventPayload(
        event=TelephonyEventName.CALL_COMPLETED,
        campaign_id=attempt.campaign_id,
        contact_id=contact.id,
        call_id=attempt.call_id,
        provider_call_id=attempt.provider_call_id,
        occurred_at=datetime.now(timezone.utc),
        dialogue=DialoguePayload(
            consent_status=ConsentDecision.REFUSED,
            consent_timestamp=datetime.now(timezone.utc),
            answers=[],
        ),
    )

    processor.process(payload)

    refreshed_attempt = session.get(CallAttempt, attempt.id)
    refreshed_contact = session.get(Contact, contact.id)
    assert refreshed_attempt.outcome == CallOutcome.REFUSED
    assert refreshed_contact.state == ContactState.REFUSED
    event_entry = session.query(Event).filter_by(event_type=EventType.SURVEY_REFUSED).one()
    assert event_entry.payload["call_id"] == attempt.call_id


def test_not_reached_after_max_attempts(session: Session) -> None:
    campaign, contact, attempt = seed_entities(session)
    contact.attempts_count = campaign.max_attempts
    session.commit()
    processor = build_processor(session)

    payload = TelephonyEventPayload(
        event=TelephonyEventName.CALL_NO_ANSWER,
        campaign_id=attempt.campaign_id,
        contact_id=contact.id,
        call_id=attempt.call_id,
        provider_call_id=attempt.provider_call_id,
        occurred_at=datetime.now(timezone.utc),
    )

    processor.process(payload)

    refreshed_contact = session.get(Contact, contact.id)
    assert refreshed_contact.state == ContactState.NOT_REACHED
    event_entry = session.query(Event).filter_by(event_type=EventType.SURVEY_NOT_REACHED).one()
    assert event_entry.payload["call_id"] == attempt.call_id