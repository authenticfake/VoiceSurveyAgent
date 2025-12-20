from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any

import pytest

from app.calls.scheduler import (
    CAMPAIGN_STATUS_RUNNING,
    CONTACT_STATE_IN_PROGRESS,
    CONTACT_STATE_NOT_REACHED,
    CONTACT_STATE_PENDING,
    CallScheduler,
    CallSchedulerConfig,
)


# -----------------------------
# In-memory fakes (repositories + provider)
# -----------------------------
@dataclass
class Campaign:
    id: str
    status: str = CAMPAIGN_STATUS_RUNNING
    max_attempts: int = 3
    allowed_call_start_local: time = time(0, 0)
    allowed_call_end_local: time = time(23, 59)
    timezone: Any | None = timezone.utc


@dataclass
class Contact:
    id: str
    campaign_id: str
    phone_number: str
    state: str = CONTACT_STATE_PENDING
    attempts_count: int = 0
    do_not_call: bool = False


@dataclass
class CallAttempt:
    id: str
    contact_id: str
    campaign_id: str
    attempt_number: int
    provider_call_id: str | None = None


class InMemoryCampaignRepo:
    def __init__(self, campaigns: list[Campaign]) -> None:
        self._campaigns = campaigns

    def list_running(self) -> list[Campaign]:
        # Scheduler will still check status == RUNNING, but keep this simple.
        return list(self._campaigns)


class InMemoryContactRepo:
    def __init__(self, contacts: list[Contact]) -> None:
        self._by_id = {c.id: c for c in contacts}
        self._contacts = contacts
        self.update_calls: list[dict[str, Any]] = []
        self.revert_calls: list[dict[str, Any]] = []

    def list_by_campaign(self, campaign_id: str) -> list[Contact]:
        return [c for c in self._contacts if c.campaign_id == campaign_id]

    def update_after_scheduled(
        self,
        *,
        contact_id: str,
        new_state: str,
        new_attempts_count: int,
        last_attempt_at: datetime,
    ) -> None:
        c = self._by_id[contact_id]
        c.state = new_state
        c.attempts_count = new_attempts_count
        self.update_calls.append(
            {
                "contact_id": contact_id,
                "new_state": new_state,
                "new_attempts_count": new_attempts_count,
                "last_attempt_at": last_attempt_at,
            }
        )

    def revert_after_failure(
        self,
        *,
        contact_id: str,
        previous_state: str,
        previous_attempts_count: int,
    ) -> None:
        c = self._by_id[contact_id]
        c.state = previous_state
        c.attempts_count = previous_attempts_count
        self.revert_calls.append(
            {
                "contact_id": contact_id,
                "previous_state": previous_state,
                "previous_attempts_count": previous_attempts_count,
            }
        )


class InMemoryAttemptRepo:
    def __init__(self) -> None:
        self._seq = 0
        self.attempts: list[CallAttempt] = []
        self.create_calls: list[dict[str, Any]] = []
        self.set_provider_calls: list[dict[str, Any]] = []

    def create(
        self,
        *,
        contact_id: str,
        campaign_id: str,
        attempt_number: int,
        created_at: datetime,
    ) -> CallAttempt:
        self._seq += 1
        attempt = CallAttempt(
            id=f"att-{self._seq}",
            contact_id=contact_id,
            campaign_id=campaign_id,
            attempt_number=attempt_number,
            provider_call_id=None,
        )
        self.attempts.append(attempt)
        self.create_calls.append(
            {
                "attempt_id": attempt.id,
                "contact_id": contact_id,
                "campaign_id": campaign_id,
                "attempt_number": attempt_number,
                "created_at": created_at,
            }
        )
        return attempt

    def set_provider_call_id(self, *, attempt_id: str, provider_call_id: str) -> None:
        for a in self.attempts:
            if a.id == attempt_id:
                a.provider_call_id = provider_call_id
                break
        self.set_provider_calls.append(
            {"attempt_id": attempt_id, "provider_call_id": provider_call_id}
        )


class FakeTelephonyProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.should_fail = False

    def initiate_call(
        self,
        *,
        to_number: str,
        from_number: str,
        callback_url: str,
        metadata: dict[str, str],
    ) -> str:
        if self.should_fail:
            raise RuntimeError("provider error")
        self.calls.append(
            {
                "to_number": to_number,
                "from_number": from_number,
                "callback_url": callback_url,
                "metadata": metadata,
            }
        )
        return f"prov-{len(self.calls)}"


# -----------------------------
# Tests (pure logic)
# -----------------------------
def test_selects_pending_and_not_reached_only() -> None:
    now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    campaign = Campaign(id="c1", max_attempts=3)

    contacts = [
        Contact(id="p1", campaign_id="c1", phone_number="+1", state=CONTACT_STATE_PENDING),
        Contact(id="nr1", campaign_id="c1", phone_number="+2", state=CONTACT_STATE_NOT_REACHED, attempts_count=1),
        Contact(id="ip1", campaign_id="c1", phone_number="+3", state=CONTACT_STATE_IN_PROGRESS),
    ]

    scheduler = CallScheduler(
        campaigns=InMemoryCampaignRepo([campaign]),
        contacts=InMemoryContactRepo(contacts),
        attempts=InMemoryAttemptRepo(),
        telephony_provider=FakeTelephonyProvider(),
        config=CallSchedulerConfig(max_concurrent_calls=10, batch_size=10),
        from_number="+999",
        callback_url="http://cb",
    )

    initiated = scheduler.run_once(now=now)

    assert initiated == 2


def test_excludes_max_attempts_reached() -> None:
    now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    campaign = Campaign(id="c1", max_attempts=3)

    contacts = [
        Contact(id="ok", campaign_id="c1", phone_number="+1", state=CONTACT_STATE_NOT_REACHED, attempts_count=2),
        Contact(id="max", campaign_id="c1", phone_number="+2", state=CONTACT_STATE_NOT_REACHED, attempts_count=3),
    ]

    scheduler = CallScheduler(
        campaigns=InMemoryCampaignRepo([campaign]),
        contacts=InMemoryContactRepo(contacts),
        attempts=InMemoryAttemptRepo(),
        telephony_provider=FakeTelephonyProvider(),
        config=CallSchedulerConfig(max_concurrent_calls=10, batch_size=10),
        from_number="+999",
        callback_url="http://cb",
    )

    initiated = scheduler.run_once(now=now)

    assert initiated == 1


def test_respects_call_window() -> None:
    campaign = Campaign(
        id="c1",
        max_attempts=3,
        allowed_call_start_local=time(9, 0),
        allowed_call_end_local=time(10, 0),
        timezone=timezone.utc,
    )
    contacts = [Contact(id="p1", campaign_id="c1", phone_number="+1", state=CONTACT_STATE_PENDING)]

    scheduler = CallScheduler(
        campaigns=InMemoryCampaignRepo([campaign]),
        contacts=InMemoryContactRepo(contacts),
        attempts=InMemoryAttemptRepo(),
        telephony_provider=FakeTelephonyProvider(),
        config=CallSchedulerConfig(max_concurrent_calls=10, batch_size=10),
        from_number="+999",
        callback_url="http://cb",
    )

    initiated_outside = scheduler.run_once(now=datetime(2025, 1, 1, 8, 59, tzinfo=timezone.utc))
    initiated_inside = scheduler.run_once(now=datetime(2025, 1, 1, 9, 30, tzinfo=timezone.utc))

    assert initiated_outside == 0
    assert initiated_inside == 1


def test_creates_attempt_before_initiating_call_order() -> None:
    now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    campaign = Campaign(id="c1", max_attempts=3)
    contacts = [Contact(id="p1", campaign_id="c1", phone_number="+1", state=CONTACT_STATE_PENDING)]

    attempts = InMemoryAttemptRepo()
    provider = FakeTelephonyProvider()

    scheduler = CallScheduler(
        campaigns=InMemoryCampaignRepo([campaign]),
        contacts=InMemoryContactRepo(contacts),
        attempts=attempts,
        telephony_provider=provider,
        config=CallSchedulerConfig(max_concurrent_calls=10, batch_size=10),
        from_number="+999",
        callback_url="http://cb",
    )

    initiated = scheduler.run_once(now=now)

    assert initiated == 1
    assert len(attempts.create_calls) == 1
    assert len(provider.calls) == 1

    created_attempt_id = attempts.create_calls[0]["attempt_id"]
    metadata_attempt_id = provider.calls[0]["metadata"]["attempt_id"]
    assert metadata_attempt_id == created_attempt_id


def test_provider_failure_reverts_contact_state_and_attempts() -> None:
    now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    campaign = Campaign(id="c1", max_attempts=3)
    contact = Contact(id="p1", campaign_id="c1", phone_number="+1", state=CONTACT_STATE_PENDING, attempts_count=0)

    contacts_repo = InMemoryContactRepo([contact])
    attempts_repo = InMemoryAttemptRepo()
    provider = FakeTelephonyProvider()
    provider.should_fail = True

    scheduler = CallScheduler(
        campaigns=InMemoryCampaignRepo([campaign]),
        contacts=contacts_repo,
        attempts=attempts_repo,
        telephony_provider=provider,
        config=CallSchedulerConfig(max_concurrent_calls=10, batch_size=10),
        from_number="+999",
        callback_url="http://cb",
    )

    initiated = scheduler.run_once(now=now)

    assert initiated == 0
    assert contact.state == CONTACT_STATE_PENDING
    assert contact.attempts_count == 0
    assert len(contacts_repo.revert_calls) == 1


def test_respects_max_concurrent_calls_limit() -> None:
    now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    campaign = Campaign(id="c1", max_attempts=3)
    contacts = [
        Contact(id="p1", campaign_id="c1", phone_number="+1"),
        Contact(id="p2", campaign_id="c1", phone_number="+2"),
        Contact(id="p3", campaign_id="c1", phone_number="+3"),
    ]

    scheduler = CallScheduler(
        campaigns=InMemoryCampaignRepo([campaign]),
        contacts=InMemoryContactRepo(contacts),
        attempts=InMemoryAttemptRepo(),
        telephony_provider=FakeTelephonyProvider(),
        config=CallSchedulerConfig(max_concurrent_calls=2, batch_size=10),
        from_number="+999",
        callback_url="http://cb",
    )

    initiated = scheduler.run_once(now=now)

    assert initiated == 2
