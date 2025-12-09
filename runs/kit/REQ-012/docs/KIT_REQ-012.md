# KIT Documentation — REQ-012

## Dialogue Orchestrator Consent Flow

### Overview

REQ-012 implements the consent flow orchestration for the voice survey agent. This component handles the critical first phase of every survey call:

1. Playing the intro script immediately when a call is answered
2. Asking for explicit consent to participate
3. Processing the user's response using LLM-based intent detection
4. Proceeding to questions on positive consent
5. Terminating the call within 10 seconds on refusal
6. Publishing `survey.refused` events when consent is denied

### Architecture

┌─────────────────────────────────────────────────────────────────┐
│                    DialogueIntegration                          │
│  (Connects telephony, LLM, and event bus)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ConsentFlowOrchestrator                         │
│  - Manages dialogue sessions                                    │
│  - Handles call.answered events                                 │
│  - Processes user responses                                     │
│  - Coordinates termination on refusal                           │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ ConsentDetector │ │ TelephonyControl│ │ EventPublisher  │
│ (LLM-based)     │ │ (Protocol)      │ │ (Protocol)      │
└─────────────────┘ └─────────────────┘ └─────────────────┘

### Key Components

#### ConsentDetector

Uses LLM to detect consent intent from user responses:
- **POSITIVE**: User agrees to participate
- **NEGATIVE**: User refuses
- **UNCLEAR**: Cannot determine intent
- **REPEAT_REQUEST**: User asks to repeat

Includes fallback keyword matching for reliability.

#### ConsentFlowOrchestrator

Manages the consent flow state machine:
- Creates and tracks dialogue sessions
- Plays intro script and consent question
- Handles user responses based on detected intent
- Terminates calls on refusal
- Publishes events

#### DialogueSession

Tracks session state including:
- Current phase (intro, consent_request, question_1, etc.)
- Consent state (pending, granted, refused)
- Transcript of all utterances
- Timestamps for auditing

### Acceptance Criteria Mapping

| Criterion | Implementation |
|-----------|----------------|
| Intro script played immediately on call.answered | `ConsentFlowOrchestrator.handle_call_answered()` plays intro first |
| Consent question asked after intro | Consent question played immediately after intro |
| Positive consent proceeds to first question | `_handle_consent_granted()` sets phase to QUESTION_1 |
| Negative consent triggers call termination within 10 seconds | `_handle_consent_refused()` calls `terminate_call()` immediately |
| survey.refused event published on refusal | `_handle_consent_refused()` calls `event_publisher.publish_refused()` |

### Language Support

Both English and Italian are supported:
- Consent questions in both languages
- Refusal acknowledgments in both languages
- LLM prompt includes language context for detection

### Error Handling

- Empty/silent responses treated as UNCLEAR
- LLM errors fall back to keyword matching
- Maximum 2 unclear attempts before treating as refusal
- All errors logged with correlation IDs

### Dependencies

- **REQ-010**: Telephony webhook handler (provides call.answered events)
- **REQ-011**: LLM gateway integration (provides consent detection)

### Testing

Run tests with:
bash
cd runs/kit/REQ-012
pytest -v test/

Coverage includes:
- Consent detection with various intents
- Flow orchestration state transitions
- Event publishing
- Error handling
- Language support