# REQ-012: Dialogue Orchestrator Consent Flow

## Summary

This module implements the consent flow for voice survey calls. When a call is answered, it:

1. Plays the intro script (identity, purpose, duration)
2. Asks for explicit consent
3. Detects consent intent using LLM
4. Proceeds to questions or terminates based on response

## Quick Start

### Installation

bash
cd runs/kit/REQ-012
pip install -r requirements.txt

### Running Tests

bash
pytest -v test/

### Usage Example

python
from app.dialogue.integration import DialogueIntegration

# Create integration with your implementations
integration = DialogueIntegration(
    llm_gateway=your_llm_gateway,
    telephony_control=your_telephony,
    event_bus=your_event_bus,
)

# Handle call.answered event
session = await integration.on_call_answered(
    call_id="call-123",
    campaign_id=campaign_uuid,
    contact_id=contact_uuid,
    call_attempt_id=attempt_uuid,
    language="en",
    intro_script="Hello, this is Example Corp...",
    question_1_text="How satisfied are you?",
    question_1_type="scale",
    question_2_text="What could we improve?",
    question_2_type="free_text",
    question_3_text="Would you recommend us?",
    question_3_type="numeric",
)

# Handle user speech during consent phase
result = await integration.on_user_speech(
    call_id="call-123",
    transcript="yes, I agree",
    attempt_count=1,
)

# Check result
if result and result.intent == ConsentIntent.POSITIVE:
    # Proceed to Q&A flow (REQ-013)
    pass

## Module Structure

src/app/dialogue/
├── __init__.py          # Public exports
├── models.py            # Domain models (CallContext, DialogueSession)
├── consent.py           # ConsentDetector, ConsentFlowOrchestrator
├── events.py            # Event publishing
└── integration.py       # Integration layer

test/
├── test_consent_detector.py
├── test_consent_flow.py
├── test_dialogue_models.py
├── test_dialogue_events.py
└── test_dialogue_integration.py

## Key Classes

### ConsentDetector

Detects consent intent from user speech using LLM with keyword fallback.

### ConsentFlowOrchestrator

Manages the consent flow state machine and coordinates with telephony and events.

### DialogueIntegration

High-level integration layer connecting all components.

## Configuration

The module uses these environment variables:
- `LOG_LEVEL`: Logging level (default: INFO)

## Dependencies

- REQ-010: Telephony webhook handler
- REQ-011: LLM gateway integration