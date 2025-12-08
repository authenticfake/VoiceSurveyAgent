# KIT Report – REQ-005 (Dialogue outcome handling and survey responses)

## Scope
- Implemented telephony webhook ingestion endpoint.
- Added dialogue models, processor, and event publisher to persist outcomes.
- Introduced DB session helper for dependency injection.
- Persisted survey answers, consent refusals, and not-reached decisions with event emission.

## Key Components
| Component | Description |
| --- | --- |
| `app/calling/dialogue/models.py` | Pydantic payload schemas for telephony events. |
| `app/calling/dialogue/processor.py` | Core orchestration that mutates CallAttempt, Contact, SurveyResponse, and Events. |
| `app/api/http/telephony_webhooks/router.py` | FastAPI router for `/api/webhooks/telephony/events`. |
| `app/events/bus/publisher.py` | Survey event publisher that stores event rows. |
| `app/infra/db/session.py` | Session factory and FastAPI dependency for shared DB access. |

## Testing
- `pytest -q runs/kit/REQ-005/test` – unit tests covering completion, refusal, and not-reached flows.

## Assumptions / Notes
- Provider sends exactly three answers upon successful consent; processor validates this invariant.
- Event publishing currently persists to DB; downstream queue integration will extend this contract in REQ-006.
- Router always returns 202 to telephony provider; missing call attempts are logged and ignored.