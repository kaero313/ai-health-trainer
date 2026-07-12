# RAG Retrieval Trace Privacy And Retention

## Purpose

Health coaching queries can contain goals, allergies, body measurements, exercise history, and a
user-authored question. Retrieval needs that text in memory, but operational evidence does not need
the original wording. This policy minimizes stored data while preserving correlation, fallback
diagnostics, evaluation, and incident response.

## Storage Boundary

The raw query is used only during the active retrieval call. New database rows enforce
`query_text IS NULL` and store:

- `query_hash`: HMAC-SHA256 fingerprint scoped by policy, key version, request type, and category
- `query_summary`: request type/category plus character and approximate term counts
- `query_policy_version`: `query-minimization-v1`
- `query_key_version`: operator-managed fingerprint key version
- `query_retention_until`: deletion eligibility time
- `query_redacted_at`: time the non-raw audit representation was produced

The same representation is used in `rag_pipeline_decisions`. OpenSearch/embedding fallback context
must never duplicate the raw query. `privacy-audit` checks both retrieval rows and decision JSON.
Chat `ai_recommendations.context_summary` stores only context type and "content not stored"; it does
not retain the user message.

Plain SHA-256 is not used for new rows because predictable short questions are vulnerable to
dictionary matching. `RAG_TRACE_HASH_KEY` provides the HMAC secret. When it is empty, development
falls back to a domain-separated JWT secret; production should configure a dedicated secret.

## Key Rotation

Set a new `RAG_TRACE_HASH_KEY` and increment `RAG_TRACE_HASH_KEY_VERSION` together. The key version is
part of the HMAC input, so rotation intentionally breaks cross-version correlation. Historical keys
are not required to serve requests and should not be stored in the application database.

## Legacy Redaction

Migration `e6f708192a3b` transforms every existing raw query into a legacy fingerprint and summary,
then sets `query_text` to `NULL`. This transformation is intentionally irreversible. Downgrade uses
a redacted placeholder and does not reconstruct the original query.

Migration `a8192a3b4c5d` removes legacy query copies from fallback decision JSON and chat context
summaries. Its downgrade is intentionally a no-op because deleted health text must not reappear.

The 2026-07-12 local migration redacted 84 existing rows. Post-migration audit result:

- total retrieval rows: 84
- raw query rows: 0
- missing fingerprint rows: 0

## Retention

Default retention is 90 days (`RAG_TRACE_RETENTION_DAYS`). Expired rows are removed in complete
`rag_trace_group_id` units so one retrieval event is never partially retained. The command is a
dry-run unless `--execute` is explicitly supplied and limits each batch by trace-group count.

```bash
python -m app.cli.ai privacy-audit
python -m app.cli.ai retrieval-retention --limit-groups 1000
python -m app.cli.ai retrieval-retention --limit-groups 1000 --execute
```

`privacy-audit` must report `raw_query_rows=0`, `missing_query_hash_rows=0`, and
`raw_decision_context_rows=0`, and `raw_chat_context_rows=0`. Retention execution
belongs in a scheduled operations worker after deployment; local development does not auto-delete
evidence.

## Tradeoffs

- Accepted: lose exact-query replay to reduce sensitive-data exposure.
- Accepted: key rotation breaks historical fingerprint correlation.
- Preserved: backend/mode, rank, score, source/chunk, category, latency, and response-use evidence.
- Preserved: deterministic correlation inside one key version and request scope.
- Rejected: encrypted raw-query storage. It retains breach value and creates key custody obligations
  without being necessary for current evaluation or incident response.
