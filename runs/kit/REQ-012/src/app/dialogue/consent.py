"""
Consent detection and flow orchestration.

REQ-012: Dialogue orchestrator consent flow
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from app.dialogue.models import (
    CallContext,
    ConsentState,
    DialoguePhase,
    DialogueSession,
    DialogueSessionState,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)

class ConsentIntent(str, Enum):
    """Detected consent intent from user response."""

    POSITIVE = "positive"  # User consents
    NEGATIVE = "negative"  # User refuses
    UNCLEAR = "unclear"  # Cannot determine intent
    REPEAT_REQUEST = "repeat_request"  # User asks to repeat

@dataclass
class ConsentResult:
    """Result of consent detection."""

    intent: ConsentIntent
    confidence: float
    raw_response: str
    reasoning: str | None = None

class LLMGatewayProtocol(Protocol):
    """Protocol for LLM gateway integration."""

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 150,
    ) -> str:
        """Generate chat completion.

        Args:
            messages: Conversation messages.
            system_prompt: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.

        Returns:
            Generated response text.
        """
        ...

class TelephonyControlProtocol(Protocol):
    """Protocol for telephony control operations."""

    async def play_text(self, call_id: str, text: str, language: str) -> None:
        """Play text-to-speech on the call.

        Args:
            call_id: Call identifier.
            text: Text to speak.
            language: Language code.
        """
        ...

    async def terminate_call(self, call_id: str, reason: str) -> None:
        """Terminate the call.

        Args:
            call_id: Call identifier.
            reason: Termination reason.
        """
        ...

class EventPublisherProtocol(Protocol):
    """Protocol for event publishing."""

    async def publish_refused(
        self,
        campaign_id: str,
        contact_id: str,
        call_id: str,
        attempt_count: int,
    ) -> None:
        """Publish survey.refused event.

        Args:
            campaign_id: Campaign identifier.
            contact_id: Contact identifier.
            call_id: Call identifier.
            attempt_count: Number of attempts.
        """
        ...

class ConsentDetector:
    """Detects consent intent from user responses using LLM."""

    # Consent detection system prompt
    CONSENT_SYSTEM_PROMPT = """You are a consent detection system for phone surveys.
Analyze the user's response to determine if they consent to participate in a brief survey.

Respond with EXACTLY one of these intents:
- POSITIVE: User clearly agrees/consents (e.g., "yes", "sure", "okay", "go ahead", "sì", "va bene")
- NEGATIVE: User clearly refuses (e.g., "no", "not interested", "no thanks", "non mi interessa")
- UNCLEAR: Cannot determine intent (mumbling, off-topic, silence)
- REPEAT_REQUEST: User asks to repeat the question (e.g., "what?", "can you repeat?", "come?")

Output format (JSON):
{"intent": "POSITIVE|NEGATIVE|UNCLEAR|REPEAT_REQUEST", "confidence": 0.0-1.0, "reasoning": "brief explanation"}

Be conservative: if unsure, use UNCLEAR. Consider cultural variations for Italian responses."""

    def __init__(self, llm_gateway: LLMGatewayProtocol) -> None:
        """Initialize consent detector.

        Args:
            llm_gateway: LLM gateway for intent detection.
        """
        self._llm = llm_gateway

    async def detect(
        self,
        user_response: str,
        language: str,
        context: str | None = None,
    ) -> ConsentResult:
        """Detect consent intent from user response.

        Args:
            user_response: User's spoken response.
            language: Language code ('en' or 'it').
            context: Optional additional context.

        Returns:
            ConsentResult with detected intent.
        """
        import json

        if not user_response or not user_response.strip():
            return ConsentResult(
                intent=ConsentIntent.UNCLEAR,
                confidence=1.0,
                raw_response=user_response,
                reasoning="Empty or silent response",
            )

        # Build prompt for LLM
        messages = [
            {
                "role": "user",
                "content": f"Language: {language}\nUser response: \"{user_response}\"\n\nDetect consent intent.",
            }
        ]

        try:
            response = await self._llm.chat_completion(
                messages=messages,
                system_prompt=self.CONSENT_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=100,
            )

            # Parse LLM response
            result = self._parse_llm_response(response, user_response)
            logger.info(
                "Consent detection completed",
                extra={
                    "intent": result.intent.value,
                    "confidence": result.confidence,
                    "language": language,
                },
            )
            return result

        except Exception as e:
            logger.error(f"Consent detection failed: {e}")
            # Default to unclear on error
            return ConsentResult(
                intent=ConsentIntent.UNCLEAR,
                confidence=0.5,
                raw_response=user_response,
                reasoning=f"Detection error: {str(e)}",
            )

    def _parse_llm_response(self, response: str, raw_response: str) -> ConsentResult:
        """Parse LLM response into ConsentResult.

        Args:
            response: LLM response text.
            raw_response: Original user response.

        Returns:
            Parsed ConsentResult.
        """
        import json

        try:
            # Try to parse as JSON
            data = json.loads(response)
            intent_str = data.get("intent", "UNCLEAR").upper()
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning")

            intent = ConsentIntent(intent_str.lower())

            return ConsentResult(
                intent=intent,
                confidence=min(max(confidence, 0.0), 1.0),
                raw_response=raw_response,
                reasoning=reasoning,
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            # Fallback: simple keyword matching
            return self._fallback_detection(raw_response)

    def _fallback_detection(self, response: str) -> ConsentResult:
        """Fallback consent detection using keywords.

        Args:
            response: User response text.

        Returns:
            ConsentResult from keyword matching.
        """
        response_lower = response.lower().strip()

        # Positive keywords (EN + IT)
        positive_keywords = [
            "yes", "yeah", "yep", "sure", "okay", "ok", "go ahead",
            "sì", "si", "certo", "va bene", "d'accordo", "procedi",
        ]

        # Negative keywords (EN + IT)
        negative_keywords = [
            "no", "nope", "not interested", "no thanks", "don't want",
            "non", "no grazie", "non mi interessa", "non voglio",
        ]

        # Repeat request keywords
        repeat_keywords = [
            "what", "repeat", "again", "sorry", "pardon",
            "come", "ripeti", "scusa", "non ho capito",
        ]

        for kw in positive_keywords:
            if kw in response_lower:
                return ConsentResult(
                    intent=ConsentIntent.POSITIVE,
                    confidence=0.7,
                    raw_response=response,
                    reasoning="Keyword match (fallback)",
                )

        for kw in negative_keywords:
            if kw in response_lower:
                return ConsentResult(
                    intent=ConsentIntent.NEGATIVE,
                    confidence=0.7,
                    raw_response=response,
                    reasoning="Keyword match (fallback)",
                )

        for kw in repeat_keywords:
            if kw in response_lower:
                return ConsentResult(
                    intent=ConsentIntent.REPEAT_REQUEST,
                    confidence=0.6,
                    raw_response=response,
                    reasoning="Keyword match (fallback)",
                )

        return ConsentResult(
            intent=ConsentIntent.UNCLEAR,
            confidence=0.5,
            raw_response=response,
            reasoning="No clear intent detected (fallback)",
        )

class ConsentFlowOrchestrator:
    """Orchestrates the consent flow for survey calls.

    Handles:
    - Playing intro script on call.answered
    - Asking consent question
    - Processing consent response
    - Terminating call on refusal within 10 seconds
    - Publishing survey.refused event
    """

    # Consent question templates
    CONSENT_QUESTIONS = {
        "en": "Do you consent to participate in this brief survey?",
        "it": "Acconsente a partecipare a questo breve sondaggio?",
    }

    # Refusal acknowledgment templates
    REFUSAL_MESSAGES = {
        "en": "Thank you for your time. We respect your decision. Goodbye.",
        "it": "Grazie per il suo tempo. Rispettiamo la sua decisione. Arrivederci.",
    }

    # Proceed messages
    PROCEED_MESSAGES = {
        "en": "Thank you for agreeing to participate. Let's begin with the first question.",
        "it": "Grazie per aver accettato di partecipare. Iniziamo con la prima domanda.",
    }

    # Repeat messages
    REPEAT_MESSAGES = {
        "en": "I'll repeat that for you.",
        "it": "Ripeto per lei.",
    }

    # Unclear response messages
    UNCLEAR_MESSAGES = {
        "en": "I'm sorry, I didn't quite catch that. Do you consent to participate? Please say yes or no.",
        "it": "Mi scusi, non ho capito bene. Acconsente a partecipare? Per favore risponda sì o no.",
    }

    # Maximum unclear attempts before termination
    MAX_UNCLEAR_ATTEMPTS = 2

    def __init__(
        self,
        consent_detector: ConsentDetector,
        telephony_control: TelephonyControlProtocol,
        event_publisher: EventPublisherProtocol,
    ) -> None:
        """Initialize consent flow orchestrator.

        Args:
            consent_detector: Consent detection service.
            telephony_control: Telephony control interface.
            event_publisher: Event publishing interface.
        """
        self._detector = consent_detector
        self._telephony = telephony_control
        self._events = event_publisher
        self._sessions: dict[str, DialogueSession] = {}
        self._unclear_counts: dict[str, int] = {}

    async def handle_call_answered(
        self,
        call_context: CallContext,
    ) -> DialogueSession:
        """Handle call.answered event - start consent flow.

        Plays intro script immediately and asks for consent.

        Args:
            call_context: Context for the call.

        Returns:
            Created dialogue session.
        """
        logger.info(
            "Call answered, starting consent flow",
            extra={
                "call_id": call_context.call_id,
                "campaign_id": str(call_context.campaign_id),
                "contact_id": str(call_context.contact_id),
            },
        )

        # Create session
        session = DialogueSession(call_context=call_context)
        self._sessions[call_context.call_id] = session
        self._unclear_counts[call_context.call_id] = 0

        # Play intro script
        await self._telephony.play_text(
            call_id=call_context.call_id,
            text=call_context.intro_script,
            language=call_context.language,
        )
        session.add_utterance("agent", call_context.intro_script)

        # Transition to consent request phase
        session.phase = DialoguePhase.CONSENT_REQUEST
        session.consent_requested_at = datetime.now(timezone.utc)

        # Ask consent question
        consent_question = self.CONSENT_QUESTIONS.get(
            call_context.language, self.CONSENT_QUESTIONS["en"]
        )
        await self._telephony.play_text(
            call_id=call_context.call_id,
            text=consent_question,
            language=call_context.language,
        )
        session.add_utterance("agent", consent_question)

        logger.info(
            "Consent question asked",
            extra={"call_id": call_context.call_id, "phase": session.phase.value},
        )

        return session

    async def handle_user_response(
        self,
        call_id: str,
        user_response: str,
        attempt_count: int = 1,
    ) -> ConsentResult:
        """Handle user response during consent phase.

        Args:
            call_id: Call identifier.
            user_response: User's spoken response.
            attempt_count: Current attempt count for the contact.

        Returns:
            ConsentResult with detected intent and actions taken.

        Raises:
            ValueError: If session not found or not in consent phase.
        """
        session = self._sessions.get(call_id)
        if not session:
            raise ValueError(f"No session found for call_id: {call_id}")

        if session.phase not in (
            DialoguePhase.CONSENT_REQUEST,
            DialoguePhase.CONSENT_PROCESSING,
        ):
            raise ValueError(f"Session not in consent phase: {session.phase}")

        if not session.call_context:
            raise ValueError("Session missing call context")

        session.phase = DialoguePhase.CONSENT_PROCESSING
        session.add_utterance("user", user_response)

        # Detect consent intent
        result = await self._detector.detect(
            user_response=user_response,
            language=session.call_context.language,
        )

        logger.info(
            "Consent response processed",
            extra={
                "call_id": call_id,
                "intent": result.intent.value,
                "confidence": result.confidence,
            },
        )

        # Handle based on intent
        if result.intent == ConsentIntent.POSITIVE:
            await self._handle_consent_granted(session)
        elif result.intent == ConsentIntent.NEGATIVE:
            await self._handle_consent_refused(session, attempt_count)
        elif result.intent == ConsentIntent.REPEAT_REQUEST:
            await self._handle_repeat_request(session)
        else:  # UNCLEAR
            await self._handle_unclear_response(session, attempt_count)

        return result

    async def _handle_consent_granted(self, session: DialogueSession) -> None:
        """Handle positive consent.

        Args:
            session: Dialogue session.
        """
        if not session.call_context:
            return

        session.set_consent_granted()

        # Play proceed message
        proceed_msg = self.PROCEED_MESSAGES.get(
            session.call_context.language, self.PROCEED_MESSAGES["en"]
        )
        await self._telephony.play_text(
            call_id=session.call_context.call_id,
            text=proceed_msg,
            language=session.call_context.language,
        )
        session.add_utterance("agent", proceed_msg)

        logger.info(
            "Consent granted, proceeding to questions",
            extra={"call_id": session.call_context.call_id},
        )

    async def _handle_consent_refused(
        self,
        session: DialogueSession,
        attempt_count: int,
    ) -> None:
        """Handle negative consent - terminate call within 10 seconds.

        Args:
            session: Dialogue session.
            attempt_count: Current attempt count.
        """
        if not session.call_context:
            return

        session.set_consent_refused()

        # Play refusal acknowledgment
        refusal_msg = self.REFUSAL_MESSAGES.get(
            session.call_context.language, self.REFUSAL_MESSAGES["en"]
        )
        await self._telephony.play_text(
            call_id=session.call_context.call_id,
            text=refusal_msg,
            language=session.call_context.language,
        )
        session.add_utterance("agent", refusal_msg)

        # Terminate call
        await self._telephony.terminate_call(
            call_id=session.call_context.call_id,
            reason="consent_refused",
        )

        # Publish survey.refused event
        await self._events.publish_refused(
            campaign_id=str(session.call_context.campaign_id),
            contact_id=str(session.call_context.contact_id),
            call_id=session.call_context.call_id,
            attempt_count=attempt_count,
        )

        logger.info(
            "Consent refused, call terminated, event published",
            extra={
                "call_id": session.call_context.call_id,
                "campaign_id": str(session.call_context.campaign_id),
            },
        )

    async def _handle_repeat_request(self, session: DialogueSession) -> None:
        """Handle repeat request.

        Args:
            session: Dialogue session.
        """
        if not session.call_context:
            return

        # Play repeat message
        repeat_msg = self.REPEAT_MESSAGES.get(
            session.call_context.language, self.REPEAT_MESSAGES["en"]
        )
        await self._telephony.play_text(
            call_id=session.call_context.call_id,
            text=repeat_msg,
            language=session.call_context.language,
        )
        session.add_utterance("agent", repeat_msg)

        # Repeat intro and consent question
        await self._telephony.play_text(
            call_id=session.call_context.call_id,
            text=session.call_context.intro_script,
            language=session.call_context.language,
        )
        session.add_utterance("agent", session.call_context.intro_script)

        consent_question = self.CONSENT_QUESTIONS.get(
            session.call_context.language, self.CONSENT_QUESTIONS["en"]
        )
        await self._telephony.play_text(
            call_id=session.call_context.call_id,
            text=consent_question,
            language=session.call_context.language,
        )
        session.add_utterance("agent", consent_question)

        # Stay in consent request phase
        session.phase = DialoguePhase.CONSENT_REQUEST

    async def _handle_unclear_response(
        self,
        session: DialogueSession,
        attempt_count: int,
    ) -> None:
        """Handle unclear response.

        Args:
            session: Dialogue session.
            attempt_count: Current attempt count.
        """
        if not session.call_context:
            return

        call_id = session.call_context.call_id
        self._unclear_counts[call_id] = self._unclear_counts.get(call_id, 0) + 1

        if self._unclear_counts[call_id] >= self.MAX_UNCLEAR_ATTEMPTS:
            # Too many unclear responses, treat as refusal
            logger.info(
                "Max unclear attempts reached, treating as refusal",
                extra={"call_id": call_id, "attempts": self._unclear_counts[call_id]},
            )
            await self._handle_consent_refused(session, attempt_count)
            return

        # Ask for clarification
        unclear_msg = self.UNCLEAR_MESSAGES.get(
            session.call_context.language, self.UNCLEAR_MESSAGES["en"]
        )
        await self._telephony.play_text(
            call_id=call_id,
            text=unclear_msg,
            language=session.call_context.language,
        )
        session.add_utterance("agent", unclear_msg)

        # Stay in consent request phase
        session.phase = DialoguePhase.CONSENT_REQUEST

    def get_session(self, call_id: str) -> DialogueSession | None:
        """Get dialogue session by call ID.

        Args:
            call_id: Call identifier.

        Returns:
            DialogueSession if found, None otherwise.
        """
        return self._sessions.get(call_id)

    def remove_session(self, call_id: str) -> None:
        """Remove dialogue session.

        Args:
            call_id: Call identifier.
        """
        self._sessions.pop(call_id, None)
        self._unclear_counts.pop(call_id, None)