from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Callable, Iterable, List, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from app.calling.scheduler.models import (
    ScheduledAttempt,
    SchedulerRunResult,
    SchedulerSettings,
)
from app.calling.telephony.models import OutboundCallRequest, QuestionPrompt
from app.calling.telephony.provider import TelephonyProvider, TelephonyProviderError
from app.infra.db import models as db_models

logger = logging.getLogger(__name__)


class SchedulerError(RuntimeError):
    """Base scheduler exception."""


class ProviderConfigurationError(SchedulerError):
    """Raised when no usable provider configuration is available."""


@dataclass(frozen=True)
class CandidateContactSnapshot:
    contact_id: uuid.UUID
    campaign_id: uuid.UUID
    attempts_count: int
    last_attempt_at: Optional[datetime]
    preferred_language: db_models.ContactLanguage
    phone_number: str
    max_attempts: int
    retry_interval_minutes: int
    allowed_call_start_local: time
    allowed_call_end_local: time
    campaign_language: db_models.CampaignLanguage


class SchedulerService:
    """Selects eligible contacts and starts outbound telephony calls."""

    _ELIGIBLE_STATES = (
        db_models.ContactState.PENDING,
        db_models.ContactState.NOT_REACHED,
    )

    def __init__(
        self,
        session_factory: sessionmaker,
        telephony_provider: TelephonyProvider,
        settings: SchedulerSettings,
        clock: Callable[[], datetime] = datetime.utcnow,
        call_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        self._session_factory = session_factory
        self._telephony_provider = telephony_provider
        self._settings = settings
        self._clock = clock
        self._call_id_factory = call_id_factory

    def run(self) -> SchedulerRunResult:
        now = self._clock()
        current_time_local = now.astimezone(self._settings.timezone).time()
        with self._session_factory() as session:
            config = self._load_provider_config(session)
            target_capacity, active_calls = self._determine_capacity(session, config.max_concurrent_calls)
            if target_capacity <= 0:
                return SchedulerRunResult(
                    capacity_exhausted=True,
                    fetched_candidates=0,
                    available_capacity=max(0, config.max_concurrent_calls - active_calls),
                )
            fetch_limit = target_capacity * self._settings.prefetch_factor
            candidates = self._load_candidate_snapshots(session, fetch_limit)
        scheduled: List[ScheduledAttempt] = []
        skipped: List[uuid.UUID] = []

        for candidate in candidates:
            if len(scheduled) >= target_capacity:
                break
            if not self._is_within_window(candidate, current_time_local):
                skipped.append(candidate.contact_id)
                continue
            if not self._retry_interval_elapsed(candidate, now):
                continue
            try:
                attempt = self._schedule_contact(candidate.contact_id, now)
            except TelephonyProviderError:
                logger.warning("Telephony provider failure for contact %s", candidate.contact_id)
                continue
            if attempt:
                scheduled.append(attempt)
            else:
                skipped.append(candidate.contact_id)

        capacity_exhausted = len(scheduled) >= target_capacity
        return SchedulerRunResult(
            scheduled=scheduled,
            skipped_contacts=skipped,
            capacity_exhausted=capacity_exhausted,
            fetched_candidates=len(candidates),
            available_capacity=target_capacity,
        )

    def _load_provider_config(self, session: Session) -> db_models.ProviderConfiguration:
        config = session.execute(
            sa.select(db_models.ProviderConfiguration).order_by(db_models.ProviderConfiguration.created_at.asc()).limit(1)
        ).scalar_one_or_none()
        if not config:
            raise ProviderConfigurationError("No provider configuration found")
        if config.max_concurrent_calls <= 0:
            raise ProviderConfigurationError("Provider configuration has invalid max_concurrent_calls")
        return config

    def _determine_capacity(self, session: Session, max_concurrent_calls: int) -> tuple[int, int]:
        active_calls = session.execute(
            sa.select(sa.func.count()).select_from(db_models.CallAttempt).where(db_models.CallAttempt.ended_at.is_(None))
        ).scalar_one()
        available = max(0, int(max_concurrent_calls) - int(active_calls or 0))
        target = min(self._settings.batch_size, available)
        return target, active_calls or 0

    def _load_candidate_snapshots(self, session: Session, limit: int) -> List[CandidateContactSnapshot]:
        stmt = (
            sa.select(
                db_models.Contact.id,
                db_models.Contact.campaign_id,
                db_models.Contact.attempts_count,
                db_models.Contact.last_attempt_at,
                db_models.Contact.preferred_language,
                db_models.Contact.phone_number,
                db_models.Campaign.max_attempts,
                db_models.Campaign.retry_interval_minutes,
                db_models.Campaign.allowed_call_start_local,
                db_models.Campaign.allowed_call_end_local,
                db_models.Campaign.language,
            )
            .join(db_models.Campaign, db_models.Campaign.id == db_models.Contact.campaign_id)
            .where(db_models.Contact.state.in_(self._ELIGIBLE_STATES))
            .where(db_models.Contact.do_not_call.is_(False))
            .where(db_models.Contact.attempts_count < db_models.Campaign.max_attempts)
            .order_by(sa.nullsfirst(db_models.Contact.last_attempt_at), db_models.Contact.created_at)
            .limit(limit)
        )
        rows = session.execute(stmt).all()
        return [
            CandidateContactSnapshot(
                contact_id=row[0],
                campaign_id=row[1],
                attempts_count=row[2],
                last_attempt_at=row[3],
                preferred_language=row[4],
                phone_number=row[5],
                max_attempts=row[6],
                retry_interval_minutes=row[7],
                allowed_call_start_local=row[8],
                allowed_call_end_local=row[9],
                campaign_language=row[10],
            )
            for row in rows
        ]

    def _schedule_contact(self, contact_id: uuid.UUID, now: datetime) -> Optional[ScheduledAttempt]:
        with self._session_factory() as session, session.begin():
            row = session.execute(
                sa.select(db_models.Contact, db_models.Campaign)
                .join(db_models.Campaign, db_models.Campaign.id == db_models.Contact.campaign_id)
                .where(db_models.Contact.id == contact_id)
                .with_for_update(skip_locked=True)
            ).first()
            if not row:
                return None
            contact, campaign = row
            current_time_local = now.astimezone(self._settings.timezone).time()
            if contact.state not in self._ELIGIBLE_STATES:
                return None
            if contact.attempts_count >= campaign.max_attempts:
                return None
            if not self._is_within_window(
                CandidateContactSnapshot(
                    contact_id=contact.id,
                    campaign_id=campaign.id,
                    attempts_count=contact.attempts_count,
                    last_attempt_at=contact.last_attempt_at,
                    preferred_language=contact.preferred_language,
                    phone_number=contact.phone_number,
                    max_attempts=campaign.max_attempts,
                    retry_interval_minutes=campaign.retry_interval_minutes,
                    allowed_call_start_local=campaign.allowed_call_start_local,
                    allowed_call_end_local=campaign.allowed_call_end_local,
                    campaign_language=campaign.language,
                ),
                current_time_local,
            ):
                return None
            if not self._retry_interval_elapsed(
                CandidateContactSnapshot(
                    contact_id=contact.id,
                    campaign_id=campaign.id,
                    attempts_count=contact.attempts_count,
                    last_attempt_at=contact.last_attempt_at,
                    preferred_language=contact.preferred_language,
                    phone_number=contact.phone_number,
                    max_attempts=campaign.max_attempts,
                    retry_interval_minutes=campaign.retry_interval_minutes,
                    allowed_call_start_local=campaign.allowed_call_start_local,
                    allowed_call_end_local=campaign.allowed_call_end_local,
                    campaign_language=campaign.language,
                ),
                now,
            ):
                return None

            call_id = self._call_id_factory()
            request = self._build_outbound_request(contact, campaign, call_id)
            response = self._telephony_provider.start_outbound_call(request)

            attempt_number = contact.attempts_count + 1
            call_attempt = db_models.CallAttempt(
                contact_id=contact.id,
                campaign_id=campaign.id,
                attempt_number=attempt_number,
                call_id=call_id,
                provider_call_id=response.provider_call_id,
                started_at=now,
                provider_raw_status=response.provider_status,
                metadata=response.raw_payload,
            )
            contact.state = db_models.ContactState.IN_PROGRESS
            contact.attempts_count = attempt_number
            contact.last_attempt_at = now
            contact.last_outcome = None
            session.add(call_attempt)
            session.flush()
            return ScheduledAttempt(
                contact_id=contact.id,
                call_attempt_id=call_attempt.id,
                call_id=call_id,
            )

    def _build_outbound_request(
        self,
        contact: db_models.Contact,
        campaign: db_models.Campaign,
        call_id: str,
    ) -> OutboundCallRequest:
        language = self._resolve_language(contact, campaign)
        questions = [
            QuestionPrompt(position=1, text=campaign.question_1_text, answer_type=campaign.question_1_type.value),
            QuestionPrompt(position=2, text=campaign.question_2_text, answer_type=campaign.question_2_type.value),
            QuestionPrompt(position=3, text=campaign.question_3_text, answer_type=campaign.question_3_type.value),
        ]
        metadata = {
            "campaign_id": str(campaign.id),
            "contact_id": str(contact.id),
            "call_id": call_id,
            "preferred_language": language,
        }
        from_number = getattr(campaign, "outbound_number", None)
        return OutboundCallRequest(
            call_id=call_id,
            to_number=contact.phone_number,
            from_number=from_number or "",
            language=language,
            callback_url=self._settings.callback_url,
            intro_script=campaign.intro_script,
            questions=questions,
            metadata=metadata,
        )

    def _resolve_language(self, contact: db_models.Contact, campaign: db_models.Campaign) -> str:
        if contact.preferred_language and contact.preferred_language != db_models.ContactLanguage.AUTO:
            return contact.preferred_language.value
        return campaign.language.value

    @staticmethod
    def _is_within_window(candidate: CandidateContactSnapshot, current_time_local: time) -> bool:
        start = candidate.allowed_call_start_local
        end = candidate.allowed_call_end_local
        if start <= end:
            return start <= current_time_local <= end
        # Window crosses midnight
        return current_time_local >= start or current_time_local <= end

    @staticmethod
    def _retry_interval_elapsed(candidate: CandidateContactSnapshot, now: datetime) -> bool:
        if not candidate.last_attempt_at:
            return True
        delay = timedelta(minutes=int(candidate.retry_interval_minutes))
        return candidate.last_attempt_at <= now - delay