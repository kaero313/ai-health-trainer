# RAG v1 운영 검증 리포트

> 이 문서는 `python -m app.cli.rag validate-v1` 명령으로 재생성 가능한 운영 검증 리포트다.

## Reproduce

```bash
docker compose exec backend python -m app.cli.rag validate-v1 --report-path /workspace/docs/RAG_EVALUATION_REPORT.md
```

## Coverage

- Markdown seed corpus ingest 이후의 운영 DB와 OpenSearch index 상태를 검증한다.
- Retrieval evaluation, source grade hit, safety source hit, fallback count를 기록한다.
- Skip/partial/full refresh decision trace는 `rag_pipeline_decisions`와 recent job metrics로 확인한다.
- Text/PDF parser capability는 backend tests에서 file path 기반 fixture로 검증한다.

## Summary

- total_cases: 5
- passed: 5
- failed: 0
- pass_rate: 100.00%
- fallback_count: 0
- safety_source_hit_count: 1
- source_grade_hit_count: 5

## OpenSearch Index

| Field | Value |
|-------|-------|
| `index` | rag_chunks_v1 |
| `alias` | rag_chunks_current |
| `exists` | True |
| `alias_exists` | True |
| `health` | yellow |
| `status` | open |
| `docs_count` | 321 |
| `docs_deleted` | 0 |
| `store_size` | 39.6mb |
| `primary_store_size` | 39.6mb |

## DB Counts

| Metric | Count |
|--------|-------|
| `rag_catalog_plan_items` | 42 |
| `rag_catalog_plan_runs` | 7 |
| `rag_chunks` | 531 |
| `rag_chunks_active` | 279 |
| `rag_embedding_cache` | 337 |
| `rag_ingest_jobs` | 36 |
| `rag_pipeline_decisions` | 36 |
| `rag_sources` | 23 |

## Source Acquisition Summary

| Metric | Count |
|--------|-------|
| `catalog_local_file_source_count` | 5 |
| `catalog_source_count` | 3 |
| `etag_present_count` | 1 |
| `html_parser_source_count` | 3 |
| `last_modified_present_count` | 2 |
| `local_file_fingerprint_count` | 5 |
| `local_file_source_count` | 20 |
| `markdown_parser_source_count` | 18 |
| `pdf_text_parser_source_count` | 1 |
| `scheduled_refresh_count` | 3 |
| `source_grade_a_count` | 4 |
| `stale_source_count` | 0 |
| `text_parser_source_count` | 1 |
| `url_source_count` | 3 |

## Latest Catalog Plan

| Field | Value |
|-------|-------|
| `id` | 7 |
| `status` | succeeded |
| `total_sources` | 5 |
| `planned_create_count` | 0 |
| `planned_skip_count` | 5 |
| `planned_partial_count` | 0 |
| `planned_full_count` | 0 |
| `planned_manual_count` | 0 |
| `planned_defer_count` | 0 |
| `created_at` | 2026-05-05T14:08:05.655963+00:00 |

## Decision Summary

| Action | Reason | Count |
|--------|--------|-------|
| `create_source` | `NEW_SOURCE` | 23 |
| `full_reindex` | `LARGE_OR_STRUCTURAL_CHANGE` | 7 |
| `manual_review_required` | `LOW_PARSER_CONFIDENCE` | 1 |
| `partial_refresh` | `SMALL_CONTENT_CHANGE` | 1 |
| `skip_refresh` | `SOURCE_HASH_UNCHANGED` | 4 |

## Recent Jobs

| Job | Type | Source | Status | Stage | Change Ratio | Reuse | Reembed | Index Skip |
|-----|------|--------|--------|-------|--------------|-------|---------|------------|
| 37 | create | 24 | succeeded | finished | 1.0000 | 0 | 1 | 0 |
| 36 | create | 23 | succeeded | finished | 1.0000 | 0 | 4 | 0 |
| 35 | create | 22 | succeeded | finished | 1.0000 | 5 | 0 | 0 |
| 34 | create | 21 | succeeded | finished | 1.0000 | 8 | 0 | 0 |
| 33 | create | 20 | succeeded | finished | 1.0000 | 7 | 0 | 0 |
| 32 | refresh | 19 | succeeded | finished | 0.0000 | 149 | 0 | 0 |
| 31 | refresh | 18 | succeeded | finished | 0.0000 | 4 | 0 | 0 |
| 30 | refresh | 17 | succeeded | finished | 0.0000 | 16 | 0 | 0 |
| 29 | refresh | 19 | skipped | skip_refresh | 0.0000 | 0 | 0 | 0 |
| 28 | refresh | 18 | succeeded | finished | 0.8889 | 1 | 3 | 0 |

## Retrieval Cases

| Query | Passed | Category | Tag | Source | Fallback | Top Titles |
|-------|--------|----------|-----|--------|----------|------------|
| 다이어트 중 단백질이 부족할 때 한국 식단에서 무엇을 추가하면 좋을까? | True | True | True | True | False | 단백질이 부족한 날의 원칙 (1/5), 다이어트 중 단백질 보충 (2/5), 추천 표현 기준 (5/5) |
| 벤치프레스 중량은 언제 올리고 반복수는 어떻게 조절해야 할까? | True | True | True | True | False | 증량 기준 (6/8), 가슴 (1/5), 증량 기준 (6/8) |
| 스쿼트할 때 무릎 통증이 있으면 운동 추천을 어떻게 제한해야 할까? | True | True | True | True | False | 무릎 통증 시 보수적 대응 (3/5), 무릎 통증 시 보수적 대응 (3/5), 허리 통증 시 보수적 대응 (5/5) |
| 벌크업과 다이어트와 유지를 목표별로 어떻게 다르게 운영해야 할까? | True | True | True | True | False | 벌크업 (1/5), 매크로 비율 (2/4), 유지 (3/5) |
| 가슴, 등, 하체 운동을 주요 근육군 기준으로 설명해줘 | True | True | True | True | False | 하체 (4/5), 가슴 (1/5), 등 (2/5) |

## V1 Verdict

- Markdown seed corpus ingest, OpenSearch retrieval, decision trace, evaluation report 재생성을 검증한다.
- Text/PDF parser capability는 backend tests에서 file path 기반 fixture로 검증한다.
- OpenSearch 장애 fallback은 automated test와 policy trace 기준으로 검증한다.
