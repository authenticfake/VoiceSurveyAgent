from __future__ import annotations

from typing import Any, List

from app.workers.email import EmailEventHandler, SurveyEvent

HANDLED_EVENTS: List[SurveyEvent] = []


class DummyEmailHandler(EmailEventHandler):
    def handle(self, event: SurveyEvent) -> None:
        HANDLED_EVENTS.append(event)


def build_handler(_: Any) -> DummyEmailHandler:
    HANDLED_EVENTS.clear()
    return DummyEmailHandler()