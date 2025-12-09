"""
Survey response persistence service.

REQ-014: Survey response persistence

Handles atomic persistence of survey responses, updating contact state,
and call attempt outcomes within a single transaction.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dialogue.models import (
    CapturedAnswer,
    DialogueSession,
    DialogueSessionState,
)
from app.dialogue.persistence_models import (
    CallAttempt,
    Contact,
    ContactOutcome,
    ContactState,
    SurveyResponse,
)
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
        """Create a new survey response with all 3 answers.

        Args:
            session: Database session.
            contact_id: Contact UUID.
            campaign_id: Campaign UUID.
            call_attempt_id: Call attempt UUID.
            answers: List of captured answers (must be 3).

        Returns:
            Created SurveyResponse entity.

        Raises:
            ValueError: If answers count is not 3.
        """
        if len(answers) != 3:
            raise ValueError(f"Expected 3 answers, got {len(answers)}")

        # Sort answers by question index to ensure correct mapping
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
        """Get survey response by contact and campaign.

        Args:
            session: Database session.
            contact_id: Contact UUID.
            campaign_id: Campaign UUID.

        Returns:
            SurveyResponse if found, None otherwise.
        """
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
        """Update contact state and optionally last outcome.

        Args:
            session: Database session.
            contact_id: Contact UUID.
            state: New contact state.
            outcome: Optional last outcome.
        """
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
        """Get contact by ID.

        Args:
            session: Database session.
            contact_id: Contact UUID.

        Returns:
            Contact if found, None otherwise.
        """
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
        """Update call attempt outcome and end time.

        Args:
            session: Database session.
            call_attempt_id: Call attempt UUID.
            outcome: Outcome string (completed, refused, etc.).
            ended_at: End timestamp.
        """
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
        """Get call attempt by ID.

        Args:
            session: Database session.
            call_attempt_id: Call attempt UUID.

        Returns:
            CallAttempt if found, None otherwise.
        """
        stmt = select(CallAttempt).where(CallAttempt.id == call_attempt_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class SurveyPersistenceService:
    """Service for persisting survey responses atomically.

    Ensures all updates (survey response, contact state, call attempt outcome)
    are performed within a single transaction.
    """

    def __init__(
        self,
        survey_response_repo: SurveyResponseRepository | None = None,
        contact_repo: ContactRepository | None = None,
        call_attempt_repo: CallAttemptRepository | None = None,
    ) -> None:
        """Initialize the persistence service.

        Args:
            survey_response_repo: Survey response repository.
            contact_repo: Contact repository.
            call_attempt_repo: Call attempt repository.
        """
        self._survey_response_repo = survey_response_repo or SurveyResponseRepository()
        self._contact_repo = contact_repo or ContactRepository()
        self._call_attempt_repo = call_attempt_repo or CallAttemptRepository()

    async def persist_completed_survey(
        self,
        session: AsyncSession,
        dialogue_session: DialogueSession,
    ) -> PersistenceResult:
        """Persist a completed survey response atomically.

        This method:
        1. Creates a SurveyResponse with all 3 answers
        2. Updates Contact state to 'completed'
        3. Updates CallAttempt outcome to 'completed'

        All operations are performed within the provided session's transaction.

        Args:
            session: Database session (transaction managed by caller).
            dialogue_session: Completed dialogue session with answers.

        Returns:
            PersistenceResult with operation outcome.

        Raises:
            TransactionError: If any persistence operation fails.
            NotFoundError: If required entities are not found.
        """
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
            # Verify contact exists
            contact = await self._contact_repo.get_by_id(session, contact_id)
            if contact is None:
                raise NotFoundError(f"Contact not found: {contact_id}")

            # Verify call attempt exists
            call_attempt = await self._call_attempt_repo.get_by_id(
                session, call_attempt_id
            )
            if call_attempt is None:
                raise NotFoundError(f"CallAttempt not found: {call_attempt_id}")

            # Check for existing survey response (idempotency)
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

            # 1. Create survey response
            survey_response = await self._survey_response_repo.create_survey_response(
                session=session,
                contact_id=contact_id,
                campaign_id=campaign_id,
                call_attempt_id=call_attempt_id,
                answers=dialogue_session.answers,
            )

            # 2. Update contact state to completed
            await self._contact_repo.update_state(
                session=session,
                contact_id=contact_id,
                state=ContactState.COMPLETED,
                outcome=ContactOutcome.COMPLETED,
            )

            # 3. Update call attempt outcome to completed
            await self._call_attempt_repo.update_outcome(
                session=session,
                call_attempt_id=call_attempt_id,
                outcome="completed",
                ended_at=completed_at,
            )

            logger.info(
                f"Successfully persisted survey response "
                f"survey_response_id={survey_response.id} "
                f"contact_id={contact_id} "
                f"call_attempt_id={call_attempt_id}"
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
        """Persist a refused survey outcome.

        Updates contact state and call attempt outcome for refusal.

        Args:
            session: Database session.
            dialogue_session: Dialogue session with refusal.

        Returns:
            PersistenceResult with operation outcome.
        """
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

            # Update contact state to refused
            await self._contact_repo.update_state(
                session=session,
                contact_id=contact_id,
                state=ContactState.REFUSED,
                outcome=ContactOutcome.REFUSED,
            )

            # Update call attempt outcome to refused
            await self._call_attempt_repo.update_outcome(
                session=session,
                call_attempt_id=call_attempt_id,
                outcome="refused",
                ended_at=ended_at,
            )

            logger.info(
                f"Persisted refused survey contact_id={contact_id} "
                f"call_attempt_id={call_attempt_id}"
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