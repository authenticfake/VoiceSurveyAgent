"""
Integration layer connecting dialogue orchestration with telephony and LLM.

REQ-012: Dialogue orchestrator consent flow
"""

from typing import Any
from uuid import UUID

from app.dialogue.consent import (
    ConsentDetector,
    ConsentFlowOrchestrator,
    ConsentResult,
    EventPublisherProtocol,
    LLMGatewayProtocol,
    TelephonyControlProtocol,
)
from app.dialogue.events import DialogueEventPublisher, EventBusProtocol
from app.dialogue.models import CallContext, DialogueSession
from app.shared.logging import get_logger

logger = get_logger(__name__)

class DialogueIntegration:
    """Integration layer for dialogue orchestration.

    Connects the consent flow orchestrator with:
    - Telephony provider (REQ-009, REQ-010)
    - LLM gateway (REQ-011)
    - Event bus (REQ-015)
    """

    def __init__(
        self,
        llm_gateway: LLMGatewayProtocol,
        telephony_control: TelephonyControlProtocol,
        event_bus: EventBusProtocol,
    ) -> None:
        """Initialize dialogue integration.

        Args:
            llm_gateway: LLM gateway for consent detection.
            telephony_control: Telephony control interface.
            event_bus: Event bus for publishing events.
        """
        self._llm = llm_gateway
        self._telephony = telephony_control

        # Create event publisher
        self._event_publisher = DialogueEventPublisher(event_bus)

        # Create consent detector
        self._consent_detector = ConsentDetector(llm_gateway)

        # Create consent flow orchestrator
        self._orchestrator = ConsentFlowOrchestrator(
            consent_detector=self._consent_detector,
            telephony_control=telephony_control,
            event_publisher=self._event_publisher,
        )

    async def on_call_answered(
        self,
        call_id: str,
        campaign_id: UUID,
        contact_id: UUID,
        call_attempt_id: UUID,
        language: str,
        intro_script: str,
        question_1_text: str,
        question_1_type: str,
        question_2_text: str,
        question_2_type: str,
        question_3_text: str,
        question_3_type: str,
        correlation_id: str | None = None,
    ) -> DialogueSession:
        """Handle call.answered event.

        Args:
            call_id: Call identifier.
            campaign_id: Campaign UUID.
            contact_id: Contact UUID.
            call_attempt_id: Call attempt UUID.
            language: Language code ('en' or 'it').
            intro_script: Intro script text.
            question_1_text: First question text.
            question_1_type: First question type.
            question_2_text: Second question text.
            question_2_type: Second question type.
            question_3_text: Third question text.
            question_3_type: Third question type.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            Created dialogue session.
        """
        context = CallContext(
            call_id=call_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            call_attempt_id=call_attempt_id,
            language=language,
            intro_script=intro_script,
            question_1_text=question_1_text,
            question_1_type=question_1_type,
            question_2_text=question_2_text,
            question_2_type=question_2_type,
            question_3_text=question_3_text,
            question_3_type=question_3_type,
            correlation_id=correlation_id,
        )

        logger.info(
            "Processing call.answered event",
            extra={
                "call_id": call_id,
                "campaign_id": str(campaign_id),
                "correlation_id": correlation_id,
            },
        )

        return await self._orchestrator.handle_call_answered(context)

    async def on_user_speech(
        self,
        call_id: str,
        transcript: str,
        attempt_count: int = 1,
    ) -> ConsentResult | None:
        """Handle user speech during consent phase.

        Args:
            call_id: Call identifier.
            transcript: Transcribed user speech.
            attempt_count: Current attempt count.

        Returns:
            ConsentResult if in consent phase, None otherwise.
        """
        session = self._orchestrator.get_session(call_id)
        if not session:
            logger.warning(f"No session found for call_id: {call_id}")
            return None

        # Only handle during consent phase
        from app.dialogue.models import DialoguePhase

        if session.phase not in (
            DialoguePhase.CONSENT_REQUEST,
            DialoguePhase.CONSENT_PROCESSING,
        ):
            logger.debug(
                f"Session not in consent phase: {session.phase}",
                extra={"call_id": call_id},
            )
            return None

        return await self._orchestrator.handle_user_response(
            call_id=call_id,
            user_response=transcript,
            attempt_count=attempt_count,
        )

    def get_session(self, call_id: str) -> DialogueSession | None:
        """Get dialogue session by call ID.

        Args:
            call_id: Call identifier.

        Returns:
            DialogueSession if found.
        """
        return self._orchestrator.get_session(call_id)

    def cleanup_session(self, call_id: str) -> None:
        """Clean up session after call ends.

        Args:
            call_id: Call identifier.
        """
        self._orchestrator.remove_session(call_id)