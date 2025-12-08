from __future__ import annotations

import importlib
import signal
import time
from dataclasses import dataclass
from threading import Event
from types import ModuleType
from typing import Any, Callable, Protocol


class Runnable(Protocol):
    """Basic contract for worker cycles."""

    def run_cycle(self) -> None:  # pragma: no cover - Protocol definition
        ...


def load_factory(path: str) -> Callable[..., Any]:
    """Load a callable factory from module path notation module:attr."""
    if ":" not in path:
        raise ValueError(f"Invalid import path '{path}'. Expected format module:attr.")
    module_name, attr_name = path.split(":", 1)
    module: ModuleType = importlib.import_module(module_name)
    factory = getattr(module, attr_name, None)
    if factory is None or not callable(factory):
        raise ValueError(
            f"Resolved attribute '{attr_name}' in '{module_name}' is not callable."
        )
    return factory


@dataclass
class WorkerLoop:
    """Deterministic loop runner with graceful shutdown support."""

    runnable: Runnable
    interval_seconds: float
    sleep_fn: Callable[[float], None] = time.sleep

    def run(self, max_cycles: int | None = None, stop_event: Event | None = None) -> None:
        """Run loop forever or up to max_cycles."""
        cycles = 0
        stop_event = stop_event or Event()
        self._install_signal_handlers(stop_event)

        while not stop_event.is_set():
            self.runnable.run_cycle()
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            if stop_event.is_set():
                break
            self.sleep_fn(self.interval_seconds)

    @staticmethod
    def _install_signal_handlers(stop_event: Event) -> None:
        def handler(signum: int, _: Any) -> None:
            stop_event.set()

        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)