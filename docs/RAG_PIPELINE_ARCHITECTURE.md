# RAG Pipeline Architecture

> **Purpose:** 다음 구현 단계인 RAG Pipeline Control Plane의 기준을 좁혀 정의한다.
> **Scope:** 문서/Markdown/Text/PDF 기반 RAG ingest, refresh, reindex, evaluation
> **Out of scope for v1:** 이미지 OCR, 영상 transcript, table extraction, 외부 API scheduler worker의 완성 구현
> **Last updated:** 2026-05-02

---

## 1. Goal

이번 단계의 목표는 전체 RAG 운영 파이프라인의 골격을 코드와 문서에서 일치시키는 것이다.

v1 vertical slice:

```text
registered source
 -> parser
 -> chunker
 -> embedding
 -> PostgreSQL source/chunk 원장
 -> OpenSearch index
 -> retrieval evaluation
 -> refresh/reindex
```

문서/PDF 경로는 실제 구현하고, 이미지/영상/API connector는 확장 가능한 인터페이스와 운영 정책으로 남긴다.

---

## 2. Source Registry

RAG source는 ingest 시점의 임시 입력이 아니라, 갱신 가능한 운영 자산이다.

권장 metadata:

| Field | Description |
|-------|-------------|
| `origin_type` | `internal_seed`, `file`, `url`, `api`, `pdf`, `image`, `video` |
| `origin_uri` | 파일 경로, URL, API endpoint, storage key |
| `ingest_method` | `cli`, `admin_api`, `scheduled`, `manual_seed` |
| `parser_type` | `markdown`, `text`, `pdf_text`, `html`, `image_ocr`, `video_transcript` |
| `chunk_strategy` | `section`, `paragraph`, `page`, `table_row`, `timestamp` |
| `refresh_policy` | `manual`, `scheduled`, `never` |
| `refresh_interval_hours` | scheduled refresh 간격 |
| `last_checked_at` | 마지막 원본 확인 시각 |
| `next_refresh_at` | 다음 refresh 대상 시각 |
| `external_etag` | URL/API source의 etag |
| `external_last_modified` | 외부 source의 last-modified |
| `last_refresh_status` | `succeeded`, `skipped`, `failed` |

기존 `rag_sources`의 `metadata` JSONB는 v1에서 빠른 확장을 위해 사용할 수 있다. 이후 운영 요구가 고정되면 명시 컬럼으로 승격한다.

---

## 3. Parser Interface

Parser는 원본 입력을 검색 가능한 section 단위로 바꾼다.

권장 내부 타입:

```text
ParsedDocument
  title
  source_uri
  parser_type
  content_hash
  sections[]

ParsedSection
  title
  text
  anchor
  page_number
  metadata
```

Parser별 v1 정책:

| Parser | Input | Output | Notes |
|--------|-------|--------|-------|
| `markdown` | `.md` | heading 기반 sections | heading path를 anchor로 기록 |
| `text` | `.txt` | paragraph sections | paragraph range를 anchor로 기록 |
| `pdf_text` | `.pdf` | page text sections | `pypdf` 기반 텍스트 추출, page_number 기록 |

후속 parser:

- `html`: readability + heading parser
- `table`: row group parser
- `image_ocr`: OCR text + vision caption
- `video_transcript`: timestamp transcript segment

---

## 4. Chunker Strategy

Chunker는 `ParsedSection`을 embedding 가능한 `rag_chunks`로 변환한다.

v1 기본값:

- default strategy: `section`
- min size: 80자
- max size: 1000~1200자
- overlap: 기본 0
- merge: 너무 짧은 section은 인접 chunk와 병합
- split: 너무 긴 section은 문장 단위로 분할

Chunk metadata:

| Field | Description |
|-------|-------------|
| `chunk_strategy` | section/page/paragraph |
| `chunk_anchor` | heading path, paragraph range, page number |
| `page_number` | PDF page 기반 chunk일 때 기록 |
| `token_count` | 추정 token 수 |
| `content_hash` | normalized chunk text hash |

품질 기준:

- 하나의 chunk에는 하나의 주제나 규칙만 담는다.
- page chunk는 page 번호를 유지한다.
- PDF에서 페이지 텍스트가 비어 있으면 skipped section으로 기록한다.
- 안전/통증 관련 내용은 `safety` category 또는 safety tag로 식별 가능해야 한다.

---

## 5. Ingest Flow

문서/PDF ingest 흐름:

```text
register-source
 -> source metadata 저장
 -> parse source
 -> normalized content hash 계산
 -> chunk 생성
 -> embedding 생성
 -> rag_chunks 저장
 -> OpenSearch 색인
 -> rag_ingest_jobs succeeded/failed 기록
```

CLI 기준:

```bash
python -m app.cli.rag register-source \
  --origin-uri backend/rag_data/nutrition_basics.md \
  --title "Nutrition Basics" \
  --category nutrition \
  --tags nutrition,macro \
  --parser auto \
  --chunk-strategy section \
  --refresh-policy manual
```

`ingest`는 기존 단일 문서 즉시 저장 명령으로 유지한다. `register-source`는 refresh/reindex 가능한 운영 source를 만드는 명령이다.

---

## 6. Refresh And Reindex Flow

Refresh는 source registry를 기준으로 변경을 감지한다.

```text
refresh-source
 -> origin read/fetch
 -> external_etag/last_modified 확인
 -> normalized content hash 계산
 -> 기존 hash와 비교
 -> 같으면 skipped job
 -> 다르면 기존 chunks archive
 -> source version 증가
 -> 새 chunks 생성
 -> embedding 생성
 -> OpenSearch 색인
 -> evaluation 대상 표시
```

CLI 기준:

```bash
python -m app.cli.rag refresh-source --source-id 1
python -m app.cli.rag refresh-source --source-id 1 --force
python -m app.cli.rag refresh-due --limit 20
```

운영 원칙:

- 변경 없음은 실패가 아니라 `skipped`다.
- OpenSearch 색인 실패는 PostgreSQL 저장 실패와 분리한다.
- source/chunk 원장은 보존하고 `index_status=failed`로 재시도 가능하게 둔다.
- 기존 AI 답변이 참조한 chunk는 FK 무결성을 유지한다.

---

## 6-1. Decision And Policy Layer

Refresh/reindex는 단순히 성공/실패만 기록하지 않는다. 각 작업은 현재 상황과 제약을 평가한 뒤 `rag_pipeline_decisions`에 선택 근거를 남긴다.

기본 판단 기준:

- source hash가 같으면 `skip_refresh`
- parser confidence가 0.70 미만이면 `manual_review_required`
- 변경 chunk 비율이 0.30 미만이면 `partial_refresh`
- 변경 chunk 비율이 0.30 이상이거나 parser/chunker/normalization version이 바뀌면 `full_reindex`
- 재임베딩 예상 시간이 허용 시간을 넘으면 `defer_reembedding`
- OpenSearch 장애 시 retrieval은 `pgvector_fallback`

자세한 정책은 `docs/RAG_DECISION_POLICY.md`를 따른다.

---

## 7. Retrieval And Evaluation

Retrieval path:

```text
query
 -> query embedding
 -> OpenSearch keyword search
 -> OpenSearch vector search
 -> hybrid merge
 -> PostgreSQL source/chunk load
 -> prompt context
 -> retrieval trace
```

Evaluation path:

```text
evaluation cases
 -> RAGService.search()
 -> category/tag/source match
 -> score/backend/index 기록
 -> pass/fail summary
 -> report markdown
```

다음 단계에서는 `docs/RAG_EVALUATION_REPORT.md`를 생성해 실제 결과를 기록한다.

평가 기준:

- expected category match
- expected tag match
- expected source keyword match
- top-k source title
- search backend
- search mode
- index version
- fallback 여부
- no-result 여부

---

## 8. OpenSearch And pgvector Roles

OpenSearch:

- 기본 retrieval index
- keyword search
- vector kNN search
- hybrid retrieval
- category/tag/source_grade/status filter

PostgreSQL/pgvector:

- source of truth
- embedding 원장
- OpenSearch 장애 fallback
- reindex source
- trace/audit 보관

원칙:

- OpenSearch는 검색 projection이다.
- PostgreSQL에 없는 chunk는 prompt에 넣지 않는다.
- OpenSearch 결과가 PostgreSQL에서 조회되지 않으면 stale index로 보고 제외한다.
- index 변경은 alias로 전환한다.

---

## 9. Failure Modes

| Failure | Handling |
|---------|----------|
| parser failure | ingest job `failed`, source draft 유지 |
| empty PDF page | section skipped, job warning |
| embedding failure | chunk `index_status=pending`, job failed |
| OpenSearch unavailable | PostgreSQL commit 유지, `index_status=failed` |
| stale OpenSearch hit | trace에 기록 후 prompt 제외 |
| unchanged source | job `skipped` |
| bad source discovered | source/chunks archive, OpenSearch delete |

---

## 10. Acceptance Criteria For Next Implementation

다음 구현은 아래 기준을 만족해야 한다.

- source registry metadata를 저장할 수 있다.
- Markdown/Text/PDF text parser preview가 가능하다.
- parser 결과가 section/page anchor를 가진다.
- source refresh 시 content hash 변경 여부를 판단한다.
- 변경 없음은 skipped job으로 기록한다.
- 변경 있음은 기존 chunks archive 후 새 chunks를 만든다.
- OpenSearch 색인 실패와 DB 저장 실패를 분리한다.
- retrieval evaluation 결과를 사람이 읽을 수 있는 report로 남긴다.

---

## 11. Later Extensions

v1 이후 확장:

- URL/API connector
- APScheduler 또는 별도 worker
- image OCR/vision caption parser
- video transcript/timestamp parser
- table extraction
- reranker
- blue-green index evaluation gate
- admin debug API
- source freshness dashboard
