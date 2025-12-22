"""REQ-014 - Survey response persistence (sync-only logic tests).

Constraints satisfied:
- sync-only tests (no pytest-asyncio)
- no DB / no SQLAlchemy session usage
- in-memory repositories
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict
from uuid import UUID, uuid4

import pytest

from app.dialogue.models import CallContext, CapturedAnswer, DialogueSession
from app.dialogue.persistence import (
    NotFoundError,
    SurveyPersistenceService,
    TransactionError,
)


@dataclass
class Contact:
    id: UUID
    campaign_id: UUID
    phone_number: str
    state: str
    last_outcome: str | None = None


@dataclass
class CallAttempt:
    id: UUID
    contact_id: UUID
    campaign_id: UUID
    attempt_number: int
    call_id: str
    outcome: str | None = None
    ended_at: datetime | None = None


@dataclass
class SurveyResponse:
    id: UUID
    contact_id: UUID
    campaign_id: UUID
    call_attempt_id: UUID
    q1_answer: str
    q2_answer: str
    q3_answer: str
    q1_confidence: float | None = None
    q2_confidence: float | None = None
    q3_confidence: float | None = None
    completed_at: datetime | None = None


@dataclass
class InMemoryStore:
    contacts: Dict[UUID, Contact]
    attempts: Dict[UUID, CallAttempt]
    responses: Dict[tuple[UUID, UUID], SurveyResponse]

    def snapshot(self) -> "InMemoryStore":
        return copy.deepcopy(self)

    def restore(self, snap: "InMemoryStore") -> None:
        self.contacts = snap.contacts
        self.attempts = snap.attempts
        self.responses = snap.responses


class FakeSession:
    """A minimal sync 'session' with a transaction-like context manager."""

    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    @contextmanager
    def begin(self):
        snap = self.store.snapshot()
        try:
            yield self
        except Exception:
            self.store.restore(snap)
            raise


class InMemorySurveyResponseRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def get_by_contact_and_campaign(
        self, session: FakeSession, contact_id: UUID, campaign_id: UUID
    ) -> SurveyResponse | None:
        return self.store.responses.get((contact_id, campaign_id))

    def create_survey_response(
        self,
        session: FakeSession,
        contact_id: UUID,
        campaign_id: UUID,
        call_attempt_id: UUID,
        answers: list[CapturedAnswer],
    ) -> SurveyResponse:
        if len(answers) != 3:
            raise ValueError(f"Expected 3 answers, got {len(answers)}")

        sorted_answers = sorted(answers, key=lambda a: a.question_index)

        sr = SurveyResponse(
            id=uuid4(),
            contact_id=contact_id,
            campaign_id=campaign_id,
            call_attempt_id=call_attempt_id,
            q1_answer=sorted_answers[0].answer_text,
            q2_answer=sorted_answers[1].answer_text,
            q3_answer=sorted_answers[2].answer_text,
            q1_confidence=sorted_answers[0].confidence,
            q2_confidence=sorted_answers[1].confidence,
            q3_confidence=sorted_answers[2].confidence,
            completed_at=datetime.now(timezone.utc),
        )
        self.store.responses[(contact_id, campaign_id)] = sr
        return sr


class InMemoryContactRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def get_by_id(self, session: FakeSession, contact_id: UUID) -> Contact | None:
        return self.store.contacts.get(contact_id)

    def update_state(
        self,
        session: FakeSession,
        contact_id: UUID,
        state: object,
        outcome: object | None = None,
    ) -> None:
        c = self.store.contacts.get(contact_id)
        if c is None:
            raise NotFoundError(f"Contact not found: {contact_id}")
        c.state = getattr(state, "value", state)
        if outcome is not None:
            c.last_outcome = getattr(outcome, "value", outcome)


class InMemoryCallAttemptRepo:
    def __init__(self, store: InMemoryStore, *, fail_update: bool = False) -> None:
        self.store = store
        self.fail_update = fail_update

    def get_by_id(self, session: FakeSession, call_attempt_id: UUID) -> CallAttempt | None:
        return self.store.attempts.get(call_attempt_id)

    def update_outcome(
        self,
        session: FakeSession,
        call_attempt_id: UUID,
        outcome: str,
        ended_at: datetime,
    ) -> None:
        if self.fail_update:
            raise RuntimeError("boom")
        a = self.store.attempts.get(call_attempt_id)
        if a is None:
            raise NotFoundError(f"CallAttempt not found: {call_attempt_id}")
        a.outcome = outcome
        a.ended_at = ended_at


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore(contacts={}, attempts={}, responses={})


@pytest.fixture
def session(store: InMemoryStore) -> FakeSession:
    return FakeSession(store)


def _make_completed_dialogue_session(
    *, contact_id: UUID, campaign_id: UUID, attempt_id: UUID
) -> DialogueSession:
    return DialogueSession(
        call_context=CallContext(
            call_id="call-123",
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_attempt_id=attempt_id,
            language="it",
        ),
        answers=[
            CapturedAnswer(0, "Q1", "A1", 0.9),
            CapturedAnswer(1, "Q2", "A2", 0.8),
            CapturedAnswer(2, "Q3", "A3", 0.7),
        ],
    )


def test_persist_completed_creates_response_and_updates_contact_and_attempt(
    store: InMemoryStore, session: FakeSession
) -> None:
    contact_id = uuid4()
    campaign_id = uuid4()
    attempt_id = uuid4()

    store.contacts[contact_id] = Contact(
        id=contact_id,
        campaign_id=campaign_id,
        phone_number="+390000000000",
        state="in_progress",
        last_outcome=None,
    )
    store.attempts[attempt_id] = CallAttempt(
        id=attempt_id,
        contact_id=contact_id,
        campaign_id=campaign_id,
        attempt_number=1,
        call_id="call-123",
        outcome=None,
        ended_at=None,
    )

    ds = _make_completed_dialogue_session(
        contact_id=contact_id, campaign_id=campaign_id, attempt_id=attempt_id
    )

    svc = SurveyPersistenceService(
        survey_response_repo=InMemorySurveyResponseRepo(store),
        contact_repo=InMemoryContactRepo(store),
        call_attempt_repo=InMemoryCallAttemptRepo(store),
    )

    result = svc.persist_completed_survey_sync(session, ds)

    assert result.success is True
    assert result.survey_response_id is not None
    assert result.contact_id == contact_id
    assert result.call_attempt_id == attempt_id
    assert result.completed_at is not None

    sr = store.responses[(contact_id, campaign_id)]
    assert sr.call_attempt_id == attempt_id
    assert [sr.q1_answer, sr.q2_answer, sr.q3_answer] == ["A1", "A2", "A3"]
    assert sr.completed_at is not None

    assert store.contacts[contact_id].state == "completed"
    assert store.contacts[contact_id].last_outcome == "completed"

    assert store.attempts[attempt_id].outcome == "completed"
    assert store.attempts[attempt_id].ended_at is not None


def test_persist_completed_requires_exactly_three_answers(
    store: InMemoryStore, session: FakeSession
) -> None:
    contact_id = uuid4()
    campaign_id = uuid4()
    attempt_id = uuid4()

    store.contacts[contact_id] = Contact(
        id=contact_id,
        campaign_id=campaign_id,
        phone_number="+390000000000",
        state="in_progress",
        last_outcome=None,
    )
    store.attempts[attempt_id] = CallAttempt(
        id=attempt_id,
        contact_id=contact_id,
        campaign_id=campaign_id,
        attempt_number=1,
        call_id="call-123",
        outcome=None,
        ended_at=None,
    )

    ds = DialogueSession(
        call_context=CallContext(
            call_id="call-123",
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_attempt_id=attempt_id,
        ),
        answers=[CapturedAnswer(0, "Q1", "A1", 0.9)],
    )

    svc = SurveyPersistenceService(
        survey_response_repo=InMemorySurveyResponseRepo(store),
        contact_repo=InMemoryContactRepo(store),
        call_attempt_repo=InMemoryCallAttemptRepo(store),
    )

    res = svc.persist_completed_survey_sync(session, ds)
    assert res.success is False
    assert "expected 3 answers" in (res.error_message or "").lower()
    assert store.responses == {}


def test_persist_completed_is_idempotent_if_response_exists(
    store: InMemoryStore, session: FakeSession
) -> None:
    contact_id = uuid4()
    campaign_id = uuid4()
    attempt_id = uuid4()

    store.contacts[contact_id] = Contact(
        id=contact_id,
        campaign_id=campaign_id,
        phone_number="+390000000000",
        state="in_progress",
        last_outcome=None,
    )
    store.attempts[attempt_id] = CallAttempt(
        id=attempt_id,
        contact_id=contact_id,
        campaign_id=campaign_id,
        attempt_number=1,
        call_id="call-123",
        outcome=None,
        ended_at=None,
    )

    existing = SurveyResponse(
        id=uuid4(),
        contact_id=contact_id,
        campaign_id=campaign_id,
        call_attempt_id=attempt_id,
        q1_answer="old1",
        q2_answer="old2",
        q3_answer="old3",
        q1_confidence=0.1,
        q2_confidence=0.2,
        q3_confidence=0.3,
        completed_at=datetime.now(timezone.utc),
    )
    store.responses[(contact_id, campaign_id)] = existing

    ds = _make_completed_dialogue_session(
        contact_id=contact_id, campaign_id=campaign_id, attempt_id=attempt_id
    )

    svc = SurveyPersistenceService(
        survey_response_repo=InMemorySurveyResponseRepo(store),
        contact_repo=InMemoryContactRepo(store),
        call_attempt_repo=InMemoryCallAttemptRepo(store),
    )

    res = svc.persist_completed_survey_sync(session, ds)
    assert res.success is True
    assert res.survey_response_id == existing.id
    assert store.responses[(contact_id, campaign_id)].q1_answer == "old1"


def test_persist_completed_raises_not_found_if_contact_missing(
    store: InMemoryStore, session: FakeSession
) -> None:
    contact_id = uuid4()
    campaign_id = uuid4()
    attempt_id = uuid4()

    store.attempts[attempt_id] = CallAttempt(
        id=attempt_id,
        contact_id=contact_id,
        campaign_id=campaign_id,
        attempt_number=1,
        call_id="call-123",
        outcome=None,
        ended_at=None,
    )

    ds = _make_completed_dialogue_session(
        contact_id=contact_id, campaign_id=campaign_id, attempt_id=attempt_id
    )

    svc = SurveyPersistenceService(
        survey_response_repo=InMemorySurveyResponseRepo(store),
        contact_repo=InMemoryContactRepo(store),
        call_attempt_repo=InMemoryCallAttemptRepo(store),
    )

    with pytest.raises(NotFoundError):
        svc.persist_completed_survey_sync(session, ds)
    assert store.responses == {}


def test_persist_completed_atomicity_no_partial_updates_on_repo_failure(
    store: InMemoryStore, session: FakeSession
) -> None:
    contact_id = uuid4()
    campaign_id = uuid4()
    attempt_id = uuid4()

    store.contacts[contact_id] = Contact(
        id=contact_id,
        campaign_id=campaign_id,
        phone_number="+390000000000",
        state="in_progress",
        last_outcome=None,
    )
    store.attempts[attempt_id] = CallAttempt(
        id=attempt_id,
        contact_id=contact_id,
        campaign_id=campaign_id,
        attempt_number=1,
        call_id="call-123",
        outcome=None,
        ended_at=None,
    )

    ds = _make_completed_dialogue_session(
        contact_id=contact_id, campaign_id=campaign_id, attempt_id=attempt_id
    )

    failing_attempt_repo = InMemoryCallAttemptRepo(store, fail_update=True)
    svc = SurveyPersistenceService(
        survey_response_repo=InMemorySurveyResponseRepo(store),
        contact_repo=InMemoryContactRepo(store),
        call_attempt_repo=failing_attempt_repo,
    )

    with pytest.raises(TransactionError):
        svc.persist_completed_survey_sync(session, ds)

    assert store.responses == {}
    assert store.contacts[contact_id].state == "in_progress"
    assert store.contacts[contact_id].last_outcome is None
    assert store.attempts[attempt_id].outcome is None
    assert store.attempts[attempt_id].ended_at is None


def test_persist_refused_updates_contact_and_attempt_and_timestamp(
    store: InMemoryStore, session: FakeSession
) -> None:
    contact_id = uuid4()
    campaign_id = uuid4()
    attempt_id = uuid4()

    store.contacts[contact_id] = Contact(
        id=contact_id,
        campaign_id=campaign_id,
        phone_number="+390000000000",
        state="in_progress",
        last_outcome=None,
    )
    store.attempts[attempt_id] = CallAttempt(
        id=attempt_id,
        contact_id=contact_id,
        campaign_id=campaign_id,
        attempt_number=1,
        call_id="call-123",
        outcome=None,
        ended_at=None,
    )

    ds = DialogueSession(
        call_context=CallContext(
            call_id="call-123",
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_attempt_id=attempt_id,
        )
    )

    svc = SurveyPersistenceService(
        survey_response_repo=InMemorySurveyResponseRepo(store),
        contact_repo=InMemoryContactRepo(store),
        call_attempt_repo=InMemoryCallAttemptRepo(store),
    )

    res = svc.persist_refused_survey_sync(session, ds)
    assert res.success is True
    assert res.completed_at is not None
    assert store.contacts[contact_id].state == "refused"
    assert store.contacts[contact_id].last_outcome == "refused"
    assert store.attempts[attempt_id].outcome == "refused"
    assert store.attempts[attempt_id].ended_at is not None
