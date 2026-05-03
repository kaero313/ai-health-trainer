# RAG Decision Policy

> **Purpose:** RAG 파이프라인이 상황별 제약을 어떻게 판단하고 어떤 근거를 남기는지 정의한다.
> **Audience:** 백엔드/AI 엔지니어 포트폴리오 검토자, 운영자, Codex 작업자
> **Last updated:** 2026-05-02

---

## 1. Core Message

이 프로젝트의 RAG 품질은 검색 결과 하나로만 판단하지 않는다.

핵심은 다음 질문에 답할 수 있는가이다.

- 어떤 문서가 들어왔고 신뢰할 수 있는가?
- 어떤 parser/chunker를 선택했고 왜 그 선택이 안전한가?
- 문서가 바뀌었을 때 전체 재임베딩이 필요한가, 부분 갱신이 충분한가?
- 재임베딩 시간이 운영 예산을 넘으면 어떤 선택을 하는가?
- OpenSearch 장애 시 사용자 요청을 중단할 것인가, degraded fallback을 허용할 것인가?
- AI 응답에 사용된 지식이 언제, 어떤 정책으로 갱신되었는지 재현 가능한가?

따라서 RAG pipeline은 기능 처리와 별개로 `rag_pipeline_decisions`에 의사결정 기록을 남긴다.

---

## 2. Decision Inputs

RAG pipeline decision은 다음 값을 고려한다.

| Input | Meaning |
|-------|---------|
| `document_type` | markdown, text, pdf_text, future image/video/url/api |
| `parser_type` | 실제 선택된 parser |
| `parser_confidence` | parser가 원문을 충분히 추출했다고 판단하는 신뢰도 |
| `source_grade` | source 신뢰 등급 |
| `category` / `tags` | safety, nutrition, exercise 등 검색 정책 영향 |
| `content_hash` | source normalized content hash |
| `change_ratio` | 기존 active chunk 대비 변경 비율 |
| `parser_or_chunker_changed` | parser/chunker/normalization version 변경 여부 |
| `embedding_input_hash` | embedding model, dim, normalization, chunk content 기준 hash |
| `estimated_embedding_seconds` | 재임베딩 예상 시간 |
| `allowed_embedding_seconds` | 이번 작업에서 허용하는 시간 예산 |
| `opensearch_status` | retrieval index 사용 가능 여부 |

---

## 2-1. URL/HTML Refresh Inputs

Official URL sources add remote freshness and Hybrid Chunking context to the same decision record.

| Input | Meaning |
|-------|---------|
| `final_url` | Redirect 이후 실제 수집 URL |
| `content_type` | HTML parser 적용 근거 |
| `etag_changed` | 이전 fetch 대비 ETag 변경 여부 |
| `last_modified_changed` | 이전 fetch 대비 Last-Modified 변경 여부 |
| `raw_content_hash` | HTTP body byte hash |
| `changed_section_count` | parent section hash 기준 변경 section 수 |
| `total_section_count` | 현재/이전 parent section 수의 최대값 |
| `section_change_ratio` | section 단위 변경 비율 |

Policy interpretation:

- `etag` 또는 `last_modified`가 바뀌어도 normalized document hash가 같으면 `skip_refresh`가 가능하다.
- document hash가 바뀌고 `section_change_ratio`가 threshold 미만이면 `partial_refresh`가 우선이다.
- parser/chunker version 변경, heading 구조 대량 변경, section ratio threshold 초과는 `full_reindex`다.
- parser confidence가 낮은 HTML은 공식 URL이어도 `manual_review_required`로 멈춘다.

---

## 3. Default Policy

| Situation | Action | Risk | Reason |
|-----------|--------|------|--------|
| source hash unchanged | `skip_refresh` | low | 비용과 색인 churn을 줄인다. |
| parser confidence < 0.70 | `manual_review_required` | high | 낮은 품질의 지식이 prompt context에 들어가는 것을 막는다. |
| estimated embedding time exceeds budget | `defer_reembedding` | medium | API quota, 작업 시간, 운영 지연을 보호한다. |
| new source | `create_source` | low/medium | source registry, job, trace를 남기며 신규 등록한다. |
| change ratio < 0.30 | `partial_refresh` | low | 안정적인 chunk와 embedding을 재사용한다. |
| change ratio >= 0.30 | `full_reindex` | medium | 구조 변화가 크므로 stale anchor risk를 낮춘다. |
| parser/chunker/normalization version changed | `full_reindex` | medium | hash와 chunk boundary 의미가 바뀌었으므로 전체 projection을 재구성한다. |
| OpenSearch unavailable | `pgvector_fallback` | medium | 사용자 요청은 유지하되 degraded retrieval로 trace를 남긴다. |

---

## 4. Hash Policy

Hash는 단순 중복 제거가 아니라 운영 판단의 근거다.

| Hash | Scope | Used For |
|------|-------|----------|
| `content_hash` | normalized chunk text | chunk 내용 변경 감지 |
| `anchor_hash` | source 내부 논리 위치 | 같은 위치의 chunk lineage 추적 |
| `embedding_input_hash` | model + dim + normalization + content | embedding cache 재사용 판단 |
| `index_payload_hash` | OpenSearch projection payload | 불필요한 재색인 skip |

Hash metadata에는 `hash_schema_version`, `normalization_version`, `parser_version`, `chunker_version`을 함께 남긴다.

---

## 5. Refresh Examples

### Same Document

```text
source hash unchanged
 -> selected_action=skip_refresh
 -> no embedding call
 -> no OpenSearch indexing
 -> job.status=skipped
```

### Small Content Change

```text
change_ratio < 0.30
 -> selected_action=partial_refresh
 -> unchanged chunk stays active
 -> changed chunk gets new embedding unless embedding_input_hash cache hit
 -> deleted anchors are archived
```

### Large Or Structural Change

```text
change_ratio >= 0.30 or parser/chunker version changed
 -> selected_action=full_reindex
 -> old active chunks archived
 -> new chunks generated
 -> embeddings reused from cache where possible
```

### Low Confidence PDF

```text
parser_confidence < 0.70
 -> selected_action=manual_review_required
 -> no active chunks created
 -> operator reviews source or switches parser/OCR path
```

### Embedding Time Budget Exceeded

```text
estimated_embedding_seconds > allowed_embedding_seconds
 -> selected_action=defer_reembedding
 -> source remains on previous active version
 -> job records skipped_reason=EMBEDDING_TIME_BUDGET_EXCEEDED
```

### Retrieval Index Failure

```text
OpenSearch keyword/vector search fails
 -> selected_action=pgvector_fallback
 -> PostgreSQL/pgvector retrieval is used
 -> retrieval trace stores search_backend=pgvector_fallback
```

---

## 6. What Gets Stored

`rag_ingest_jobs` stores lifecycle metrics:

- `pipeline_stage`
- `parser_confidence`
- `change_ratio`
- `embedding_reuse_count`
- `reembedding_count`
- `index_skip_count`
- `estimated_embedding_seconds`
- `latency_ms`
- `skipped_reason`

`rag_pipeline_decisions` stores the actual reasoning record:

- `decision_type`
- `policy_version`
- `selected_action`
- `risk_level`
- `reason_code`
- `context`
- `tradeoffs`

`rag_embedding_cache` separates embedding reuse from chunk lifecycle:

- same `embedding_input_hash` can be reused by new source versions
- archived chunks do not delete reusable embeddings
- `usage_count` and `last_used_at` show reuse value

---

## 7. Portfolio Signal

이 정책 계층은 다음 역량을 보여주기 위한 것이다.

- 결과 중심이 아니라 운영 상황 중심으로 RAG pipeline을 설계한다.
- API 비용, latency, 장애, freshness, source risk를 코드와 trace로 표현한다.
- 재임베딩과 재색인을 무조건 수행하지 않고 합리적으로 skip/reuse/defer한다.
- parser/chunker/hash/model version을 함께 관리해 재현 가능성을 보장한다.
- 검색 품질 평가와 운영 지표를 분리해 장기 고도화가 가능하게 한다.
