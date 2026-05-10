# RAG Catalog Control Plane

> **Purpose:** 공식 URL catalog를 바로 ingest하지 않고, 변경 감지 결과와 운영 판단을 DB plan으로 남긴 뒤 run id 기준으로 apply하는 RAG source registry 운영 계층을 정의한다.
> **Scope:** `backend/rag_sources/catalog.json`의 단일 페이지 HTML official source.
> **Out of scope:** crawler, scheduler worker, Admin UI, API connector, OCR, video transcript.

---

## 1. Core Message

RAG source는 한번 넣고 끝나는 파일이 아니라 계속 바뀌는 운영 자산이다. 이 프로젝트의 v1 control plane은 다음 질문에 답하는 것을 목표로 한다.

- 원격 공식 문서가 실제로 바뀌었는가?
- 바뀌었다면 문서 전체가 바뀐 것인가, 일부 section/chunk만 바뀐 것인가?
- parser/chunker/hash version 변경 때문에 강제 full reindex가 필요한가?
- 예상 embedding 비용과 허용 시간을 고려하면 지금 적용해도 되는가?
- 계획 이후 원격 문서가 다시 바뀌어 plan이 stale해지지는 않았는가?
- orphaned source나 low-confidence HTML을 자동으로 넣지 않고 검토 대상으로 남겼는가?

핵심은 `catalog-plan`과 `catalog-apply`를 분리하는 것이다. plan은 live fetch/parse/chunk/diff까지 수행하지만 RAG 원본 데이터와 OpenSearch를 변경하지 않는다. apply는 저장된 plan run을 운영자가 명시적으로 실행할 때만 source/chunk/index를 변경한다.

---

## 2. Data Model

### `rag_catalog_plan_runs`

Catalog plan 실행 단위다.

주요 필드:

- `catalog_file`, `catalog_version`
- `mode`: v1은 `live_fetch`
- `status`: `running`, `succeeded`, `failed`, `applied`
- `started_at`, `finished_at`
- `total_sources`, `matched_count`, `missing_count`, `orphaned_count`
- planned action summary: create, skip, partial, full, manual, defer
- `report_path`
- `summary`

### `rag_catalog_plan_items`

Source별 diff와 적용 결과다.

주요 필드:

- catalog metadata: `catalog_key`, `catalog_url`, `catalog_title`, `category`, `tags`, `license`, `source_grade`
- matching status: `missing`, `matched`, `orphaned`, `metadata_changed`
- fetch/parser status: `fetch_status`, `parser_confidence`
- old/new document hashes, ETag, Last-Modified
- `metadata_changed_fields`
- section/chunk diff counts and ratios
- `estimated_embedding_seconds`
- `quality_warnings`
- `planned_action`, `reason_code`, `risk_level`
- apply lifecycle: `apply_status`, `applied_job_id`, `applied_at`, `apply_error_code`, `apply_error_message`
- `context`

---

## 3. Stable Hash Lineage

HTML Hybrid Chunking은 content hash와 anchor hash를 분리한다. 이 분리는 partial refresh의 핵심이다.

| Field | Meaning | Used For |
|-------|---------|----------|
| `parent_anchor_hash` | source URL + heading path 기반 stable section 위치 | 같은 section 위치 추적 |
| `parent_content_hash` | parent section 내부 normalized text hash | section 내용 변경 감지 |
| `chunk_anchor_hash` | parent anchor + section 내부 child evidence index | 같은 child evidence 위치 추적 |
| `chunk_content_hash` | child evidence normalized content hash | chunk 내용 변경 감지 |
| `anchor_hash` | content-independent stable chunk anchor | existing chunk lineage 비교 |

기존 active chunk에 stable anchor metadata가 없으면 `ANCHOR_LINEAGE_MISSING`으로 보고 `full_reindex`를 계획한다. 이전 chunk boundary가 content-dependent였을 수 있기 때문에 부분 갱신을 시도하지 않는다.

---

## 4. Plan Decision Matrix

| Situation | Planned Action | Reason |
|-----------|----------------|--------|
| catalog에는 있지만 DB source가 없음 | `create_source` | `NEW_CATALOG_SOURCE` |
| DB에는 있지만 catalog에서 빠짐 | `manual_review_required` | `ORPHANED_SOURCE` |
| parser confidence 낮음 또는 chunk 없음 | `manual_review_required` | `QUALITY_GATE_FAILED` |
| 문서 hash와 metadata가 동일 | `skip_refresh` | `SOURCE_UNCHANGED` |
| stable anchor lineage 없음 | `full_reindex` | `ANCHOR_LINEAGE_MISSING` |
| parser/chunker/normalization version 변경 | `full_reindex` | `PIPELINE_VERSION_CHANGED` |
| embedding 예상 시간이 budget 초과 | `defer_reembedding` | `EMBEDDING_BUDGET_EXCEEDED` |
| section/chunk 변경 비율 < threshold | `partial_refresh` | `LOW_CHANGE_RATIO` |
| section/chunk 변경 비율 >= threshold | `full_reindex` | `HIGH_CHANGE_RATIO` |

`etag`와 `last_modified`는 freshness signal로 저장하지만 최종 판단은 normalized document hash와 section/chunk diff를 우선한다. 원격 header만 바뀌고 normalized content가 같으면 `skip_refresh`가 가능하다.

---

## 5. Apply Safety

`catalog-apply --run-id <id>`는 저장된 plan item을 source별로 적용한다.

Apply 전에는 같은 URL을 다시 fetch하고 planned `new_content_hash`와 현재 hash를 비교한다. 다르면 `PLAN_STALE`로 중단하고 source/chunk/OpenSearch는 변경하지 않는다.

Action별 처리:

- `create_source`: 기존 `register_url` ingest 경로 사용
- `partial_refresh`: 기존 refresh 경로를 stable anchor 기반으로 적용
- `full_reindex`: refresh 경로를 force full reindex로 적용
- `skip_refresh`: 데이터 변경 없이 `apply_status=skipped`
- `manual_review_required`: 데이터 변경 없이 `apply_status=blocked`
- `defer_reembedding`: 데이터 변경 없이 `apply_status=blocked`
- `orphaned`: 자동 archive/delete하지 않고 manual review 유지

적용된 item은 `applied_job_id`로 `rag_ingest_jobs`와 연결된다.

---

## 6. CLI

기본 운영 흐름:

```bash
docker compose exec backend python -m app.cli.rag catalog-plan \
  --file rag_sources/catalog.json \
  --report-path /workspace/docs/RAG_CATALOG_PLAN_REPORT.md

docker compose exec backend python -m app.cli.rag catalog-runs --limit 20
docker compose exec backend python -m app.cli.rag catalog-run --run-id <run_id>
docker compose exec backend python -m app.cli.rag catalog-apply --run-id <run_id>
```

`ingest-catalog`는 bootstrap/direct ingest 용도로 유지한다. 운영 기본 경로는 `catalog-plan` -> review -> `catalog-apply`다.

---

## 7. Report

`catalog-plan --report-path`는 Markdown report를 생성한다.

Report에 남기는 항목:

- run id, status, mode, catalog source count
- planned action summary
- source별 catalog status, planned action, reason code, risk level
- section/chunk change ratio
- quality warnings
- estimated embedding seconds

`validate-v1`은 latest catalog plan/run summary를 포함해 운영 검증 리포트에서 source acquisition 상태를 같이 확인한다.

---

## 8. Portfolio Signal

이 control plane은 다음 역량을 보여준다.

- 데이터 수집을 즉시 반영하지 않고 plan/apply로 분리하는 운영 설계
- section/chunk diff 기반의 부분 갱신 판단
- content hash와 anchor hash 분리를 통한 안정적인 lineage 관리
- embedding 비용, parser confidence, stale plan, orphaned source 같은 운영 리스크 처리
- DB에 계획과 적용 결과를 남기는 audit 가능한 RAG KnowledgeOps

---

## 9. Source Adapter Extension

The catalog control plane now supports two acquisition families with the same plan/apply lifecycle.

| Acquisition | Source | Parser | Notes |
|-------------|--------|--------|-------|
| `url_html` | operator registered official single-page URL | `html` | Backward compatible default when catalog rows omit `acquisition_type` |
| `local_file` | local MD/TXT/PDF path in `rag_sources/document_catalog.json` | `markdown`, `text`, `pdf_text` | Reproducible internal corpus and parser capability validation |

Local file items store file fingerprint metadata in source `metadata.fetch_metadata`: `file_size`, `mtime`, `raw_content_hash`, `resolved_path`, `reference_urls`, and `curation_method`. Apply re-reads the file and blocks with `PLAN_STALE` when the planned normalized content hash differs from the current file.

Official PDF URL acquisition, API connectors, scheduler workers, OCR, and video transcript adapters remain follow-up work. The current scope keeps persisted/embedded corpus reproducible and low-risk while preserving official references in metadata.

---

## 10. Review / Approval Layer

Catalog plan review is the operator checkpoint before apply.

```bash
docker compose exec backend python -m app.cli.rag catalog-review \
  --run-id <catalog_plan_run_id> \
  --report-path /workspace/docs/RAG_CATALOG_REVIEW_REPORT.md
```

The review layer reads plan items and writes `rag_review_runs`, `rag_review_items`, and a Markdown report. It does not call ingest, refresh, delete, or OpenSearch indexing.

Review decision examples:

- unchanged official source -> `no_action`
- new source -> `approve_create`
- limited section/chunk diff -> `approve_partial_refresh`
- large structural diff -> `manual_confirm_full_reindex`
- low confidence or orphaned source -> `blocked_manual_review`
- fetch or parser failure -> `fix_source_acquisition`

Only after review should an operator execute `catalog-apply --run-id <catalog_plan_run_id>`.
