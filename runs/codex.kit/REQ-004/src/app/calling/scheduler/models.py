from __future__ import annotations

from dataclasses import dataclass, field
from datetime import tzinfo, timezone
from typing import List
from uuid import UUID


@dataclass(frozen=True)
class SchedulerSettings:
    """Runtime knobs for scheduler behavior."""

    callback_url: str
    batch_size: int = 25
    timezone: tzinfo = timezone.utc
    prefetch_factor: int = 3

    def __post_init__(self) -> None:
        if self.batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if self.prefetch_factor < 1:
            raise ValueError("prefetch_factor must be >= 1")


@dataclass(frozen=True)
class ScheduledAttempt:
    """Outcome of a single contact scheduling decision."""

    contact_id: UUID
    call_attempt_id: UUID
    call_id: str


@dataclass(frozen=True)
class SchedulerRunResult:
    """Summary returned after a scheduler execution."""

    scheduled: List[ScheduledAttempt] = field(default_factory=list)
    skipped_contacts: List[UUID] = field(default_factory=list)
    capacity_exhausted: bool = False
    fetched_candidates: int = 0
    available_capacity: int = 0