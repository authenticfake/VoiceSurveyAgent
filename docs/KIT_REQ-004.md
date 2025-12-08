# KIT — REQ-004 Call Scheduler & Telephony Adapter

## Scope
Implements the outbound call scheduler and an HTTP telephony provider adapter aligned with SPEC slice‑1.

## Highlights
- **SchedulerService** selects pending/not-reached contacts, enforces retry intervals, call windows, and provider concurrency limits.
- **Transactional state updates**: contact state, attempts, and CallAttempt rows are persisted atomically with telephony dispatch.
- **Telephony abstraction** with `TelephonyProvider` Protocol and a concrete `HttpTelephonyProvider` that POSTs to `/calls`.
- **Config-aware capacity**: uses `provider_configurations.max_concurrent_calls` and active call counts to throttle batches.
- **Deterministic seams**: injected clock, call-id factory, and provider enable repeatable tests.

## Tests
`pytest -q runs/kit/REQ-004/test`

## Assumptions
- Campaign allowed call windows are interpreted in a single configured timezone (injected via `SchedulerSettings`).
- Telephony provider exposes a REST endpoint returning `call_id` and `status`.
- Provider configuration table has at least one row; first row is authoritative.