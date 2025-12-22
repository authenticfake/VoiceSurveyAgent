"""
Unit tests for REQ-008 CallScheduler (SYNC, in-memory).

Acceptance criteria covered:
1) Scheduler config default interval is 60s
2) Eligible contacts: state pending/not_reached
3) attempts_count < campaign.max_attempts
4) now is within allowed_call_start_local/end_local
5) CallAttempt is created BEFORE provider initiation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any
from uuid import UUID, uuid4

from app.calls.scheduler import CallScheduler, CallSchedulerConfig


@dataclass
class FakeCampaign:
    id: UUID
    status: str
    max_attempts: int
    allowed_call_start_local: time | None
    allowed_call_end_local: time | None
    language: str = "it"


@dataclass
class FakeContact:
    id: UUID
    campaign_id: UUID
    state: str
    attempts_count: int
    do_not_call: bool
    phone_number: str
    preferred_language: str | None = None


class InMemoryAttemptRepo:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []
        self.created: list[dict[str, Any]] = []

    def create(self, contact_id: UUID, campaign_id: UUID, attempt_number: int, call_id: str) -> object:
        self.events.append(("attempt_created", call_id))
        self.created.append(
            {
                "contact_id": contact_id,
                "campaign_id": campaign_id,
                "attempt_number": attempt_number,
                "call_id": call_id,
            }
        )
        return self.created[-1]


class FakeProvider:
    def __init__(self, events: list[tuple[str, str]]) -> None:
        self._events = events

    def initiate_call(self, to_number: str, from_number: str, callback_url: str, metadata: dict[str, str]) -> str:
        self._events.append(("provider_called", metadata["call_id"]))
        return "provider-call-id-1"


def test_config_default_interval_is_60_seconds() -> None:
    cfg = CallSchedulerConfig()
    assert cfg.interval_seconds == 60


def test_run_once_sync_filters_and_orders_side_effects() -> None:
    now = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    campaign_id = uuid4()
    campaigns = [
        FakeCampaign(
            id=campaign_id,
            status="running",
            max_attempts=3,
            allowed_call_start_local=time(9, 0),
            allowed_call_end_local=time(20, 0),
            language="it",
        )
    ]

    eligible = FakeContact(
        id=uuid4(),
        campaign_id=campaign_id,
        state="pending",
        attempts_count=0,
        do_not_call=False,
        phone_number="+390000000001",
        preferred_language=None,
    )

    ineligible_state = FakeContact(
        id=uuid4(),
        campaign_id=campaign_id,
        state="in_progress",
        attempts_count=0,
        do_not_call=False,
        phone_number="+390000000002",
    )

    ineligible_attempts = FakeContact(
        id=uuid4(),
        campaign_id=campaign_id,
        state="not_reached",
        attempts_count=3,  # == max_attempts => excluded
        do_not_call=False,
        phone_number="+390000000003",
    )

    ineligible_dnc = FakeContact(
        id=uuid4(),
        campaign_id=campaign_id,
        state="pending",
        attempts_count=0,
        do_not_call=True,
        phone_number="+390000000004",
    )

    repo = InMemoryAttemptRepo()
    provider = FakeProvider(repo.events)

    initiated = CallScheduler.run_once_sync(
        campaigns=campaigns,
        contacts=[eligible, ineligible_state, ineligible_attempts, ineligible_dnc],
        call_attempt_repo=repo,
        telephony_provider=provider,
        now=now,
        config=CallSchedulerConfig(max_concurrent_calls=10, batch_size=50),
        outbound_number="+390000000000",
        callback_base_url="http://localhost:8000",
    )

    assert initiated == 1
    assert eligible.state == "in_progress"
    assert eligible.attempts_count == 1

    # AC-5: attempt created BEFORE provider is called (same call_id)
    assert len(repo.events) == 2
    assert repo.events[0][0] == "attempt_created"
    assert repo.events[1][0] == "provider_called"
    assert repo.events[0][1] == repo.events[1][1]


def test_run_once_sync_respects_time_window() -> None:
    now = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)

    campaign_id = uuid4()
    campaigns = [
        FakeCampaign(
            id=campaign_id,
            status="running",
            max_attempts=3,
            allowed_call_start_local=time(9, 0),
            allowed_call_end_local=time(20, 0),
        )
    ]

    contact = FakeContact(
        id=uuid4(),
        campaign_id=campaign_id,
        state="pending",
        attempts_count=0,
        do_not_call=False,
        phone_number="+390000000001",
    )

    repo = InMemoryAttemptRepo()
    provider = FakeProvider(repo.events)

    initiated = CallScheduler.run_once_sync(
        campaigns=campaigns,
        contacts=[contact],
        call_attempt_repo=repo,
        telephony_provider=provider,
        now=now,
    )

    assert initiated == 0
    assert repo.events == []

def test_run_once_sync_respects_max_concurrent_calls_limit() -> None:
    now = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    campaign_id = uuid4()
    campaigns = [
        FakeCampaign(
            id=campaign_id,
            status="running",
            max_attempts=5,
            allowed_call_start_local=time(9, 0),
            allowed_call_end_local=time(20, 0),
        )
    ]

    # 10 contatti tutti eligibili
    contacts = [
        FakeContact(
            id=uuid4(),
            campaign_id=campaign_id,
            state="pending",
            attempts_count=0,
            do_not_call=False,
            phone_number=f"+3900000001{i:02d}",
        )
        for i in range(10)
    ]

    repo = InMemoryAttemptRepo()
    provider = FakeProvider(repo.events)

    initiated = CallScheduler.run_once_sync(
        campaigns=campaigns,
        contacts=contacts,
        call_attempt_repo=repo,
        telephony_provider=provider,
        now=now,
        config=CallSchedulerConfig(max_concurrent_calls=3, batch_size=50),
    )

    # Deve limitare a 3 chiamate anche se ce ne sono 10 eligibili
    assert initiated == 3
    assert len(repo.created) == 3
    assert len([e for e in repo.events if e[0] == "provider_called"]) == 3


def test_run_once_sync_respects_max_concurrent_calls_limit() -> None:
    now = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    campaign_id = uuid4()
    campaigns = [
        FakeCampaign(
            id=campaign_id,
            status="running",
            max_attempts=5,
            allowed_call_start_local=time(9, 0),
            allowed_call_end_local=time(20, 0),
        )
    ]

    # 10 contatti tutti eligibili
    contacts = [
        FakeContact(
            id=uuid4(),
            campaign_id=campaign_id,
            state="pending",
            attempts_count=0,
            do_not_call=False,
            phone_number=f"+3900000001{i:02d}",
        )
        for i in range(10)
    ]

    repo = InMemoryAttemptRepo()
    provider = FakeProvider(repo.events)

    initiated = CallScheduler.run_once_sync(
        campaigns=campaigns,
        contacts=contacts,
        call_attempt_repo=repo,
        telephony_provider=provider,
        now=now,
        config=CallSchedulerConfig(max_concurrent_calls=3, batch_size=50),
    )

    # Deve limitare a 3 chiamate anche se ce ne sono 10 eligibili
    assert initiated == 3
    assert len(repo.created) == 3
    assert len([e for e in repo.events if e[0] == "provider_called"]) == 3


def test_run_once_sync_ignores_non_running_campaigns() -> None:
    now = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    campaign_id = uuid4()
    campaigns = [
        FakeCampaign(
            id=campaign_id,
            status="paused",  # non running => ignorata
            max_attempts=3,
            allowed_call_start_local=time(9, 0),
            allowed_call_end_local=time(20, 0),
        )
    ]

    contact = FakeContact(
        id=uuid4(),
        campaign_id=campaign_id,
        state="pending",
        attempts_count=0,
        do_not_call=False,
        phone_number="+390000000001",
    )

    repo = InMemoryAttemptRepo()
    provider = FakeProvider(repo.events)

    initiated = CallScheduler.run_once_sync(
        campaigns=campaigns,
        contacts=[contact],
        call_attempt_repo=repo,
        telephony_provider=provider,
        now=now,
    )

    assert initiated == 0
    assert repo.events == []
    assert repo.created == []


