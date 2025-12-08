from __future__ import annotations

from typing import Any, Dict

from app.workers.base import Runnable

INVOCATIONS: Dict[str, int] = {"count": 0}


class DummyScheduler(Runnable):
    def run_cycle(self) -> None:
        INVOCATIONS["count"] += 1


def build_scheduler(_: Any) -> DummyScheduler:
    return DummyScheduler()