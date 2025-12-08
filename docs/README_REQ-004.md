# REQ-004 — Call Scheduler & Telephony Adapter

## Overview
This module introduces the outbound scheduler responsible for selecting eligible contacts and starting calls via a pluggable telephony provider adapter.

### Key Components
- `SchedulerService`: main orchestration entrypoint.
- `SchedulerSettings`: per-run configuration (batch size, callback URL, timezone).
- `TelephonyProvider` protocol + `HttpTelephonyProvider` implementation.
- `OutboundCallRequest/Response`, `QuestionPrompt` dataclasses.

### Behavior
1. Load provider configuration & determine available capacity.
2. Prefetch eligible contact snapshots.
3. For each candidate:
   - enforce time windows and retry intervals,
   - lock the contact row (`FOR UPDATE SKIP LOCKED`),
   - call the telephony provider,
   - update the contact + insert `CallAttempt`.

Errors in telephony dispatch only impact the specific contact; other candidates continue.

### Running Tests
```
pytest -q runs/kit/REQ-004/test
```

### Future Extensions
- Plug Redis-based distributed locks (interface seam already provided).
- Add per-campaign concurrency throttles.
- Enrich telephony adapter with retries/backoff and provider-specific metrics.