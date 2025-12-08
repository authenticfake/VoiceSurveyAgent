# REQ-005 – Dialogue Outcome Handling

## What’s Included
- Telephony webhook endpoint (`/api/webhooks/telephony/events`).
- Dialogue payload schemas and processor for consent, answers, and retries.
- Survey event publisher persisting rows into the `events` table.
- SQLAlchemy session helper for API dependency injection.
- Unit tests validating completed, refused, and not-reached scenarios.

## Running Tests
```bash
pytest -q runs/kit/REQ-005/test
```

## Usage Notes
1. Ensure `DATABASE_URL` is set (e.g., `postgresql+psycopg://user:pass@host/db`).
2. Mount the router into the FastAPI application: `app.include_router(router)`.
3. Telephony providers must supply `campaign_id`, `contact_id`, and `call_id` (or `provider_call_id`) per event.
4. Survey events are currently stored in the DB; event bus integration will piggyback on the same publisher.

## Future Work
- Wire real messaging transport (REQ-006).
- Extend dialogue metadata to capture latency metrics and additional audit fields.
- Harden idempotency when providers retry webhook deliveries.