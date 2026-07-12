# AI Request Lifecycle

## Purpose

AI Health Trainer treats an AI request and a provider call as different operational units.
One API request can perform retrieval, one initial Gemini call, a transient provider retry,
and one schema repair. Aggregating those events into one row hides cost, latency, and failure
boundaries, so the lifecycle uses a parent request trace and child provider attempts.

## State Model

`ai_generation_traces` is the request-level source of truth.

- `started`: accepted and persisted before retrieval or provider invocation
- `succeeded`: a schema-valid response and its business record were persisted
- `failed`: provider, schema, persistence, or infrastructure failure
- `blocked`: safety or policy rejection
- `skipped`: no provider invocation, such as RAG fail-closed or quota rejection
- `abandoned`: a stale `started` request reconciled after process interruption

`ai_generation_attempts` records every Gemini invocation.

- `initial`: first provider call
- `provider_retry`: retry after a transient provider failure or timeout
- `schema_repair`: one validation-aware repair call

Each attempt stores its own status, model, latency, tokens, finish reason, provider response ID,
response integrity hash, and sanitized error stage. Raw prompts and raw responses are not stored.

## Transaction Boundaries

1. The parent `started` row is committed before retrieval or provider invocation.
2. A Redis quota slot is atomically reserved against the parent `request_id` before retrieval.
3. On the first provider attempt the reservation becomes `consumed`; retries and schema repair
   reuse that reservation and never increment the user quota again.
4. An attempt `started` row is committed immediately before calling Gemini.
5. The attempt is completed after the provider returns or fails.
6. Recommendation/chat business data and the parent terminal status are committed together.
7. Food analysis has no business row until the user explicitly saves selected foods, so its
   parent trace is completed before the analysis response is returned.

This leaves durable evidence when the process stops between provider invocation and response
persistence. `reconcile-stale` converts old `started` requests and attempts to `abandoned`.

## Atomic Daily Quota

The product quota and provider cost are separate measurements.

- Product quota: one accepted logical request, identified by the parent `request_id`.
- Provider cost: every child attempt, including provider retry and schema repair.
- Default limit: 30 logical requests per user and local quota day.
- Default quota timezone: `Asia/Seoul`.
- Storage: Redis Lua scripts provide atomic reserve/consume/release transitions.
- Failure policy: fail closed. Redis uncertainty prevents a provider call.

The parent trace records `quota_status`, `quota_bucket`, timezone, configured limit, admitted
position, and reservation/finalization timestamps. The state model is:

- `not_checked`: legacy row or admission not yet attempted
- `reserved`: accepted, but no provider attempt has started
- `consumed`: at least one provider attempt was admitted
- `released`: request ended before provider invocation or stale reservation was reconciled
- `rejected`: daily limit was already exhausted
- `error`: quota storage or persistence was unavailable

Redis keys use a shared cluster hash tag per `user_id + local date`, so the counter and request
reservation remain in the same hash slot. A request ID is idempotent: repeating reserve or consume
does not increment the counter. Keys expire after the local-day reset plus a one-day reconciliation
grace period.

Redis and PostgreSQL cannot participate in one native transaction. The implementation therefore
uses conservative ordering: reserve Redis first, persist the DB audit before retrieval, consume
Redis before committing the provider attempt, and never call Gemini if settlement is uncertain.
This can temporarily over-count after an ambiguous DB commit, but cannot under-count and call the
provider without admission evidence. Reconciliation releases only unconsumed stale reservations.

## Retry And Deadline Policy

- request deadline: 60 seconds
- provider timeout: 30 seconds per attempt
- transient provider retry: at most one
- schema repair: at most one
- unknown source references: schema failure and one repair opportunity
- no trusted RAG context: fail closed without provider invocation

The values are configured through `AI_REQUEST_DEADLINE_SECONDS`,
`AI_PROVIDER_TIMEOUT_SECONDS`, `AI_MAX_PROVIDER_RETRIES`, and
`AI_MAX_SCHEMA_REPAIRS`. Quota behavior is configured through
`AI_DAILY_REQUEST_LIMIT`, `AI_QUOTA_TIMEZONE`, `AI_QUOTA_KEY_PREFIX`, and
`AI_QUOTA_KEY_GRACE_SECONDS`.

## Operations

```bash
python -m app.cli.ai trace --request-id <uuid>
python -m app.cli.ai reconcile-stale --stale-minutes 5
python -m app.cli.ai privacy-audit
python -m app.cli.ai retrieval-retention --limit-groups 1000
```

The trace command prints the request lifecycle, quota decision, and ordered provider attempts
without exposing prompt or response bodies.

## Verified Evidence

On 2026-07-12, a live `chat_v2` request produced one parent request and one child attempt:

- parent: `succeeded`, `provider_invoked=true`, completed before its deadline
- attempt: `initial`, `succeeded`, 24,725ms
- usage: 562 input tokens and 330 output tokens
- retrieval: OpenSearch hybrid with three verified public source titles

Atomic quota verification on the same date used real Redis Lua execution:

- 50 concurrent reservations against a limit of 10 produced exactly 10 admits and 40 rejects
- repeat reserve/consume for one request ID kept the counter at one
- pre-provider termination and stale reconciliation released the reservation
- KST midnight created a new independent daily bucket
- Redis failure and malformed state both failed closed without provider invocation

## Remaining Hardening

- generate integration reports from a validation run ID rather than manually asserted PASS rows
- add a scheduled invocation of `reconcile-stale` in the production worker environment
- add per-user IANA timezone preferences if the product expands beyond the current Korea-first policy
