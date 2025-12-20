from datetime import datetime
from uuid import uuid4

from app.telephony.interface import WebhookEvent, WebhookEventType, CallStatus
from app.telephony.webhooks.handler import WebhookHandler


# -------------------------
# Fakes (in-memory)
# -------------------------

class FakeAttempt:
    def __init__(self, call_id, campaign_id, contact_id):
        self.call_id = call_id
        self.campaign_id = campaign_id
        self.contact_id = contact_id
        self.provider_call_id = None
        self.provider_raw_status = None
        self.answered_at = None
        self.ended_at = None
        self.outcome = None
        self.meta = {}


class FakeContact:
    def __init__(self, contact_id):
        self.id = contact_id
        self.state = "pending"
        self.last_outcome = None


class FakeAttemptRepo:
    def __init__(self, attempt):
        self._attempt = attempt

    def get_by_call_id(self, call_id):
        return self._attempt if call_id == self._attempt.call_id else None

    def save(self, attempt):
        self._attempt = attempt


class FakeContactRepo:
    def __init__(self, contact):
        self._contact = contact

    def get_by_id(self, contact_id):
        return self._contact if contact_id == self._contact.id else None

    def save(self, contact):
        self._contact = contact


class FakeDialogueStarter:
    def __init__(self):
        self.called = False
        self.args = None

    def start_dialogue(self, call_id, campaign_id, contact_id):
        self.called = True
        self.args = (call_id, campaign_id, contact_id)


# -------------------------
# Tests
# -------------------------

def test_answered_triggers_dialogue_start_sync():
    call_id = "call-1"
    campaign_id = uuid4()
    contact_id = uuid4()

    attempt = FakeAttempt(call_id, campaign_id, contact_id)
    contact = FakeContact(contact_id)

    starter = FakeDialogueStarter()
    handler = WebhookHandler(
        attempts=FakeAttemptRepo(attempt),
        contacts=FakeContactRepo(contact),
        dialogue_starter=starter,
    )

    event = WebhookEvent(
        event_type=WebhookEventType.CALL_ANSWERED,
        provider="twilio",
        provider_call_id="prov-1",
        call_id=call_id,
        campaign_id=campaign_id,
        contact_id=contact_id,
        status=CallStatus.IN_PROGRESS,
        timestamp=datetime.utcnow(),
    )

    result = handler.handle(event)

    assert result is True
    assert starter.called is True


def test_no_answer_updates_attempt_and_contact_sync():
    call_id = "call-2"
    campaign_id = uuid4()
    contact_id = uuid4()

    attempt = FakeAttempt(call_id, campaign_id, contact_id)
    contact = FakeContact(contact_id)

    handler = WebhookHandler(
        attempts=FakeAttemptRepo(attempt),
        contacts=FakeContactRepo(contact),
    )

    event = WebhookEvent(
        event_type=WebhookEventType.CALL_NO_ANSWER,
        provider="twilio",
        provider_call_id="prov-2",
        call_id=call_id,
        campaign_id=campaign_id,
        contact_id=contact_id,
        status=CallStatus.NO_ANSWER,
        timestamp=datetime.utcnow(),
    )

    result = handler.handle(event)

    assert result is True
    assert attempt.outcome == "no_answer"
    assert contact.state == "not_reached"
    assert contact.last_outcome == "no_answer"


def test_duplicate_event_is_ignored_sync():
    call_id = "call-3"
    campaign_id = uuid4()
    contact_id = uuid4()

    attempt = FakeAttempt(call_id, campaign_id, contact_id)
    contact = FakeContact(contact_id)

    handler = WebhookHandler(
        attempts=FakeAttemptRepo(attempt),
        contacts=FakeContactRepo(contact),
    )

    event = WebhookEvent(
        event_type=WebhookEventType.CALL_COMPLETED,
        provider="twilio",
        provider_call_id="prov-3",
        call_id=call_id,
        campaign_id=campaign_id,
        contact_id=contact_id,
        status=CallStatus.COMPLETED,
        timestamp=datetime.utcnow(),
    )

    assert handler.handle(event) is True
    assert handler.handle(event) is False  # idempotent
