from __future__ import annotations

import argparse

from app.infra.config import AppSettings, get_app_settings
from app.infra.observability import configure_logging, get_logger
from app.workers.base import Runnable, WorkerLoop, load_factory

logger = get_logger("app.workers.scheduler")


class SchedulerRunnable(Runnable):
    """Protocol alias for documentation/typing."""


def _build_runnable(settings: AppSettings) -> SchedulerRunnable:
    factory = load_factory(settings.scheduler.factory_path)
    runnable = factory(settings)
    if not isinstance(runnable, Runnable.__mro__[0]):  # type: ignore[attr-defined]
        # We cannot use isinstance with Protocol easily; rely on duck-typing.
        if not hasattr(runnable, "run_cycle"):
            raise TypeError("Scheduler runnable must expose run_cycle().")
    return runnable  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="scheduler-worker", description="Call scheduler worker loop"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scheduling cycle (useful for smoke tests).",
    )
    args = parser.parse_args(argv)

    settings = get_app_settings()
    configure_logging(
        service_name=settings.observability.service_name,
        level=settings.observability.log_level,
    )
    runnable = _build_runnable(settings)
    loop = WorkerLoop(runnable=runnable, interval_seconds=settings.scheduler.poll_interval_seconds)
    logger.info(
        "scheduler_started",
        extra={"extra_fields": {"environment": settings.environment}},
    )
    loop.run(max_cycles=1 if args.once else None)
    logger.info("scheduler_stopped")


if __name__ == "__main__":
    main()