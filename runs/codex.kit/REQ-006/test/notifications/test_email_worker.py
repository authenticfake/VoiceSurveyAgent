from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.events.bus.models import SurveyAnswerModel, SurveyEventMessage, SurveyEventType
from app.infra.db.base import Base
from app.infra.db.models import (
    Campaign,
    CampaignLanguage,
    CampaignStatus,
    Contact,
    ContactLanguage,
    ContactState,
    EmailNotification,
    EmailNotificationStatus,
    EmailTemplate,
    EmailTemplateType,
    Event,
)
from app.infra.messaging.sqs import QueueConsumer, QueueMessage
from app.notifications.email.models import EmailSendRequest, EmailSendResult
from app.notifications.email.provider import EmailProvider
from app.notifications.email.rendering import TemplateRenderer
from app.notifications.email.service import EmailNotificationProcessor
from app.notifications.email.worker import SurveyEmailWorker


class FakeEmailProvider(EmailProvider):
    def __init__(self):
        self.sent_requests: List[EmailSendRequest] = []

    def send_email(self, request: EmailSendRequest) -> EmailSendResult:
        self.sent_requests.append(request)
        return EmailSendResult(message_id=f"msg-{len(self.sent_requests)}", provider="fake")


class FakeQueueConsumer(QueueConsumer):
    def __init__(self, message_body: str):
        self._message_body = message_body
        self.deleted = False

    def receive_messages(self) -> List[QueueMessage]:
        if self._message_body is None:
            return []
        body = self._message_body
        self._message_body = None
        return [
            QueueMessage(
                message_id="1",
                receipt_handle="r1",
                body=body,
                attributes={},
            )
        ]

    def delete_message(self, receipt_handle: str) -> None:
        self.deleted = True


def _build_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_reference_data(session: Session):
    template = EmailTemplate(
        id=uuid4(),
        name="Completed EN",
        type=EmailTemplateType.COMPLETED,
        locale="en",
        subject="Thank you",
        body_html="<p>Hi {{ contact.email }}</p>",
        body_text="Hi {{ contact.email }}",
    )
    campaign = Campaign(
        id=uuid4(),
        name="Q1 Survey",
        description=None,
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
        allowed_call_start_local=datetime.now().time(),
        allowed_call_end_local=datetime.now().time(),
        email_completed_template_id=template.id,
    )
    contact = Contact(
        id=uuid4(),
        campaign=campaign,
        phone_number="+15555550123",
        email="respondent@example.com",
        preferred_language=ContactLanguage.EN,
        state=ContactState.COMPLETED,
        has_prior_consent=True,
        do_not_call=False,
    )
    event = Event(
        id=uuid4(),
        campaign=campaign,
        contact=contact,
        event_type="survey.completed",
        payload={},
    )
    session.add_all([template, campaign, contact, event])
    session.commit()
    return campaign, contact, event


def test_processor_sends_email_and_is_idempotent():
    session_factory = _build_session_factory()
    renderer = TemplateRenderer()
    provider = FakeEmailProvider()
    processor = EmailNotificationProcessor(session_factory, provider, renderer)

    with session_factory() as session:
        campaign, contact, event = _seed_reference_data(session)

    message = SurveyEventMessage(
        event_id=event.id,
        event_type=SurveyEventType.COMPLETED,
        campaign_id=campaign.id,
        contact_id=contact.id,
        call_attempt_id=uuid4(),
        call_id="call-1",
        timestamp=datetime.now(timezone.utc),
        attempts_count=1,
        answers=[SurveyAnswerModel(question_number=1, answer_text="Great", confidence=0.9)],
        outcome="completed",
        email=contact.email,
        locale="en",
    )

    result = processor.process(message)
    assert result.status == "sent"
    assert provider.sent_requests[0].to == "respondent@example.com"

    # Second processing should be skipped due to idempotency
    second = processor.process(message)
    assert second.status == "skipped"

    with session_factory() as session:
        notification = session.scalar(select(EmailNotification))
        assert notification.status == EmailNotificationStatus.SENT
        assert notification.provider_message_id is not None


def test_worker_consumes_queue_and_deletes_message():
    session_factory = _build_session_factory()
    renderer = TemplateRenderer()
    provider = FakeEmailProvider()
    processor = EmailNotificationProcessor(session_factory, provider, renderer)

    with session_factory() as session:
        campaign, contact, event = _seed_reference_data(session)

    message = SurveyEventMessage(
        event_id=event.id,
        event_type=SurveyEventType.COMPLETED,
        campaign_id=campaign.id,
        contact_id=contact.id,
        call_attempt_id=uuid4(),
        call_id="call-1",
        timestamp=datetime.now(timezone.utc),
        attempts_count=1,
        answers=[],
        outcome="completed",
        email=contact.email,
        locale="en",
    )
    consumer = FakeQueueConsumer(json.dumps(message.model_dump()))
    worker = SurveyEmailWorker(queue_consumer=consumer, processor=processor, idle_sleep_seconds=0)

    processed = worker.run_once()
    assert processed == 1
    assert consumer.deleted is True
    assert provider.sent_requests, "Email should be sent"