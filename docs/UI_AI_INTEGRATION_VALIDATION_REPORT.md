# UI / AI Integration Validation Report

> Run ID: `de86df0a-004c-406e-948b-b5b79b08fd9b`  
> Mode: `live_api`  
> Status: `succeeded`  
> Started: `2026-07-14T14:20:47.021431+00:00`  
> Finished: `2026-07-14T14:21:47.136481+00:00`

## Summary

| Metric | Value |
|---|---:|
| Expected checks | 14 |
| Passed | 14 |
| Failed | 0 |
| Skipped | 0 |
| Cleanup | `succeeded` |

## Check Results

| Check | Category | Status | HTTP | Latency | Error |
|---|---|---|---:|---:|---|
| `health` | setup | `passed` | 200 | 48ms | - |
| `account_auth` | setup | `passed` | 200 | 852ms | - |
| `profile_upsert` | api | `passed` | 200 | 68ms | - |
| `diet_create_read` | api | `passed` | 201 | 96ms | - |
| `exercise_create_read` | api | `passed` | 201 | 72ms | - |
| `dashboard_projection` | api | `passed` | 200 | 47ms | - |
| `diet_recommendation` | ai | `passed` | 200 | 15804ms | - |
| `exercise_recommendation` | ai | `passed` | 200 | 15834ms | - |
| `ai_chat` | ai | `passed` | 200 | 10529ms | - |
| `food_analysis_save` | ai | `passed` | 200 | 16185ms | - |
| `generation_trace_integrity` | trace | `passed` | - | 42ms | - |
| `retrieval_source_integrity` | trace | `passed` | - | 16ms | - |
| `privacy_invariants` | privacy | `passed` | - | 28ms | - |
| `cleanup` | cleanup | `passed` | - | 102ms | - |

## Evidence

- `health`: `{"database": "connected", "redis": "connected", "service_status": "ok"}`
- `account_auth`: `{"account_created": true, "login_verified": true}`
- `profile_upsert`: `{"profile_saved": true, "targets_calculated": true}`
- `diet_create_read`: `{"created_count": 1, "read_after_write": true}`
- `exercise_create_read`: `{"created_count": 1, "read_after_write": true, "set_count": 2}`
- `dashboard_projection`: `{"exercise_count": 1, "exercise_projected": true, "nutrition_projected": true}`
- `diet_recommendation`: `{"source_count": 2, "suggestion_count": 4}`
- `exercise_recommendation`: `{"source_count": 1, "suggestion_count": 3}`
- `ai_chat`: `{"answer_present": true, "source_count": 2}`
- `food_analysis_save`: `{"image_bytes": 401275, "recognized_count": 4, "selected_items_saved": 1}`
- `generation_trace_integrity`: `{"attempt_count": 4, "models": ["gemini-3-flash-preview"], "provider_latency_max_ms": 16065, "request_ids": ["7d111074-b375-480f-b47f-2fec4b3da66b", "96e10e0c-879d-4e5a-8f72-17fb4b404a5c", "65d787b5-ec3d-49b1-bdb8-42878f7f3d65", "8a76baa3-ab7d-4aca-95e6-3273b23cb3b1"], "request_types": ["chat", "diet", "exercise", "food_analysis"], "tokens_input_total": 3283, "tokens_output_total": 1375, "trace_count": 4}`
- `retrieval_source_integrity`: `{"prompt_rows": 9, "response_rows": 6, "retrieval_rows": 9, "search_backends": ["opensearch"], "source_count": 4, "trace_group_count": 3}`
- `privacy_invariants`: `{"invalid_hash_rows": 0, "query_key_versions": ["v1"], "query_policy_versions": ["query-minimization-v1"], "raw_chat_rows": 0, "raw_prompt_rows": 0, "raw_query_rows": 0, "recommendation_rows_checked": 3, "retrieval_rows_checked": 9}`
- `cleanup`: `{"api_delete_failures": 0, "database_rows_deleted": 7, "generation_traces_anonymized": true, "quota_keys_deleted": 5, "retrieval_traces_anonymized": true, "validation_user_removed": true}`

## Privacy And Cleanup Boundary

- Credentials, authorization tokens, prompts, user questions, provider responses, and food names are not stored.
- Validation diet, exercise, profile, token, recommendation, and user rows are removed after the run.
- Generation and retrieval traces remain only as anonymized operational evidence after their user foreign keys are cleared.
- Retrieval query text remains null; only keyed fingerprints and bounded summaries are retained.
