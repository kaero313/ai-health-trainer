# RAG Advanced Portfolio Roadmap

> **Purpose:** AI Health Trainer가 단순한 AI 앱이 아니라, 운영 가능한 RAG/AI 백엔드 시스템이라는 점을 보여주기 위한 장기 고도화 기준서다.
> **Audience:** 포트폴리오 검토자, 백엔드/AI 엔지니어, Codex 작업자
> **Status:** 구현하면서 계속 보정하는 로드맵
> **Last updated:** 2026-05-02

---

## 1. Portfolio Message

이 프로젝트의 핵심 메시지는 "AI 채팅 기능을 붙인 건강 앱"이 아니다.

목표는 다음을 증명하는 것이다.

- 건강/운동/영양 지식을 출처, 라이선스, 버전, 신뢰도 기준으로 관리한다.
- 문서, PDF, 이미지, 영상, API 등 서로 다른 지식 입력을 일관된 RAG 자산으로 변환한다.
- embedding, chunk, index, trace, evaluation을 분리해 운영 가능한 검색/생성 파이프라인을 만든다.
- 데이터 변경, OpenSearch 장애, embedding 실패, 잘못된 지식 발견 같은 운영 상황을 복구 가능하게 처리한다.
- AI 답변이 어떤 지식과 사용자 기록을 근거로 생성됐는지 추적하고 평가한다.

포트폴리오에서 보여줘야 할 역량은 다음이다.

| Area | 보여줄 역량 |
|------|-------------|
| Backend architecture | source of truth, projection index, job lifecycle, idempotency, rollback |
| AI/RAG engineering | parser, chunking, embedding, hybrid retrieval, evaluation, trace |
| Data governance | source grade, license, freshness, medical boundary, audit |
| Operations | retry, stale index cleanup, blue-green alias, runbook, metrics |
| Product judgment | 건강 코칭 범위 제한, 안전 문서 우선 검색, 설명 가능한 source 제공 |

---

## 2. Current Baseline

현재 구현된 기준선은 다음과 같다.

- PostgreSQL
  - `rag_sources`: RAG 지식 출처와 버전/status 원장
  - `rag_chunks`: 검색 chunk와 `gemini-embedding-001` 3072차원 embedding
  - `rag_ingest_jobs`: ingest/reindex/archive 작업 기록
  - `rag_retrieval_traces`: 검색된 chunk/source/score/backend trace
  - `ai_generation_traces`: AI 생성 model/prompt/output trace
  - `rag_catalog_plan_runs`, `rag_catalog_plan_items`: 공식 URL catalog 변경 감지 plan/apply 원장

- OpenSearch
  - `rag_chunks_v1` index
  - `rag_chunks_current` read alias
  - keyword search
  - vector kNN search
  - hybrid score 병합

- Fallback
  - OpenSearch 장애 시 PostgreSQL/pgvector fallback
  - trace에 `search_backend=pgvector_fallback` 기록

- CLI KnowledgeOps
  - `ensure-index`
  - `delete-index`
  - `ingest`
  - `reindex`
  - `archive`
  - `evaluate`
  - `fetch-preview`, `register-url`, `ingest-catalog`
  - `catalog-plan`, `catalog-runs`, `catalog-run`, `catalog-apply`
  - `validate-v1`

이 baseline 위에 아래 고도화를 계속 쌓는다.

---

## 2-1. Knowledge Domains

우선 수집하고 운영할 지식 도메인은 다음으로 고정한다.

| Domain | Examples | Notes |
|--------|----------|-------|
| Nutrition | 칼로리, 매크로, 단백질, 식단 구성, 보충제 | 식품/영양 정보는 출처와 조건을 함께 기록 |
| Exercise science | 세트/반복, 점진적 과부하, 근비대, 근력, 유산소 | 사용자 운동 기록과 연결 가능한 형태로 chunk |
| Anatomy | 주요 근육군, 관절 움직임, 운동별 작용 근육 | 운동 추천과 통증/부상 판단의 보조 지식 |
| Safety | 통증, 부상 위험 신호, 운동 중단 기준, 전문가 상담 | safety category는 검색 시 우선순위를 둘 수 있어야 함 |
| App policy | 의료 진단 금지, 답변 한계, source 표시 정책 | LLM이 넘지 말아야 할 경계를 정의 |

수집 우선순위는 공식 가이드라인, 공공기관 자료, 학회 자료, peer-reviewed paper, 대학/병원 공개 자료, 직접 작성한 내부 요약 순서로 둔다.

---

## 3. P0: Core RAG Pipeline Control Plane

P0는 다음 vertical slice를 실운영 수준으로 완성하는 것이 목표다.

```text
source registry
 -> parser/chunker
 -> embedding
 -> PostgreSQL source/chunk 원장
 -> OpenSearch retrieval index
 -> hybrid retrieval
 -> AI prompt 반영
 -> retrieval/generation trace
 -> evaluation report
 -> 변경 감지와 refresh/reindex
 -> catalog plan/apply control plane
```

### 3-1. Source Registry

RAG 데이터는 단순 파일 목록이 아니라 운영 자산으로 등록한다.

관리해야 할 항목:

- `origin_type`: `internal_seed`, `file`, `url`, `api`, `pdf`, `image`, `video`
- `origin_uri`: 파일 경로, URL, API endpoint, storage key
- `source_grade`: `A`, `B`, `C`, `D`
- `license`: 원문 사용 가능 범위
- `author_or_org`: 출처 기관 또는 작성자
- `published_at`, `reviewed_at`
- `refresh_policy`: `manual`, `scheduled`, `never`
- `refresh_interval_hours`
- `last_checked_at`, `next_refresh_at`
- `external_etag`, `external_last_modified`
- `parser_type`, `chunk_strategy`
- `content_hash`
- `status`: `draft`, `active`, `archived`, `deleted`

포트폴리오 포인트:

- 지식 출처의 신뢰도와 갱신 주기를 명시적으로 관리한다.
- 저작권/라이선스 리스크를 RAG 파이프라인의 일부로 다룬다.
- RAG source를 삭제하지 않고 version/archive로 관리해 과거 AI 답변의 근거를 보존한다.
- 공식 URL catalog는 plan DB에 먼저 저장하고 run id 기준으로 apply해 운영자가 변경 범위와 리스크를 검토할 수 있게 한다.

### 3-2. Data Collection

수집 방식은 단계적으로 확장한다.

| Source | 1차 구현 | 고도화 방향 |
|--------|----------|-------------|
| 내부 seed Markdown | 구현됨 | source registry 기반 관리 |
| 공식 가이드라인/문서 | URL catalog 3종 구현 | source grade A/B, published/reviewed date 관리 |
| 논문/학회 자료 | 후속 | citation metadata, 요약 chunk 중심 |
| 로컬 text/markdown | CLI ingest | parser preview, refresh |
| PDF | 텍스트 추출 | page anchor, table extraction |
| URL 문서 | 공식 단일 페이지 HTML fetch + catalog plan/apply 구현 | scheduler, crawler가 아닌 source registry control plane 고도화 |
| 공개 API | 후속 | connector별 schema adapter |
| 이미지 | 후속 | OCR + vision caption |
| 영상 | 후속 | transcript + timestamp chunk |

수집 경로:

- CLI ingest: 운영자/개발자 수동 등록
- API ingest: admin API 기반 등록
- scheduled refresh: `next_refresh_at` 기준 갱신
- manual curation: source grade와 category/tag 검수
- connector: 외부 URL/API별 수집 adapter

### 3-3. Parser And Chunking

파일 유형별 parser/chunker 전략을 분리한다.

| Type | Parser | Chunk Strategy | Anchor |
|------|--------|----------------|--------|
| Markdown | heading/paragraph parser | section chunk | heading path |
| Text | paragraph parser | paragraph merge | paragraph range |
| PDF | page text extraction | page/section chunk | page number |
| HTML | main/article/body + heading parser | hybrid evidence chunk | heading path + parent_section_hash + URL |
| Table | structured parser | row group chunk | table id + row range |
| Image | OCR + vision caption | caption/object chunk | image region |
| Video | transcript parser | timestamp segment chunk | start/end timestamp |

Chunk 품질 기준:

- chunk 하나는 하나의 주장, 규칙, 절차, 기준을 담는다.
- 건강/운동 수치는 단위와 조건을 포함한다.
- 벌크업/다이어트처럼 반대 목표의 기준은 같은 chunk에 섞지 않는다.
- chunk만 읽어도 의미가 유지되어야 한다.
- 긴 문서는 section parent와 child chunk를 분리할 수 있어야 한다.
- overlap은 문맥 손실이 있는 문서에만 제한적으로 사용한다.

### 3-4. Embedding And Indexing

현재 기본값:

- embedding model: `gemini-embedding-001`
- embedding dimension: `3072`
- pgvector column: `rag_chunks.embedding VECTOR(3072)`
- OpenSearch vector field: `knn_vector`
- OpenSearch method: `lucene` + `hnsw` + `cosinesimil`
- read alias: `rag_chunks_current`

관리해야 할 항목:

- `embedding_model`
- `embedding_dim`
- `content_hash`
- `source_version`
- `chunk_version`
- `opensearch_index`
- `opensearch_document_id`
- `index_status`
- `indexed_at`

선택 근거:

- 3072차원은 `gemini-embedding-001` 기준의 표현력을 보존한다.
- OpenSearch HNSW/ANN은 대량 retrieval 성능을 위한 기본 경로다.
- PostgreSQL/pgvector는 source of truth와 fallback 역할이다.
- OpenSearch index는 언제든 PostgreSQL 원장으로부터 재생성 가능해야 한다.

### 3-5. Change Detection And Refresh

데이터 변경 감지는 다음 순서로 처리한다.

```text
source refresh request
 -> etag/last_modified 확인
 -> 원문 fetch
 -> normalized content hash 계산
 -> 기존 active source hash와 비교
 -> 동일하면 skipped job
 -> 변경되면 source version 증가
 -> 기존 chunks archive
 -> 변경 chunk embedding 생성
 -> OpenSearch reindex
 -> evaluation 실행
 -> 성공 시 active 유지
```

운영 원칙:

- 같은 `content_hash + embedding_model` 조합은 중복 embedding하지 않는다.
- 변경되지 않은 chunk는 embedding 재사용을 고려한다.
- 기존 chunk는 hard delete보다 archive를 기본으로 한다.
- OpenSearch stale document는 cleanup 대상이다.
- refresh 실패는 source 원장을 잃지 않고 job error로 기록한다.
- 잘못된 지식이 발견되면 archive + reason + re-evaluation을 수행한다.

### 3-6. Retrieval Strategy

검색은 단순 vector search 하나로 끝내지 않는다.

기본 순서:

1. 사용자 context 기반 retrieval query 생성
2. category/tag/source_grade filter 적용
3. OpenSearch keyword search
4. OpenSearch vector search
5. hybrid score 병합
6. PostgreSQL source/chunk 재조회
7. safety/policy 문서 우선순위 보정
8. prompt context 구성
9. trace 저장

고도화 후보:

- query expansion
- multi-query retrieval
- reranker
- source grade boosting
- safety category forced retrieval
- no-result fallback
- freshness boosting
- user goal 기반 category weighting

### 3-7. Evaluation

RAG 품질은 retrieval과 generation을 분리해서 평가한다.

Retrieval evaluation:

- recall@k
- MRR
- expected category match
- expected tag match
- expected source match
- safety query에서 safety source 포함 여부
- no-result rate
- fallback rate
- stale index hit rate
- latency p50/p95

Generation evaluation:

- 사용자 기록 반영 여부
- RAG 근거 반영 여부
- source title 노출 여부
- 의료 진단/치료 표현 회피
- JSON schema 준수
- hallucination risk
- prompt version별 회귀 비교

CI/운영 기준:

- RAG 데이터나 prompt 변경 시 evaluation을 실행한다.
- 기준 미달 시 OpenSearch alias 전환을 막는다.
- evaluation report를 문서로 남긴다.

---

## 3-8. Decision And Policy Layer

고급 포트폴리오에서 중요한 지점은 "결과가 잘 나왔다"가 아니라, 현재 상황에서 어떤 제약을 고려해 어떤 선택을 했는지 설명 가능한 것이다.

RAG pipeline은 다음 판단을 코드와 trace로 남긴다.

- source hash가 같을 때 skip할지 forced refresh할지
- 변경 비율이 낮을 때 partial refresh로 충분한지
- parser/chunker/normalization version 변경으로 full reindex가 필요한지
- parser confidence가 낮아 수동 검토가 필요한지
- 재임베딩 예상 시간이 운영 예산을 넘는지
- OpenSearch 장애 시 pgvector fallback을 허용할지
- safety/policy source freshness를 어떻게 우선할지

상세 정책은 `docs/RAG_DECISION_POLICY.md`에서 관리한다.

---

## 4. P1: Operations Hardening

P1은 운영 장애와 품질 저하에 대응하는 능력을 보여주는 단계다.

필수 항목:

- failed/pending chunk retry
- ingest job retry count와 max retry
- OpenSearch 장애 시 degraded trace
- stale index cleanup
- blue-green index 재색인
- alias 전환 전 evaluation gate
- source archive/delete runbook
- embedding rate limit과 timeout 처리
- batch embedding과 비용 제어
- search latency metric
- fallback rate metric
- source freshness report

포트폴리오 포인트:

- 단순 성공 경로가 아니라 실패/복구/관측 가능성을 설계한다.
- OpenSearch와 PostgreSQL의 consistency 경계를 명확히 다룬다.
- 운영자가 어떤 job이 실패했고 무엇을 재시도해야 하는지 알 수 있게 한다.

---

## 5. P2: Multimodal And Connector Expansion

P2는 입력 데이터 종류와 검색 품질을 넓히는 단계다.

확장 후보:

- URL connector
  - robots/license 확인
  - etag/last_modified refresh
  - HTML section chunk

- API connector
  - 공공 영양/식품/운동 데이터 API
  - connector별 schema adapter
  - rate limit과 cache

- PDF advanced
  - table extraction
  - heading reconstruction
  - page image OCR

- Image RAG
  - OCR text
  - Gemini vision caption
  - image region metadata

- Video RAG
  - transcript ingestion
  - timestamp chunk
  - exercise form/safety segment metadata

- Retrieval quality
  - reranker
  - user-specific personalization layer
  - freshness/source-grade score boosting

---

## 6. Security, Privacy, And Safety

건강/운동 AI에서 RAG는 안전 정책과 개인정보 보호를 포함해야 한다.

필수 고려:

- 개인정보 포함 문서는 RAG source로 ingest하지 않는다.
- admin-only ingest 권한을 둔다.
- source license를 기록하고 무단 복제를 피한다.
- 의료 진단, 약물, 질병 치료 지식은 생활 습관 코칭 범위로 제한한다.
- 통증/부상/위험 신호 query는 safety source를 우선 검색한다.
- AI 응답은 전문가 상담 안내와 한계를 포함해야 한다.
- trace에는 민감한 원문을 과도하게 남기지 않는다.

---

## 7. Roadmap Order

추천 구현 순서:

1. RAG Pipeline Control Plane
   - source registry
   - parser/chunker interface
   - document/PDF vertical slice
   - refresh CLI

2. RAG E2E Verification
   - OpenSearch ensure-index
   - seed ingest
   - retrieval evaluation
   - evaluation report

3. Operations Debugging
   - trace lookup CLI/API
   - failed job retry
   - stale index cleanup

4. Blue-Green Reindex
   - `rag_chunks_v2`
   - evaluation gate
   - alias switch

5. External Connectors
   - URL/API source registration
   - scheduled refresh

6. Multimodal RAG
   - image OCR/vision
   - video transcript/timestamp

---

## 8. Definition Of Done

고급 포트폴리오로 설득력 있으려면 다음 산출물이 있어야 한다.

- architecture document
- operating guide
- source registry schema
- parser/chunker strategy
- real ingest command
- real OpenSearch index
- retrieval evaluation report
- trace sample
- failure/retry runbook
- commit history showing incremental design decisions

이 문서는 구현이 진행될수록 계속 업데이트한다.
