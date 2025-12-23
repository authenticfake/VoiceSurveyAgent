"""
Survey response persistence service.

REQ-014: Survey response persistence

Handles atomic persistence of survey responses, updating contact state,
and call attempt outcomes within a single transaction.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import inspect
from typing import Protocol
from uuid import UUID

try:
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import AsyncSession
except ModuleNotFoundError:  # pragma: no cover
    # Keep module importable for sync-only logic tests / minimal environments.
    select = None  # type: ignore[assignment]
    update = None  # type: ignore[assignment]

    class AsyncSession:  # type: ignore[no-redef]
        """Fallback AsyncSession type when SQLAlchemy is not installed."""

        pass


from app.dialogue.models import (
    CapturedAnswer,
    DialogueSession,
    DialogueSessionState,
)

try:
    from enum import Enum
    from typing import TYPE_CHECKING, Any

    if TYPE_CHECKING:  # pragma: no cover
        from app.dialogue.persistence_models import CallAttempt, Contact, SurveyResponse

    class ContactState(str, Enum):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        REFUSED = "refused"
        NOT_REACHED = "not_reached"
        EXCLUDED = "excluded"

    class ContactOutcome(str, Enum):
        COMPLETED = "completed"
        REFUSED = "refused"
        NO_ANSWER = "no_answer"
        BUSY = "busy"
        FAILED = "failed"

    CallAttempt = Any
    Contact = Any
    SurveyResponse = Any

except ModuleNotFoundError:  # pragma: no cover
    # Minimal fallback types/enums; async repos will still fail if used.
    from enum import Enum
    from typing import Any

    class ContactState(str, Enum):  # type: ignore[no-redef]
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        REFUSED = "refused"
        NOT_REACHED = "not_reached"
        EXCLUDED = "excluded"

    class ContactOutcome(str, Enum):  # type: ignore[no-redef]
        COMPLETED = "completed"
        REFUSED = "refused"
        NO_ANSWER = "no_answer"
        BUSY = "busy"
        FAILED = "failed"

    CallAttempt = Any  # type: ignore[no-redef]
    Contact = Any  # type: ignore[no-redef]
    SurveyResponse = Any  # type: ignore[no-redef]


from app.shared.logging import get_logger

logger = get_logger(__name__)


class PersistenceError(Exception):
    """Base exception for persistence errors."""

    pass


class TransactionError(PersistenceError):
    """Error during transaction execution."""

    pass


class NotFoundError(PersistenceError):
    """Entity not found error."""

    pass


@dataclass
class PersistenceResult:
    """Result of a persistence operation."""

    success: bool
    survey_response_id: UUID | None = None
    contact_id: UUID | None = None
    call_attempt_id: UUID | None = None
    error_message: str | None = None
    completed_at: datetime | None = None


class SurveyResponseRepositoryProtocol(Protocol):
    """Protocol for survey response repository."""

    async def create_survey_response(
        self,
        session: AsyncSession,
        contact_id: UUID,
        campaign_id: UUID,
        call_attempt_id: UUID,
        answers: list[CapturedAnswer],
    ) -> SurveyResponse:
        """Create a new survey response."""
        ...

    async def get_by_contact_and_campaign(
        self,
        session: AsyncSession,
        contact_id: UUID,
        campaign_id: UUID,
    ) -> SurveyResponse | None:
        """Get survey response by contact and campaign."""
        ...


class ContactRepositoryProtocol(Protocol):
    """Protocol for contact repository."""

    async def update_state(
        self,
        session: AsyncSession,
        contact_id: UUID,
        state: ContactState,
        outcome: ContactOutcome | None = None,
    ) -> None:
        """Update contact state."""
        ...

    async def get_by_id(
        self,
        session: AsyncSession,
        contact_id: UUID,
    ) -> Contact | None:
        """Get contact by ID."""
        ...


class CallAttemptRepositoryProtocol(Protocol):
    """Protocol for call attempt repository."""

    async def update_outcome(
        self,
        session: AsyncSession,
        call_attempt_id: UUID,
        outcome: str,
        ended_at: datetime,
    ) -> None:
        """Update call attempt outcome."""
        ...

    async def get_by_id(
        self,
        session: AsyncSession,
        call_attempt_id: UUID,
    ) -> CallAttempt | None:
        """Get call attempt by ID."""
        ...


class SurveyResponseRepository:
    """Repository for survey response persistence."""

    async def create_survey_response(
        self,
        session: AsyncSession,
        contact_id: UUID,
        campaign_id: UUID,
        call_attempt_id: UUID,
        answers: list[CapturedAnswer],
    ) -> SurveyResponse:
        """Create a new survey response with all 3 answers."""
        if select is None or update is None:
            raise RuntimeError("SQLAlchemy not installed: async persistence is unavailable")

        if len(answers) != 3:
            raise ValueError(f"Expected 3 answers, got {len(answers)}")
    
        from app.dialogue.persistence_models import SurveyResponse


        sorted_answers = sorted(answers, key=lambda a: a.question_index)
        completed_at = datetime.now(timezone.utc)

        survey_response = SurveyResponse(
            contact_id=contact_id,
            campaign_id=campaign_id,
            call_attempt_id=call_attempt_id,
            q1_answer=sorted_answers[0].answer_text,
            q2_answer=sorted_answers[1].answer_text,
            q3_answer=sorted_answers[2].answer_text,
            q1_confidence=sorted_answers[0].confidence,
            q2_confidence=sorted_answers[1].confidence,
            q3_confidence=sorted_answers[2].confidence,
            completed_at=completed_at,
        )

        session.add(survey_response)
        await session.flush()

        logger.info(
            f"Created survey response id={survey_response.id} "
            f"contact_id={contact_id} campaign_id={campaign_id}"
        )

        return survey_response

    async def get_by_contact_and_campaign(
        self,
        session: AsyncSession,
        contact_id: UUID,
        campaign_id: UUID,
    ) -> SurveyResponse | None:
        if select is None:
            raise RuntimeError("SQLAlchemy not installed: async persistence is unavailable")
        
        from app.dialogue.persistence_models import SurveyResponse

        stmt = select(SurveyResponse).where(
            SurveyResponse.contact_id == contact_id,
            SurveyResponse.campaign_id == campaign_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class ContactRepository:
    """Repository for contact persistence."""

    async def update_state(
        self,
        session: AsyncSession,
        contact_id: UUID,
        state: ContactState,
        outcome: ContactOutcome | None = None,
    ) -> None:
        if update is None:
            raise RuntimeError("SQLAlchemy not installed: async persistence is unavailable")
        
        from app.dialogue.persistence_models import Contact
        
        values: dict = {
            "state": state.value,
            "updated_at": datetime.now(timezone.utc),
        }
        if outcome is not None:
            values["last_outcome"] = outcome.value

        stmt = update(Contact).where(Contact.id == contact_id).values(**values)
        await session.execute(stmt)

        logger.info(
            f"Updated contact state contact_id={contact_id} "
            f"state={state.value} outcome={outcome}"
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        contact_id: UUID,
    ) -> Contact | None:
        if select is None:
            raise RuntimeError("SQLAlchemy not installed: async persistence is unavailable")
        
        from app.dialogue.persistence_models import Contact

        stmt = select(Contact).where(Contact.id == contact_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class CallAttemptRepository:
    """Repository for call attempt persistence."""

    async def update_outcome(
        self,
        session: AsyncSession,
        call_attempt_id: UUID,
        outcome: str,
        ended_at: datetime,
    ) -> None:
        if update is None:
            raise RuntimeError("SQLAlchemy not installed: async persistence is unavailable")
        
        from app.dialogue.persistence_models import CallAttempt

        stmt = (
            update(CallAttempt)
            .where(CallAttempt.id == call_attempt_id)
            .values(
                outcome=outcome,
                ended_at=ended_at,
            )
        )
        await session.execute(stmt)

        logger.info(
            f"Updated call attempt outcome call_attempt_id={call_attempt_id} "
            f"outcome={outcome}"
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        call_attempt_id: UUID,
    ) -> CallAttempt | None:
        if select is None:
            raise RuntimeError("SQLAlchemy not installed: async persistence is unavailable")
        
        from app.dialogue.persistence_models import CallAttempt

        stmt = select(CallAttempt).where(CallAttempt.id == call_attempt_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class SurveyPersistenceService:
    """Service for persisting survey responses atomically."""

    def __init__(
        self,
        survey_response_repo: SurveyResponseRepository | None = None,
        contact_repo: ContactRepository | None = None,
        call_attempt_repo: CallAttemptRepository | None = None,
    ) -> None:
        self._survey_response_repo = survey_response_repo or SurveyResponseRepository()
        self._contact_repo = contact_repo or ContactRepository()
        self._call_attempt_repo = call_attempt_repo or CallAttemptRepository()

    async def persist_completed_survey(
        self,
        session: AsyncSession,
        dialogue_session: DialogueSession,
    ) -> PersistenceResult:
        if dialogue_session.call_context is None:
            return PersistenceResult(
                success=False,
                error_message="Dialogue session has no call context",
            )

        if not dialogue_session.has_all_answers():
            return PersistenceResult(
                success=False,
                error_message=f"Expected 3 answers, got {len(dialogue_session.answers)}",
            )

        call_context = dialogue_session.call_context
        contact_id = call_context.contact_id
        campaign_id = call_context.campaign_id
        call_attempt_id = call_context.call_attempt_id

        try:
            contact = await self._contact_repo.get_by_id(session, contact_id)
            if contact is None:
                raise NotFoundError(f"Contact not found: {contact_id}")

            call_attempt = await self._call_attempt_repo.get_by_id(session, call_attempt_id)
            if call_attempt is None:
                raise NotFoundError(f"CallAttempt not found: {call_attempt_id}")

            existing = await self._survey_response_repo.get_by_contact_and_campaign(
                session, contact_id, campaign_id
            )
            if existing is not None:
                logger.info(
                    f"Survey response already exists for contact_id={contact_id} "
                    f"campaign_id={campaign_id}, returning existing"
                )
                return PersistenceResult(
                    success=True,
                    survey_response_id=existing.id,
                    contact_id=contact_id,
                    call_attempt_id=call_attempt_id,
                    completed_at=existing.completed_at,
                )

            completed_at = datetime.now(timezone.utc)

            survey_response = await self._survey_response_repo.create_survey_response(
                session=session,
                contact_id=contact_id,
                campaign_id=campaign_id,
                call_attempt_id=call_attempt_id,
                answers=dialogue_session.answers,
            )

            await self._contact_repo.update_state(
                session=session,
                contact_id=contact_id,
                state=ContactState.COMPLETED,
                outcome=ContactOutcome.COMPLETED,
            )

            await self._call_attempt_repo.update_outcome(
                session=session,
                call_attempt_id=call_attempt_id,
                outcome="completed",
                ended_at=completed_at,
            )

            return PersistenceResult(
                success=True,
                survey_response_id=survey_response.id,
                contact_id=contact_id,
                call_attempt_id=call_attempt_id,
                completed_at=completed_at,
            )

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to persist survey response: {e} "
                f"contact_id={contact_id} campaign_id={campaign_id}"
            )
            raise TransactionError(f"Failed to persist survey response: {e}") from e

    async def persist_refused_survey(
        self,
        session: AsyncSession,
        dialogue_session: DialogueSession,
    ) -> PersistenceResult:
        if dialogue_session.call_context is None:
            return PersistenceResult(
                success=False,
                error_message="Dialogue session has no call context",
            )

        call_context = dialogue_session.call_context
        contact_id = call_context.contact_id
        call_attempt_id = call_context.call_attempt_id

        try:
            ended_at = datetime.now(timezone.utc)

            await self._contact_repo.update_state(
                session=session,
                contact_id=contact_id,
                state=ContactState.REFUSED,
                outcome=ContactOutcome.REFUSED,
            )

            await self._call_attempt_repo.update_outcome(
                session=session,
                call_attempt_id=call_attempt_id,
                outcome="refused",
                ended_at=ended_at,
            )

            return PersistenceResult(
                success=True,
                contact_id=contact_id,
                call_attempt_id=call_attempt_id,
                completed_at=ended_at,
            )

        except Exception as e:
            logger.error(f"Failed to persist refused survey: {e}")
            raise TransactionError(f"Failed to persist refused survey: {e}") from e

    # ---------------------------------------------------------------------
    # Sync API (test-friendly)
    # ---------------------------------------------------------------------
    def persist_completed_survey_sync(
        self,
        session: object,
        dialogue_session: DialogueSession,
    ) -> PersistenceResult:
        """Sync variant of persist_completed_survey (for sync-only tests)."""

        if inspect.iscoroutinefunction(self._contact_repo.get_by_id) or inspect.iscoroutinefunction(
            self._survey_response_repo.get_by_contact_and_campaign
        ):
            raise TypeError(
                "persist_completed_survey_sync requires sync repositories; inject in-memory repos"
            )

        if dialogue_session.call_context is None:
            return PersistenceResult(
                success=False,
                error_message="Dialogue session has no call context",
            )

        if not dialogue_session.has_all_answers():
            return PersistenceResult(
                success=False,
                error_message=f"Expected 3 answers, got {len(dialogue_session.answers)}",
            )

        call_context = dialogue_session.call_context
        contact_id = call_context.contact_id
        campaign_id = call_context.campaign_id
        call_attempt_id = call_context.call_attempt_id

        def _do() -> PersistenceResult:
            contact = self._contact_repo.get_by_id(session, contact_id)
            if contact is None:
                raise NotFoundError(f"Contact not found: {contact_id}")

            call_attempt = self._call_attempt_repo.get_by_id(session, call_attempt_id)
            if call_attempt is None:
                raise NotFoundError(f"CallAttempt not found: {call_attempt_id}")

            existing = self._survey_response_repo.get_by_contact_and_campaign(
                session, contact_id, campaign_id
            )
            if existing is not None:
                return PersistenceResult(
                    success=True,
                    survey_response_id=existing.id,
                    contact_id=contact_id,
                    call_attempt_id=call_attempt_id,
                    completed_at=existing.completed_at,
                )

            completed_at = datetime.now(timezone.utc)

            survey_response = self._survey_response_repo.create_survey_response(
                session=session,
                contact_id=contact_id,
                campaign_id=campaign_id,
                call_attempt_id=call_attempt_id,
                answers=dialogue_session.answers,
            )

            self._contact_repo.update_state(
                session=session,
                contact_id=contact_id,
                state=ContactState.COMPLETED,
                outcome=ContactOutcome.COMPLETED,
            )

            self._call_attempt_repo.update_outcome(
                session=session,
                call_attempt_id=call_attempt_id,
                outcome="completed",
                ended_at=completed_at,
            )

            return PersistenceResult(
                success=True,
                survey_response_id=survey_response.id,
                contact_id=contact_id,
                call_attempt_id=call_attempt_id,
                completed_at=completed_at,
            )

        try:
            begin = getattr(session, "begin", None)
            if begin is None:
                return _do()
            with begin():
                return _do()
        except NotFoundError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to persist survey response: {e}") from e

    def persist_refused_survey_sync(
        self,
        session: object,
        dialogue_session: DialogueSession,
    ) -> PersistenceResult:
        """Sync variant of persist_refused_survey (for sync-only tests)."""

        if inspect.iscoroutinefunction(self._contact_repo.update_state):
            raise TypeError(
                "persist_refused_survey_sync requires sync repositories; inject in-memory repos"
            )

        if dialogue_session.call_context is None:
            return PersistenceResult(
                success=False,
                error_message="Dialogue session has no call context",
            )

        call_context = dialogue_session.call_context
        contact_id = call_context.contact_id
        call_attempt_id = call_context.call_attempt_id

        def _do() -> PersistenceResult:
            ended_at = datetime.now(timezone.utc)

            self._contact_repo.update_state(
                session=session,
                contact_id=contact_id,
                state=ContactState.REFUSED,
                outcome=ContactOutcome.REFUSED,
            )

            self._call_attempt_repo.update_outcome(
                session=session,
                call_attempt_id=call_attempt_id,
                outcome="refused",
                ended_at=ended_at,
            )

            return PersistenceResult(
                success=True,
                contact_id=contact_id,
                call_attempt_id=call_attempt_id,
                completed_at=ended_at,
            )

        try:
            begin = getattr(session, "begin", None)
            if begin is None:
                return _do()
            with begin():
                return _do()
        except Exception as e:
            raise TransactionError(f"Failed to persist refused survey: {e}") from e
