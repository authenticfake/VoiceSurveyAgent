"""
Tests for survey response persistence.

REQ-014: Survey response persistence
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app.dialogue.models import (
    CallContext,
    CapturedAnswer,
    DialoguePhase,
    DialogueSession,
    DialogueSessionState,
    ConsentState,
)
from app.dialogue.persistence import (
    CallAttemptRepository,
    ContactRepository,
    NotFoundError,
    PersistenceResult,
    SurveyPersistenceService,
    SurveyResponseRepository,
    TransactionError,
)
from app.dialogue.persistence_models import (
    CallAttempt,
    Contact,
    ContactOutcome,
    ContactState,
    SurveyResponse,
)


class TestSurveyResponseRepository:
    """Tests for SurveyResponseRepository."""

    @pytest.fixture
    def repository(self) -> SurveyResponseRepository:
        """Create repository instance."""
        return SurveyResponseRepository()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def sample_answers(self) -> list[CapturedAnswer]:
        """Create sample answers."""
        return [
            CapturedAnswer(
                question_index=0,
                question_text="Question 1?",
                answer_text="Answer 1",
                confidence=0.95,
            ),
            CapturedAnswer(
                question_index=1,
                question_text="Question 2?",
                answer_text="Answer 2",
                confidence=0.88,
            ),
            CapturedAnswer(
                question_index=2,
                question_text="Question 3?",
                answer_text="Answer 3",
                confidence=0.92,
            ),
        ]

    @pytest.mark.asyncio
    async def test_create_survey_response_success(
        self,
        repository: SurveyResponseRepository,
        mock_session: AsyncMock,
        sample_answers: list[CapturedAnswer],
    ) -> None:
        """Test successful survey response creation."""
        contact_id = uuid4()
        campaign_id = uuid4()
        call_attempt_id = uuid4()

        result = await repository.create_survey_response(
            session=mock_session,
            contact_id=contact_id,
            campaign_id=campaign_id,
            call_attempt_id=call_attempt_id,
            answers=sample_answers,
        )

        assert result is not None
        assert result.contact_id == contact_id
        assert result.campaign_id == campaign_id
        assert result.call_attempt_id == call_attempt_id
        assert result.q1_answer == "Answer 1"
        assert result.q2_answer == "Answer 2"
        assert result.q3_answer == "Answer 3"
        assert result.q1_confidence == 0.95
        assert result.q2_confidence == 0.88
        assert result.q3_confidence == 0.92
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_survey_response_wrong_answer_count(
        self,
        repository: SurveyResponseRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that wrong answer count raises ValueError."""
        answers = [
            CapturedAnswer(
                question_index=0,
                question_text="Q1?",
                answer_text="A1",
                confidence=0.9,
            ),
        ]

        with pytest.raises(ValueError, match="Expected 3 answers"):
            await repository.create_survey_response(
                session=mock_session,
                contact_id=uuid4(),
                campaign_id=uuid4(),
                call_attempt_id=uuid4(),
                answers=answers,
            )

    @pytest.mark.asyncio
    async def test_create_survey_response_sorts_answers(
        self,
        repository: SurveyResponseRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that answers are sorted by question index."""
        # Provide answers out of order
        answers = [
            CapturedAnswer(
                question_index=2,
                question_text="Q3?",
                answer_text="Third",
                confidence=0.7,
            ),
            CapturedAnswer(
                question_index=0,
                question_text="Q1?",
                answer_text="First",
                confidence=0.9,
            ),
            CapturedAnswer(
                question_index=1,
                question_text="Q2?",
                answer_text="Second",
                confidence=0.8,
            ),
        ]

        result = await repository.create_survey_response(
            session=mock_session,
            contact_id=uuid4(),
            campaign_id=uuid4(),
            call_attempt_id=uuid4(),
            answers=answers,
        )

        assert result.q1_answer == "First"
        assert result.q2_answer == "Second"
        assert result.q3_answer == "Third"

    @pytest.mark.asyncio
    async def test_get_by_contact_and_campaign_found(
        self,
        repository: SurveyResponseRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting existing survey response."""
        contact_id = uuid4()
        campaign_id = uuid4()
        expected_response = SurveyResponse(
            id=uuid4(),
            contact_id=contact_id,
            campaign_id=campaign_id,
            call_attempt_id=uuid4(),
            q1_answer="A1",
            q2_answer="A2",
            q3_answer="A3",
            completed_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_response
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_contact_and_campaign(
            session=mock_session,
            contact_id=contact_id,
            campaign_id=campaign_id,
        )

        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_by_contact_and_campaign_not_found(
        self,
        repository: SurveyResponseRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting non-existent survey response."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_contact_and_campaign(
            session=mock_session,
            contact_id=uuid4(),
            campaign_id=uuid4(),
        )

        assert result is None


class TestContactRepository:
    """Tests for ContactRepository."""

    @pytest.fixture
    def repository(self) -> ContactRepository:
        """Create repository instance."""
        return ContactRepository()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_update_state_with_outcome(
        self,
        repository: ContactRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating contact state with outcome."""
        contact_id = uuid4()

        await repository.update_state(
            session=mock_session,
            contact_id=contact_id,
            state=ContactState.COMPLETED,
            outcome=ContactOutcome.COMPLETED,
        )

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_state_without_outcome(
        self,
        repository: ContactRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating contact state without outcome."""
        contact_id = uuid4()

        await repository.update_state(
            session=mock_session,
            contact_id=contact_id,
            state=ContactState.IN_PROGRESS,
        )

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ContactRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting existing contact."""
        contact_id = uuid4()
        expected_contact = Contact(
            id=contact_id,
            campaign_id=uuid4(),
            phone_number="+14155551234",
            state="pending",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_contact
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(
            session=mock_session,
            contact_id=contact_id,
        )

        assert result == expected_contact


class TestCallAttemptRepository:
    """Tests for CallAttemptRepository."""

    @pytest.fixture
    def repository(self) -> CallAttemptRepository:
        """Create repository instance."""
        return CallAttemptRepository()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_update_outcome(
        self,
        repository: CallAttemptRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating call attempt outcome."""
        call_attempt_id = uuid4()
        ended_at = datetime.now(timezone.utc)

        await repository.update_outcome(
            session=mock_session,
            call_attempt_id=call_attempt_id,
            outcome="completed",
            ended_at=ended_at,
        )

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: CallAttemptRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting existing call attempt."""
        call_attempt_id = uuid4()
        expected_attempt = CallAttempt(
            id=call_attempt_id,
            contact_id=uuid4(),
            campaign_id=uuid4(),
            attempt_number=1,
            call_id="call-123",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_attempt
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(
            session=mock_session,
            call_attempt_id=call_attempt_id,
        )

        assert result == expected_attempt


class TestSurveyPersistenceService:
    """Tests for SurveyPersistenceService."""

    @pytest.fixture
    def mock_survey_repo(self) -> AsyncMock:
        """Create mock survey response repository."""
        repo = AsyncMock(spec=SurveyResponseRepository)
        return repo

    @pytest.fixture
    def mock_contact_repo(self) -> AsyncMock:
        """Create mock contact repository."""
        repo = AsyncMock(spec=ContactRepository)
        return repo

    @pytest.fixture
    def mock_call_attempt_repo(self) -> AsyncMock:
        """Create mock call attempt repository."""
        repo = AsyncMock(spec=CallAttemptRepository)
        return repo

    @pytest.fixture
    def service(
        self,
        mock_survey_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        mock_call_attempt_repo: AsyncMock,
    ) -> SurveyPersistenceService:
        """Create service instance with mocked repositories."""
        return SurveyPersistenceService(
            survey_response_repo=mock_survey_repo,
            contact_repo=mock_contact_repo,
            call_attempt_repo=mock_call_attempt_repo,
        )

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def completed_dialogue_session(self) -> DialogueSession:
        """Create a completed dialogue session with all answers."""
        session = DialogueSession(
            call_context=CallContext(
                call_id="call-123",
                campaign_id=uuid4(),
                contact_id=uuid4(),
                call_attempt_id=uuid4(),
                language="en",
                intro_script="Hello",
                questions=["Q1?", "Q2?", "Q3?"],
                question_types=["free_text", "numeric", "scale"],
            ),
            phase=DialoguePhase.COMPLETION,
            consent_state=ConsentState.GRANTED,
            state=DialogueSessionState.COMPLETED,
            answers=[
                CapturedAnswer(
                    question_index=0,
                    question_text="Q1?",
                    answer_text="Answer 1",
                    confidence=0.95,
                ),
                CapturedAnswer(
                    question_index=1,
                    question_text="Q2?",
                    answer_text="Answer 2",
                    confidence=0.88,
                ),
                CapturedAnswer(
                    question_index=2,
                    question_text="Q3?",
                    answer_text="Answer 3",
                    confidence=0.92,
                ),
            ],
        )
        return session

    @pytest.mark.asyncio
    async def test_persist_completed_survey_success(
        self,
        service: SurveyPersistenceService,
        mock_session: AsyncMock,
        mock_survey_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        mock_call_attempt_repo: AsyncMock,
        completed_dialogue_session: DialogueSession,
    ) -> None:
        """Test successful survey persistence."""
        survey_response_id = uuid4()
        completed_at = datetime.now(timezone.utc)

        # Setup mocks
        mock_contact_repo.get_by_id.return_value = Contact(
            id=completed_dialogue_session.call_context.contact_id,
            campaign_id=completed_dialogue_session.call_context.campaign_id,
            phone_number="+14155551234",
            state="in_progress",
        )
        mock_call_attempt_repo.get_by_id.return_value = CallAttempt(
            id=completed_dialogue_session.call_context.call_attempt_id,
            contact_id=completed_dialogue_session.call_context.contact_id,
            campaign_id=completed_dialogue_session.call_context.campaign_id,
            attempt_number=1,
            call_id="call-123",
        )
        mock_survey_repo.get_by_contact_and_campaign.return_value = None
        mock_survey_repo.create_survey_response.return_value = SurveyResponse(
            id=survey_response_id,
            contact_id=completed_dialogue_session.call_context.contact_id,
            campaign_id=completed_dialogue_session.call_context.campaign_id,
            call_attempt_id=completed_dialogue_session.call_context.call_attempt_id,
            q1_answer="Answer 1",
            q2_answer="Answer 2",
            q3_answer="Answer 3",
            completed_at=completed_at,
        )

        result = await service.persist_completed_survey(
            session=mock_session,
            dialogue_session=completed_dialogue_session,
        )

        assert result.success is True
        assert result.survey_response_id == survey_response_id
        assert result.contact_id == completed_dialogue_session.call_context.contact_id
        assert result.call_attempt_id == completed_dialogue_session.call_context.call_attempt_id

        # Verify all operations were called
        mock_contact_repo.get_by_id.assert_called_once()
        mock_call_attempt_repo.get_by_id.assert_called_once()
        mock_survey_repo.get_by_contact_and_campaign.assert_called_once()
        mock_survey_repo.create_survey_response.assert_called_once()
        mock_contact_repo.update_state.assert_called_once()
        mock_call_attempt_repo.update_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_completed_survey_no_call_context(
        self,
        service: SurveyPersistenceService,
        mock_session: AsyncMock,
    ) -> None:
        """Test persistence fails without call context."""
        session = DialogueSession()
        session.call_context = None

        result = await service.persist_completed_survey(
            session=mock_session,
            dialogue_session=session,
        )

        assert result.success is False
        assert "no call context" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_persist_completed_survey_missing_answers(
        self,
        service: SurveyPersistenceService,
        mock_session: AsyncMock,
    ) -> None:
        """Test persistence fails with missing answers."""
        session = DialogueSession(
            call_context=CallContext(
                call_id="call-123",
                campaign_id=uuid4(),
                contact_id=uuid4(),
                call_attempt_id=uuid4(),
            ),
            answers=[
                CapturedAnswer(
                    question_index=0,
                    question_text="Q1?",
                    answer_text="A1",
                    confidence=0.9,
                ),
            ],
        )

        result = await service.persist_completed_survey(
            session=mock_session,
            dialogue_session=session,
        )

        assert result.success is False
        assert "Expected 3 answers" in result.error_message

    @pytest.mark.asyncio
    async def test_persist_completed_survey_contact_not_found(
        self,
        service: SurveyPersistenceService,
        mock_session: AsyncMock,
        mock_contact_repo: AsyncMock,
        completed_dialogue_session: DialogueSession,
    ) -> None:
        """Test persistence fails when contact not found."""
        mock_contact_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="Contact not found"):
            await service.persist_completed_survey(
                session=mock_session,
                dialogue_session=completed_dialogue_session,
            )

    @pytest.mark.asyncio
    async def test_persist_completed_survey_call_attempt_not_found(
        self,
        service: SurveyPersistenceService,
        mock_session: AsyncMock,
        mock_contact_repo: AsyncMock,
        mock_call_attempt_repo: AsyncMock,
        completed_dialogue_session: DialogueSession,
    ) -> None:
        """Test persistence fails when call attempt not found."""
        mock_contact_repo.get_by_id.return_value = Contact(
            id=completed_dialogue_session.call_context.contact_id,
            campaign_id=completed_dialogue_session.call_context.campaign_id,
            phone_number="+14155551234",
            state="in_progress",
        )
        mock_call_attempt_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="CallAttempt not found"):
            await service.persist_completed_survey(
                session=mock_session,
                dialogue_session=completed_dialogue_session,
            )

    @pytest.mark.asyncio
    async def test_persist_completed_survey_idempotent(
        self,
        service: SurveyPersistenceService,
        mock_session: AsyncMock,
        mock_survey_repo: AsyncMock,
        mock_contact_repo: AsyncMock,
        mock_call_attempt_repo: AsyncMock,
        completed_dialogue_session: DialogueSession,
    ) -> None:
        """Test persistence is idempotent when response already exists."""
        existing_response_id = uuid4()
        completed_at = datetime.now(timezone.utc)

        mock_contact_repo.get_by_id.return_value = Contact(
            id=completed_dialogue_session.call_context.contact_id,
            campaign_id=completed_dialogue_session.call_context.campaign_id,
            phone_number="+14155551234",
            state="completed",
        )
        mock_call_attempt_repo.get_by_id.return_value = CallAttempt(
            id=completed_dialogue_session.call_context.call_attempt_id,
            contact_id=completed_dialogue_session.call_context.contact_id,
            campaign_id=completed_dialogue_session.call_context.campaign_id,
            attempt_number=1,
            call_id="call-123",
        )
        mock_survey_repo.get_by_contact_and_campaign.return_value = SurveyResponse(
            id=existing_response_id,
            contact_id=completed_dialogue_session.call_context.contact_id,
            campaign_id=completed_dialogue_session.call_context.campaign_id,
            call_attempt_id=completed_dialogue_session.call_context.call_attempt_id,
            q1_answer="A1",
            q2_answer="A2",
            q3_answer="A3",
            completed_at=completed_at,
        )

        result = await service.persist_completed_survey(
            session=mock_session,
            dialogue_session=completed_dialogue_session,
        )

        assert result.success is True
        assert result.survey_response_id == existing_response_id
        # Should not create new response
        mock_survey_repo.create_survey_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_persist_refused_survey_success(
        self,
        service: SurveyPersistenceService,
        mock_session: AsyncMock,
        mock_contact_repo: AsyncMock,
        mock_call_attempt_repo: AsyncMock,
    ) -> None:
        """Test successful refused survey persistence."""
        session = DialogueSession(
            call_context=CallContext(
                call_id="call-123",
                campaign_id=uuid4(),
                contact_id=uuid4(),
                call_attempt_id=uuid4(),
            ),
            state=DialogueSessionState.REFUSED,
            consent_state=ConsentState.REFUSED,
        )

        result = await service.persist_refused_survey(
            session=mock_session,
            dialogue_session=session,
        )

        assert result.success is True
        assert result.contact_id == session.call_context.contact_id
        assert result.call_attempt_id == session.call_context.call_attempt_id

        mock_contact_repo.update_state.assert_called_once()
        mock_call_attempt_repo.update_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_refused_survey_no_call_context(
        self,
        service: SurveyPersistenceService,
        mock_session: AsyncMock,
    ) -> None:
        """Test refused persistence fails without call context."""
        session = DialogueSession()
        session.call_context = None

        result = await service.persist_refused_survey(
            session=mock_session,
            dialogue_session=session,
        )

        assert result.success is False
        assert "no call context" in result.error_message.lower()


class TestDialogueSessionModel:
    """Tests for DialogueSession model."""

    def test_add_answer(self) -> None:
        """Test adding an answer to session."""
        session = DialogueSession()
        answer = CapturedAnswer(
            question_index=0,
            question_text="Q1?",
            answer_text="A1",
            confidence=0.9,
        )

        session.add_answer(answer)

        assert len(session.answers) == 1
        assert session.answers[0] == answer

    def test_get_answer_found(self) -> None:
        """Test getting existing answer."""
        session = DialogueSession()
        answer = CapturedAnswer(
            question_index=1,
            question_text="Q2?",
            answer_text="A2",
            confidence=0.85,
        )
        session.add_answer(answer)

        result = session.get_answer(1)

        assert result == answer

    def test_get_answer_not_found(self) -> None:
        """Test getting non-existent answer."""
        session = DialogueSession()

        result = session.get_answer(0)

        assert result is None

    def test_has_all_answers_true(self) -> None:
        """Test has_all_answers returns True with 3 answers."""
        session = DialogueSession()
        for i in range(3):
            session.add_answer(
                CapturedAnswer(
                    question_index=i,
                    question_text=f"Q{i+1}?",
                    answer_text=f"A{i+1}",
                    confidence=0.9,
                )
            )

        assert session.has_all_answers() is True

    def test_has_all_answers_false(self) -> None:
        """Test has_all_answers returns False with fewer than 3 answers."""
        session = DialogueSession()
        session.add_answer(
            CapturedAnswer(
                question_index=0,
                question_text="Q1?",
                answer_text="A1",
                confidence=0.9,
            )
        )

        assert session.has_all_answers() is False

    def test_mark_completed(self) -> None:
        """Test marking session as completed."""
        session = DialogueSession()

        session.mark_completed()

        assert session.state == DialogueSessionState.COMPLETED
        assert session.phase == DialoguePhase.COMPLETION

    def test_mark_refused(self) -> None:
        """Test marking session as refused."""
        session = DialogueSession()

        session.mark_refused()

        assert session.state == DialogueSessionState.REFUSED
        assert session.consent_state == ConsentState.REFUSED
        assert session.phase == DialoguePhase.TERMINATED

    def test_mark_failed(self) -> None:
        """Test marking session as failed."""
        session = DialogueSession()

        session.mark_failed()

        assert session.state == DialogueSessionState.FAILED
        assert session.phase == DialoguePhase.TERMINATED