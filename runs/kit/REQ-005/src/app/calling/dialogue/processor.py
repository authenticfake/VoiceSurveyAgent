from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Dict, List, Mapping, MutableMapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.db.models import (
    CallAttempt,
    CallOutcome,
    Campaign,
    Contact,
    ContactState,
    EventType,
    SurveyResponse,
)

from app.events.bus.publisher import DbSurveyEventPublisher, SurveyEvent
from .enums import ConsentDecision, TelephonyEventName
from .exceptions import (
    CallAttemptNotFoundError,
    SurveyAnswerMismatchError,
    UnsupportedTelephonyEventError,
)
from .models import SurveyAnswerPayload, TelephonyEventPayload

logger = logging.getLogger(__name__)


class TelephonyEventProcessor:
    """Handles provider webhook events and updates domain entities accordingly."""

    def __init__(
        self,
        session: Session,
        event_publisher: DbSurveyEventPublisher,
        utc_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.event_publisher = event_publisher
        self.utc_clock = utc_clock or (lambda: datetime.now(timezone.utc))
        self._handlers = {
            TelephonyEventName.CALL_INITIATED: self._handle_progress_event,
            TelephonyEventName.CALL_RINGING: self._handle_progress_event,
            TelephonyEventName.CALL_ANSWERED: self._handle_answered,
            TelephonyEventName.CALL_COMPLETED: self._handle_completed,
            TelephonyEventName.CALL_FAILED: self._handle_terminal_failure,
            TelephonyEventName.CALL_NO_ANSWER: self._handle_terminal_failure,
            TelephonyEventName.CALL_BUSY: self._handle_terminal_failure,
        }

    def process(self, payload: TelephonyEventPayload) -> None:
        call_attempt = self._load_call_attempt(payload)
        handler = self._handlers.get(payload.event)
        if handler is None:
            raise UnsupportedTelephonyEventError(f"Unsupported event: {payload.event}")
        handler(call_attempt, payload)
        self.session.flush()
        self.session.commit()

    # --- lookup helpers -------------------------------------------------
    def _load_call_attempt(self, payload: TelephonyEventPayload) -> CallAttempt:
        stmt = select(CallAttempt).where(
            CallAttempt.call_id == payload.call_id
        )
        model = self.session.scalar(stmt)
        if model is None and payload.provider_call_id:
            stmt = select(CallAttempt).where(
                CallAttempt.provider_call_id == payload.provider_call_id
            )
            model = self.session.scalar(stmt)
        if model is None:
            raise CallAttemptNotFoundError(
                f"CallAttempt for call_id={payload.call_id} / provider_call_id={payload.provider_call_id} not found"
            )
        return model

    # --- event handlers -------------------------------------------------
    def _handle_progress_event(self, call_attempt: CallAttempt, payload: TelephonyEventPayload) -> None:
        call_attempt.provider_raw_status = payload.event.value
        call_attempt.metadata = {**call_attempt.metadata, **payload.metadata}
        if call_attempt.started_at is None:
            call_attempt.started_at = payload.occurred_at
        logger.info(
            "Updated call attempt progress",
            extra={"call_id": call_attempt.call_id, "event": payload.event.value},
        )

    def _handle_answered(self, call_attempt: CallAttempt, payload: TelephonyEventPayload) -> None:
        call_attempt.answered_at = payload.occurred_at
        call_attempt.provider_raw_status = payload.event.value
        call_attempt.metadata = {**call_attempt.metadata, **payload.metadata}
        call_attempt.contact.state = ContactState.IN_PROGRESS
        call_attempt.contact.last_attempt_at = payload.occurred_at

    def _handle_completed(self, call_attempt: CallAttempt, payload: TelephonyEventPayload) -> None:
        if payload.dialogue is None:
            raise UnsupportedTelephonyEventError("Completed calls require dialogue payload.")
        dialogue = payload.dialogue
        call_attempt.metadata = {
            **call_attempt.metadata,
            **payload.metadata,
            "consent_status": dialogue.consent_status.value,
        }
        call_attempt.ended_at = payload.occurred_at
        call_attempt.provider_raw_status = payload.event.value
        contact = call_attempt.contact
        contact.last_attempt_at = payload.occurred_at

        if dialogue.consent_status == ConsentDecision.REFUSED:
            call_attempt.outcome = CallOutcome.REFUSED
            contact.state = ContactState.REFUSED
            contact.last_outcome = CallOutcome.REFUSED
            self._emit_event(
                call_attempt,
                payload,
                EventType.SURVEY_REFUSED,
                {"attempts_count": contact.attempts_count},
            )
            return

        answers = self._map_answers(dialogue.answers)
        call_attempt.outcome = CallOutcome.COMPLETED
        contact.state = ContactState.COMPLETED
        contact.last_outcome = CallOutcome.COMPLETED
        self._store_survey_response(call_attempt, answers, payload)
        self._emit_event(
            call_attempt,
            payload,
            EventType.SURVEY_COMPLETED,
            {
                "attempts_count": contact.attempts_count,
                "answers": answers,
            },
        )

    def _handle_terminal_failure(self, call_attempt: CallAttempt, payload: TelephonyEventPayload) -> None:
        call_attempt.ended_at = payload.occurred_at
        call_attempt.provider_raw_status = payload.event.value
        call_attempt.error_code = payload.error_code
        call_attempt.metadata = {**call_attempt.metadata, **payload.metadata}
        outcome_map = {
            TelephonyEventName.CALL_FAILED: CallOutcome.FAILED,
            TelephonyEventName.CALL_NO_ANSWER: CallOutcome.NO_ANSWER,
            TelephonyEventName.CALL_BUSY: CallOutcome.BUSY,
        }
        outcome = outcome_map[payload.event]
        call_attempt.outcome = outcome
        contact = call_attempt.contact
        contact.last_attempt_at = payload.occurred_at
        contact.last_outcome = outcome
        self._update_contact_after_failure(contact, call_attempt.campaign, payload, call_attempt)

    # --- helpers --------------------------------------------------------
    def _map_answers(self, answers: List[SurveyAnswerPayload]) -> Dict[int, Mapping[str, object]]:
        if len(answers) < 3:
            raise SurveyAnswerMismatchError("Provider payload must include all three question answers.")
        mapped: Dict[int, Mapping[str, object]] = {
            answer.question_number: {
                "answer_text": answer.answer_text,
                "confidence": answer.confidence,
            }
            for answer in answers
        }
        missing = {1, 2, 3} - mapped.keys()
        if missing:
            raise SurveyAnswerMismatchError(f"Missing answers for questions: {sorted(missing)}")
        return mapped

    def _store_survey_response(
        self,
        call_attempt: CallAttempt,
        answers: Dict[int, Mapping[str, object]],
        payload: TelephonyEventPayload,
    ) -> None:
        contact = call_attempt.contact
        existing = self.session.execute(
            select(SurveyResponse).where(SurveyResponse.contact_id == contact.id)
        ).scalar_one_or_none()
        if existing:
            logger.info("Survey response already stored; skipping duplicate save.", extra={"contact_id": str(contact.id)})
            return
        response = SurveyResponse(
            contact_id=contact.id,
            campaign_id=call_attempt.campaign_id,
            call_attempt_id=call_attempt.id,
            q1_answer=answers[1]["answer_text"],
            q2_answer=answers[2]["answer_text"],
            q3_answer=answers[3]["answer_text"],
            q1_confidence=answers[1]["confidence"],
            q2_confidence=answers[2]["confidence"],
            q3_confidence=answers[3]["confidence"],
            completed_at=payload.occurred_at,
        )
        self.session.add(response)

    def _update_contact_after_failure(
        self,
        contact: Contact,
        campaign: Campaign,
        payload: TelephonyEventPayload,
        call_attempt: CallAttempt,
    ) -> None:
        if contact.attempts_count >= campaign.max_attempts:
            contact.state = ContactState.NOT_REACHED
            self._emit_event(
                call_attempt,
                payload,
                EventType.SURVEY_NOT_REACHED,
                {"attempts_count": contact.attempts_count},
            )
        else:
            contact.state = ContactState.PENDING

    def _emit_event(
        self,
        call_attempt: CallAttempt,
        payload: TelephonyEventPayload,
        event_type: EventType,
        extra_payload: MutableMapping[str, object],
    ) -> None:
        event = SurveyEvent(
            event_type=event_type,
            campaign_id=call_attempt.campaign_id,
            contact_id=call_attempt.contact_id,
            call_attempt_id=call_attempt.id,
            payload={
                "call_id": call_attempt.call_id,
                "provider_call_id": call_attempt.provider_call_id,
                **extra_payload,
            },
            occurred_at=payload.occurred_at,
        )
        self.event_publisher.publish(event)