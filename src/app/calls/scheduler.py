"""app.calls.scheduler

REQ-008: Call scheduler service (CORE)

Design goals (per project constraints):
- PURE + SYNCHRONOUS core (no async, no SQLAlchemy)
- Depends only on small interfaces (Protocols)
- Deterministic + fast unit tests with in-memory repositories
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any, Protocol, Sequence


# -----------------------------
# Domain-ish enums (keep strings to avoid tight coupling)
# -----------------------------
CONTACT_STATE_PENDING = "pending"
CONTACT_STATE_NOT_REACHED = "not_reached"
CONTACT_STATE_IN_PROGRESS = "in_progress"

CAMPAIGN_STATUS_RUNNING = "running"


@dataclass(frozen=True)
class CallSchedulerConfig:
    """Pure configuration for one scheduler tick."""

    # How many calls can be initiated per tick (upper bound).
    max_concurrent_calls: int = 5
    # How many contacts to fetch/process per campaign in one tick.
    batch_size: int = 50


class ClockProtocol(Protocol):
    def now(self) -> datetime: ...


class TelephonyProviderProtocol(Protocol):
    """Sync interface to initiate an outbound call."""

    def initiate_call(
        self,
        *,
        to_number: str,
        from_number: str,
        callback_url: str,
        metadata: dict[str, str],
    ) -> str:
        """Returns provider_call_id."""


class CampaignRecord(Protocol):
    id: Any
    status: str
    max_attempts: int
    allowed_call_start_local: time
    allowed_call_end_local: time
    # Optional; if present it should be a tzinfo (e.g. zoneinfo.ZoneInfo)
    timezone: Any | None  # noqa: ANN401


class ContactRecord(Protocol):
    id: Any
    campaign_id: Any
    phone_number: str
    state: str
    attempts_count: int
    do_not_call: bool


class CallAttemptRecord(Protocol):
    id: Any
    contact_id: Any
    campaign_id: Any
    attempt_number: int
    provider_call_id: str | None


class CampaignRepositoryProtocol(Protocol):
    def list_running(self) -> Sequence[CampaignRecord]: ...


class ContactRepositoryProtocol(Protocol):
    def list_by_campaign(self, campaign_id: Any) -> Sequence[ContactRecord]: ...

    def update_after_scheduled(
        self,
        *,
        contact_id: Any,
        new_state: str,
        new_attempts_count: int,
        last_attempt_at: datetime,
    ) -> None: ...

    def revert_after_failure(
        self,
        *,
        contact_id: Any,
        previous_state: str,
        previous_attempts_count: int,
    ) -> None: ...


class CallAttemptRepositoryProtocol(Protocol):
    def create(
        self,
        *,
        contact_id: Any,
        campaign_id: Any,
        attempt_number: int,
        created_at: datetime,
    ) -> CallAttemptRecord: ...

    def set_provider_call_id(self, *, attempt_id: Any, provider_call_id: str) -> None: ...


class CallScheduler:
    """Pure call scheduler.

    Runs one *deterministic* tick.
    - selects eligible contacts
    - creates CallAttempt BEFORE initiating provider call
    - marks contact IN_PROGRESS and increments attempts_count
    """

    def __init__(
        self,
        *,
        campaigns: CampaignRepositoryProtocol,
        contacts: ContactRepositoryProtocol,
        attempts: CallAttemptRepositoryProtocol,
        config: CallSchedulerConfig | None = None,
        telephony_provider: TelephonyProviderProtocol | None = None,
        from_number: str = "",
        callback_url: str = "",
        clock: ClockProtocol | None = None,
    ) -> None:
        self._campaigns = campaigns
        self._contacts = contacts
        self._attempts = attempts
        self._telephony = telephony_provider
        self._config = config or CallSchedulerConfig()
        self._from_number = from_number
        self._callback_url = callback_url
        self._clock = clock or _SystemClock()

        if self._config.max_concurrent_calls <= 0:
            raise ValueError("max_concurrent_calls must be > 0")
        if self._config.batch_size <= 0:
            raise ValueError("batch_size must be > 0")

    def run_once(self, *, now: datetime | None = None) -> int:
        """Run one scheduler tick. Returns number of initiated calls."""
        tick_now = now or self._clock.now()

        initiated = 0
        for campaign in self._campaigns.list_running():
            if campaign.status != CAMPAIGN_STATUS_RUNNING:
                continue
            if not _is_within_call_window(campaign, tick_now):
                continue

            contacts = list(self._contacts.list_by_campaign(campaign.id))
            eligible = [
                c for c in contacts if _is_contact_eligible(campaign=campaign, contact=c)
            ]

            for contact in eligible[: self._config.batch_size]:
                if initiated >= self._config.max_concurrent_calls:
                    return initiated

                prev_state = contact.state
                prev_attempts = contact.attempts_count
                attempt_number = prev_attempts + 1

                # 1) Create attempt record BEFORE provider call (acceptance requirement)
                attempt = self._attempts.create(
                    contact_id=contact.id,
                    campaign_id=campaign.id,
                    attempt_number=attempt_number,
                    created_at=tick_now,
                )

                # 2) Mark contact as scheduled/in progress
                self._contacts.update_after_scheduled(
                    contact_id=contact.id,
                    new_state=CONTACT_STATE_IN_PROGRESS,
                    new_attempts_count=attempt_number,
                    last_attempt_at=tick_now,
                )

                # 3) Initiate call (optional if no provider configured)
                if self._telephony is not None:
                    try:
                        provider_call_id = self._telephony.initiate_call(
                            to_number=contact.phone_number,
                            from_number=self._from_number,
                            callback_url=self._callback_url,
                            metadata={
                                "campaign_id": str(campaign.id),
                                "contact_id": str(contact.id),
                                "attempt_id": str(attempt.id),
                            },
                        )
                        self._attempts.set_provider_call_id(
                            attempt_id=attempt.id,
                            provider_call_id=provider_call_id,
                        )
                    except Exception:
                        # Keep core robust: revert contact state/attempts if provider fails
                        self._contacts.revert_after_failure(
                            contact_id=contact.id,
                            previous_state=prev_state,
                            previous_attempts_count=prev_attempts,
                        )
                        continue

                initiated += 1

        return initiated


# -----------------------------
# Helpers
# -----------------------------
class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def _is_contact_eligible(*, campaign: CampaignRecord, contact: ContactRecord) -> bool:
    if contact.do_not_call:
        return False
    if contact.state not in (CONTACT_STATE_PENDING, CONTACT_STATE_NOT_REACHED):
        return False
    if contact.attempts_count >= campaign.max_attempts:
        return False
    return True


def _is_within_call_window(campaign: CampaignRecord, now: datetime) -> bool:
    start = campaign.allowed_call_start_local
    end = campaign.allowed_call_end_local

    tz = getattr(campaign, "timezone", None) or timezone.utc
    now_local = now.astimezone(tz).time()

    # Normal window (e.g. 09:00-18:00)
    if start <= end:
        return start <= now_local <= end

    # Overnight window (e.g. 22:00-06:00)
    return now_local >= start or now_local <= end
