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
| `docs_count` | 296 |
| `docs_deleted` | 144 |
| `store_size` | 24.2mb |
| `primary_store_size` | 24.2mb |

## DB Counts

| Metric | Count |
|--------|-------|
| `rag_chunks` | 337 |
| `rag_chunks_active` | 254 |
| `rag_embedding_cache` | 332 |
| `rag_ingest_jobs` | 28 |
| `rag_pipeline_decisions` | 28 |
| `rag_sources` | 18 |

## URL Source Summary

| Metric | Count |
|--------|-------|
| `catalog_source_count` | 3 |
| `etag_present_count` | 1 |
| `html_parser_source_count` | 3 |
| `last_modified_present_count` | 2 |
| `scheduled_refresh_count` | 3 |
| `source_grade_a_count` | 3 |
| `stale_source_count` | 0 |
| `url_source_count` | 3 |

## Decision Summary

| Action | Reason | Count |
|--------|--------|-------|
| `create_source` | `NEW_SOURCE` | 18 |
| `full_reindex` | `LARGE_OR_STRUCTURAL_CHANGE` | 4 |
| `manual_review_required` | `LOW_PARSER_CONFIDENCE` | 1 |
| `partial_refresh` | `SMALL_CONTENT_CHANGE` | 1 |
| `skip_refresh` | `SOURCE_HASH_UNCHANGED` | 4 |

## Recent Jobs

| Job | Type | Source | Status | Stage | Change Ratio | Reuse | Reembed | Index Skip |
|-----|------|--------|--------|-------|--------------|-------|---------|------------|
| 29 | refresh | 19 | skipped | skip_refresh | 0.0000 | 0 | 0 | 0 |
| 28 | refresh | 18 | succeeded | finished | 0.8889 | 1 | 3 | 0 |
| 27 | refresh | 17 | succeeded | finished | 0.9683 | 2 | 14 | 0 |
| 26 | create | 19 | succeeded | finished | 1.0000 | 0 | 149 | 0 |
| 25 | refresh | 18 | skipped | skip_refresh | 0.8889 | 0 | 0 | 0 |
| 24 | refresh | 17 | skipped | skip_refresh | 0.9683 | 0 | 0 | 0 |
| 23 | create |  | skipped | manual_review_required | 0.0000 | 0 | 0 | 0 |
| 22 | create | 18 | succeeded | finished | 1.0000 | 0 | 9 | 0 |
| 21 | create | 17 | succeeded | finished | 1.0000 | 0 | 63 | 0 |
| 19 | refresh | 15 | succeeded | finished | 0.6000 | 2 | 3 | 0 |

## Retrieval Cases

| Query | Passed | Category | Tag | Source | Fallback | Top Titles |
|-------|--------|----------|-----|--------|----------|------------|
| 다이어트 중 단백질이 부족할 때 한국 식단에서 무엇을 추가하면 좋을까? | True | True | True | True | False | 단백질이 부족한 날의 원칙 (1/5), 다이어트 중 단백질 보충 (2/5), 추천 표현 기준 (5/5) |
| 벤치프레스 중량은 언제 올리고 반복수는 어떻게 조절해야 할까? | True | True | True | True | False | 증량 기준 (6/8), 주요 운동 (1/5), 가슴 (1/5) |
| 스쿼트할 때 무릎 통증이 있으면 운동 추천을 어떻게 제한해야 할까? | True | True | True | True | False | 무릎 통증 시 보수적 대응 (3/5), 허리 통증 시 보수적 대응 (5/5), 어깨 통증 시 보수적 대응 (4/5) |
| 벌크업과 다이어트와 유지를 목표별로 어떻게 다르게 운영해야 할까? | True | True | True | True | False | 벌크업 (1/5), 매크로 비율 (2/4), 유지 (3/5) |
| 가슴, 등, 하체 운동을 주요 근육군 기준으로 설명해줘 | True | True | True | True | False | 하체 (4/5), 가슴 (1/5), 등 (2/5) |

## V1 Verdict

- Markdown seed corpus ingest, OpenSearch retrieval, decision trace, evaluation report 재생성을 검증한다.
- Text/PDF parser capability는 backend tests에서 file path 기반 fixture로 검증한다.
- OpenSearch 장애 fallback은 automated test와 policy trace 기준으로 검증한다.
