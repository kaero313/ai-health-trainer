# AI Health Trainer - RAG Knowledge Operations Guide

> **이 문서의 목적:** AI Health Trainer의 RAG 지식 데이터를 어떻게 수집, 정제, 저장, 검색, 갱신, 삭제, 추적할지 정의한다.
> **대상:** 백엔드/AI 개발자 포트폴리오 검토자, Codex/AI 작업자, 프로젝트 유지보수자
> **현재 기준:** 실제 구현은 코드가 우선하며, 제품/개발 의사결정은 `docs/OWNER_GUIDE.md`를 우선한다.
> **작성일:** 2026-05-01

---

## 1. 목적과 포지셔닝

이 프로젝트의 RAG는 단순히 LLM 답변에 참고 문서를 붙이는 기능이 아니다.

목표는 사용자의 음식 사진 분석 결과, 식단 기록, 운동 기록, 체중 변화, 신체 프로필을 도메인 지식과 결합하여 **추적 가능하고 갱신 가능한 개인화 AI 코칭 답변**을 만드는 것이다.

포트폴리오 관점에서 보여주어야 할 핵심은 다음과 같다.

| 영역 | 보여줄 역량 |
|------|-------------|
| 데이터 설계 | 원문, chunk, embedding, version, source, trace를 분리해 관리 |
| 운영 설계 | 문서 추가, 수정, 삭제, 재색인, 실패 복구 정책 |
| AI 품질 관리 | prompt/model/source/similarity를 기록해 답변 원인 추적 |
| 도메인 안전성 | 의료 진단이 아닌 생활 습관 코칭 범위로 제한 |
| 백엔드 숙련도 | 비동기 처리, idempotency, soft delete, audit trail, evaluation 고려 |

현재 구현은 `rag_documents` 단일 테이블에 chunk와 embedding을 저장하고, `RAGService.search()`로 pgvector 검색을 수행한다. v2 목표 구조는 **PostgreSQL을 RAG source of truth로 두고, OpenSearch를 retrieval index로 사용하는 Option B 아키텍처**다.

---

## 2. 구현 방안: PostgreSQL + OpenSearch Option B

RAG 운영 계층은 두 저장소의 책임을 명확히 분리한다.

```text
PostgreSQL
  - RAG 운영 원장(source of truth)
  - source/chunk/version/status/license/tag 관리
  - ingest/reindex/delete job 상태 관리
  - retrieval trace / generation trace / audit 보관
  - 과거 AI 답변 재현성 보장

OpenSearch
  - RAG retrieval index
  - keyword search
  - vector kNN search
  - hybrid search
  - category/tag/status 필터
  - admin/debug search
```

핵심 원칙:

- PostgreSQL에 저장되지 않은 RAG 문서는 OpenSearch에 색인하지 않는다.
- OpenSearch 문서 id는 PostgreSQL `rag_chunks.id`와 동일하게 맞춘다.
- OpenSearch는 검색 최적화 계층이며 원본 저장소가 아니다.
- 검색 결과는 OpenSearch에서 얻되, 최종 prompt와 trace에는 PostgreSQL chunk/source 정보를 기준으로 저장한다.
- OpenSearch 장애 시 PostgreSQL/pgvector fallback을 사용하거나 "검색 degraded" 상태를 trace에 남긴다.

### 2-1. 최종 요청 흐름

```text
문서 추가/수정
  -> PostgreSQL rag_sources 저장
  -> PostgreSQL rag_chunks 저장
  -> embedding 생성
  -> OpenSearch rag_chunks index 색인
  -> ingest job succeeded 기록

AI 추천/채팅 요청
  -> 사용자 context 요약
  -> retrieval query 생성
  -> OpenSearch hybrid/vector search
  -> 반환된 chunk_id로 PostgreSQL chunk/source 조회
  -> LLM prompt 생성
  -> rag_retrieval_traces 저장
  -> ai_generation_traces 저장
```

### 2-2. 저장소 선택 이유

| 책임 | PostgreSQL | OpenSearch |
|------|------------|------------|
| 원문/source 관리 | 강함 | 약함 |
| version/status/audit | 강함 | 약함 |
| FK/transaction | 강함 | 없음 |
| keyword 검색 | 보통 | 강함 |
| vector 검색 | 가능(pgvector) | 강함 |
| hybrid retrieval | 제한적 | 강함 |
| 운영 trace | 강함 | 보조 |

이 설계의 포트폴리오 메시지는 다음과 같다.

> RAG 문서의 정확성, 버전, 삭제 상태, 감사 로그는 PostgreSQL에 보관하고, retrieval 성능과 hybrid search는 OpenSearch 인덱스로 분리했다. 두 저장소는 chunk id와 index version으로 연결되며, 모든 AI 답변은 당시 검색된 source/chunk/model/prompt를 추적할 수 있다.

---

## 3. RAG가 답변에 개입하는 흐름

```text
사용자 데이터
  - 프로필: 키, 체중, 목표, 활동 수준, 알레르기, 선호 식품
  - 식단: 음식 사진 분석 결과, 일별 섭취 칼로리/매크로
  - 운동: 운동명, 근육군, 세트, 반복, 중량, 최근 기록
  - 체중: 날짜별 체중 변화

도메인 지식 데이터
  - 영양학
  - 운동 생리학
  - 해부학
  - 부상 예방
  - 목표별 전략

RAG 검색
  - 사용자 상황을 검색 query로 변환
  - category/tag 필터 적용
  - OpenSearch hybrid/vector 기준 top-k 검색
  - 필요 시 PostgreSQL/pgvector fallback
  - 검색 결과와 similarity score 기록

LLM 생성
  - 사용자 데이터 + RAG context + prompt version + safety rule
  - 구조화 JSON 응답 생성
  - 추천 결과, source, model, prompt, trace 저장
```

---

## 4. 지식 도메인 분류

RAG 문서는 category와 tag를 함께 사용한다. category는 검색 필터의 1차 기준이고, tag는 세부 검색/운영/평가 기준이다.

| Category | 설명 | 예시 Tags |
|----------|------|-----------|
| `nutrition` | 영양소, 식단 구성, 칼로리, 매크로, 식품 선택 | `protein`, `carbs`, `fat`, `calorie_deficit`, `korean_food` |
| `exercise` | 운동 프로그램, 세트/반복, 점진적 과부하, 회복 | `progressive_overload`, `hypertrophy`, `strength`, `cardio` |
| `anatomy` | 근육군, 관절, 움직임 패턴, 운동별 주요 작용 근육 | `chest`, `back`, `legs`, `shoulder`, `joint` |
| `safety` | 부상 예방, 통증 대응, 운동 금기, 위험 신호 | `injury_prevention`, `pain`, `deload`, `medical_referral` |
| `goal_strategy` | 벌크업, 다이어트, 유지, 체중 변화 전략 | `bulk`, `diet`, `maintain`, `plateau` |
| `app_policy` | 앱 내부 AI 응답 정책, 금지 표현, 상담 권고 기준 | `medical_boundary`, `disclaimer`, `fallback` |

검색 시 기본 매핑은 다음과 같다.

| 기능 | 기본 Category | 보조 Category |
|------|---------------|---------------|
| 식단 추천 | `nutrition` | `goal_strategy`, `safety` |
| 운동 추천 | `exercise` | `anatomy`, `safety`, `goal_strategy` |
| AI 채팅 | 질문 의도 기반 | 전체 category 가능 |
| 음식 사진 분석 후 설명 | `nutrition` | `app_policy` |

---

## 5. 출처 신뢰도 기준

RAG 데이터는 답변 품질과 안전성에 직접 영향을 준다. 출처는 아래 기준으로 등급을 부여한다.

| Grade | 허용 기준 | 예시 |
|-------|-----------|------|
| A | 공공기관, 학회, 공식 가이드라인, peer-reviewed 논문 | WHO, NIH, ACSM, ISSN, 정부/공공 영양 자료 |
| B | 대학/병원/전문기관 자료, 검증 가능한 교재성 자료 | 대학 공개 강의, 병원 건강 정보, 스포츠 과학 교재 요약 |
| C | 전문가 작성 글이지만 원출처 확인이 필요한 자료 | 전문가 블로그, 트레이너 가이드 |
| D | 일반 블로그, 커뮤니티, 광고성 콘텐츠 | 기본적으로 ingest 금지 |

운영 원칙:

- 기본 ingest 대상은 Grade A/B로 제한한다.
- Grade C는 source note와 검토 사유가 있어야 한다.
- Grade D는 앱 정책 문서나 부정 예시 평가셋이 아닌 이상 RAG 본문으로 사용하지 않는다.
- 논문/가이드라인은 발행일과 검토일을 기록한다.
- 저작권이 있는 원문 전체를 무단 저장하지 않는다. 필요한 경우 짧은 요약, 자체 정리문, 출처 링크를 저장한다.
- 의료 진단, 질병 치료, 약물 조정 관련 내용은 직접 처방하지 않고 전문가 상담 안내 정책으로 연결한다.

---

## 6. 문서 수집과 정제 규칙

### 6-1. 수집 대상

수집 대상은 "사용자 기록 기반 코칭에 실질적으로 필요한 지식"으로 제한한다.

우선순위가 높은 데이터:

- 체중 목표별 칼로리/매크로 설정 원칙
- 단백질 섭취 기준과 식품 선택 기준
- 점진적 과부하 원칙
- 근비대/근력/다이어트 목적별 세트/반복 범위
- 주요 근육군과 운동 매핑
- 운동 통증, 과훈련, 휴식, 부상 예방 기준
- 한국 사용자가 구하기 쉬운 식품/식단 예시

우선순위가 낮거나 제외할 데이터:

- 질병 치료 프로토콜
- 약물/보충제 복용 지시
- 극단적 식단, 단기 감량, 위험한 운동 루틴
- 출처가 불명확한 칼로리/영양 정보

### 6-2. 정제 규칙

- 문서 제목은 검색 결과에서 근거로 노출될 수 있으므로 사람이 읽을 수 있게 작성한다.
- 본문은 하나의 주제만 다룬다.
- 광고 문구, 작성자 소개, 댓글, CTA는 제거한다.
- 표는 문장형 규칙 또는 key-value 구조로 변환한다.
- 수치 기준은 단위와 조건을 함께 남긴다.
- "항상", "절대" 같은 과도한 표현은 출처에 근거가 있을 때만 사용한다.
- 한국어 답변 품질을 위해 최종 RAG content는 한국어로 저장하는 것을 기본으로 한다.

---

## 7. 권장 데이터 모델 v2

현재 `rag_documents`는 빠른 구현에는 적합하지만, 운영 관점에서는 원문, chunk, embedding, ingest 상태, retrieval trace가 분리되어야 한다. v2에서는 PostgreSQL 테이블이 운영 원장이며, OpenSearch는 이 데이터를 색인한 검색 전용 projection이다.

### 7-1. `rag_sources`

원문 문서 단위의 메타데이터를 관리한다.

| 컬럼 | 설명 |
|------|------|
| `id` | source PK |
| `title` | 원문 또는 내부 정리 문서 제목 |
| `source_type` | `guideline`, `paper`, `article`, `manual`, `internal_policy` |
| `source_url` | 원문 URL |
| `source_grade` | `A`, `B`, `C`, `D` |
| `license` | 사용 가능 범위 |
| `category` | 대표 category |
| `tags` | JSONB tag 목록 |
| `language` | `ko`, `en` 등 |
| `author_or_org` | 작성자 또는 기관 |
| `published_at` | 발행일 |
| `reviewed_at` | 내부 검토일 |
| `status` | `draft`, `active`, `archived`, `deleted` |
| `version` | source version |
| `content_hash` | 정제된 원문 hash |
| `metadata` | 기타 운영 메타데이터 |
| `created_at`, `updated_at` | 생성/수정 일시 |

### 7-2. `rag_chunks`

검색 가능한 chunk 단위 데이터다.

| 컬럼 | 설명 |
|------|------|
| `id` | chunk PK |
| `source_id` | `rag_sources.id` FK |
| `chunk_index` | source 내 순서 |
| `title` | 검색 결과에 표시할 chunk 제목 |
| `content` | chunk 본문 |
| `content_hash` | chunk 본문 hash |
| `category` | 검색 필터용 category |
| `tags` | JSONB tag 목록 |
| `embedding` | pgvector embedding |
| `embedding_model` | 예: `gemini-embedding-001` |
| `embedding_dim` | 예: `3072` |
| `opensearch_index` | 색인 대상 index 이름 |
| `opensearch_document_id` | 일반적으로 `rag_chunks.id` 문자열 |
| `indexed_at` | OpenSearch 마지막 색인 시각 |
| `index_status` | `pending`, `indexed`, `failed`, `deleted` |
| `token_count` | 추정 token 수 |
| `status` | `active`, `archived`, `deleted` |
| `version` | chunk version |
| `created_at`, `updated_at` | 생성/수정 일시 |

권장 인덱스:

- `(source_id, chunk_index)`
- `(category, status)`
- GIN index on `tags`
- vector index on `embedding`

### 7-3. `rag_ingest_jobs`

문서 추가/수정/재색인 작업의 상태를 기록한다.

| 컬럼 | 설명 |
|------|------|
| `id` | job PK |
| `job_type` | `create`, `update`, `archive`, `delete`, `reindex`, `backfill` |
| `source_id` | 대상 source |
| `status` | `pending`, `running`, `succeeded`, `failed`, `cancelled` |
| `requested_by` | 요청자 또는 system |
| `input_hash` | 입력 데이터 hash |
| `embedding_model` | 작업에 사용한 embedding model |
| `target_index` | OpenSearch 대상 index |
| `chunks_total` | 생성 대상 chunk 수 |
| `chunks_succeeded` | 성공 chunk 수 |
| `chunks_failed` | 실패 chunk 수 |
| `indexed_total` | OpenSearch 색인 대상 수 |
| `indexed_succeeded` | 색인 성공 수 |
| `indexed_failed` | 색인 실패 수 |
| `error_code` | 실패 코드 |
| `error_message` | 실패 상세 |
| `started_at`, `finished_at` | 처리 시간 |
| `created_at` | 생성 일시 |

### 7-4. `rag_retrieval_traces`

AI 답변 생성 시 어떤 chunk가 검색되었고 실제 prompt에 들어갔는지 기록한다.

| 컬럼 | 설명 |
|------|------|
| `id` | trace PK |
| `user_id` | 사용자 |
| `request_type` | `diet`, `exercise`, `chat`, `food_analysis` |
| `request_id` | 추천/채팅 등 상위 요청 id |
| `query_text` | 검색 query |
| `category_filter` | 적용된 category |
| `search_backend` | `opensearch`, `pgvector_fallback` |
| `search_mode` | `keyword`, `vector`, `hybrid` |
| `index_name` | 검색에 사용한 OpenSearch index |
| `index_version` | 검색 index version |
| `top_k` | 요청 top-k |
| `chunk_id` | 검색된 chunk |
| `source_id` | 검색된 source |
| `rank` | 검색 순위 |
| `score` | OpenSearch 최종 score |
| `similarity` | vector similarity가 제공될 경우 |
| `keyword_score` | keyword 점수가 제공될 경우 |
| `vector_score` | vector 점수가 제공될 경우 |
| `used_in_prompt` | 실제 prompt 포함 여부 |
| `embedding_model` | 검색 query embedding model |
| `created_at` | 생성 일시 |

### 7-5. `ai_generation_traces`

추천 결과와 LLM 호출의 운영 정보를 저장한다. 기존 `ai_recommendations`를 확장하거나 별도 trace 테이블을 둘 수 있다.

| 컬럼 | 설명 |
|------|------|
| `id` | trace PK |
| `user_id` | 사용자 |
| `recommendation_id` | 기존 `ai_recommendations.id` |
| `request_type` | `diet`, `exercise`, `chat` |
| `prompt_version` | prompt 템플릿 버전 |
| `model_used` | LLM 모델 |
| `rag_trace_group_id` | retrieval trace 묶음 |
| `input_context_hash` | 사용자 context hash |
| `output_hash` | AI 응답 hash |
| `latency_ms` | 호출 지연 시간 |
| `tokens_input`, `tokens_output` | 가능할 경우 기록 |
| `finish_reason` | 모델 응답 종료 사유 |
| `error_code` | 실패 코드 |
| `created_at` | 생성 일시 |

### 7-6. OpenSearch `rag_chunks` index

OpenSearch index는 PostgreSQL `rag_chunks`의 검색 projection이다.

권장 index 이름:

```text
rag_chunks_v1
rag_chunks_current -> rag_chunks_v1
```

`rag_chunks_current`는 read alias다. 재색인 시 `rag_chunks_v2`를 만든 뒤 evaluation을 통과하면 alias만 전환한다.

권장 문서 구조:

| 필드 | 타입 | 설명 |
|------|------|------|
| `chunk_id` | keyword | PostgreSQL `rag_chunks.id` |
| `source_id` | keyword | PostgreSQL `rag_sources.id` |
| `title` | text + keyword | chunk 제목 |
| `content` | text | 검색 대상 본문 |
| `category` | keyword | category 필터 |
| `tags` | keyword[] | tag 필터 |
| `source_grade` | keyword | 출처 신뢰도 |
| `status` | keyword | `active`만 검색 기본 대상 |
| `language` | keyword | `ko`, `en` |
| `source_url` | keyword | 출처 URL |
| `source_title` | text + keyword | source 제목 |
| `content_hash` | keyword | chunk hash |
| `source_version` | integer | source version |
| `chunk_version` | integer | chunk version |
| `embedding_model` | keyword | embedding model |
| `embedding_dim` | integer | embedding dimension, 현재 `3072` |
| `embedding` | knn_vector | `dimension=3072`, `hnsw`, `cosinesimil` |
| `indexed_at` | date | 색인 시각 |

검색 기본 조건:

```json
{
  "bool": {
    "filter": [
      { "term": { "status": "active" } },
      { "terms": { "category": ["nutrition", "goal_strategy"] } }
    ]
  }
}
```

OpenSearch index는 재생성 가능해야 한다. 따라서 원본 content와 운영 상태는 PostgreSQL을 기준으로 삼고, OpenSearch에는 검색에 필요한 projection만 둔다.

---

## 8. Chunking 정책

기본 chunking 정책:

| 항목 | 기준 |
|------|------|
| 기본 크기 | 500~1000자 |
| 최소 크기 | 80자 미만은 인접 chunk와 병합 |
| 최대 크기 | 1200자 초과 시 문장 단위 분할 |
| 경계 | 제목, 소제목, 목록, 표의 의미 단위 유지 |
| overlap | 기본 0, 개념 연결이 중요한 문서는 100~150자 허용 |
| 단위 | 하나의 chunk는 하나의 주장 또는 가이드만 담는 것을 목표 |

chunk 품질 기준:

- chunk만 읽어도 핵심 의미가 이해되어야 한다.
- 출처 제목 없이도 "무엇에 대한 지식인지" 드러나야 한다.
- 수치가 있는 경우 조건과 단위를 포함해야 한다.
- 서로 반대되는 목표의 지식을 한 chunk에 섞지 않는다.
  예: 벌크업 칼로리 잉여와 다이어트 칼로리 결손을 같은 chunk에 섞지 않는다.

---

## 9. Embedding과 Reindex 정책

현재 기준 embedding model은 `gemini-embedding-001`, dimension은 `3072`이다.

운영 원칙:

- 모든 chunk는 `embedding_model`, `embedding_dim`, `content_hash`를 가진다.
- 동일한 `content_hash`와 `embedding_model` 조합은 중복 embedding을 생성하지 않는다.
- source 수정으로 chunk content hash가 바뀌면 해당 chunk만 재임베딩한다.
- embedding model이 변경되면 전체 active chunk에 대해 PostgreSQL embedding 재생성과 OpenSearch reindex job을 실행한다.
- reindex 중에는 기존 OpenSearch index를 유지하고, 새 index가 준비된 뒤 read alias를 전환한다.
- 실패한 chunk는 job 상태에 실패 사유를 남기고 재시도 가능해야 한다.
- OpenSearch 색인 실패는 chunk 생성 실패와 분리해서 기록한다.
- OpenSearch가 일시 장애일 때도 PostgreSQL 저장은 commit할 수 있으며, `index_status=pending`으로 후속 재시도를 보장한다.

embedding model 변경 절차:

1. 새 embedding model을 설정에 추가한다.
2. 새 OpenSearch index 이름을 준비한다. 예: `rag_chunks_v2`
3. `rag_ingest_jobs`에 `reindex` job을 생성한다.
4. active chunk 전체에 새 embedding을 생성한다.
5. 새 index에 전체 chunk를 색인한다.
6. 샘플 query evaluation을 실행한다.
7. 검색 결과 품질이 기준을 통과하면 OpenSearch read alias를 새 index로 전환한다.
8. 이전 embedding/index는 일정 기간 보관 후 archive한다.

---

## 10. 문서 추가, 수정, 삭제 정책

### 10-1. 추가

문서 추가는 아래 단계를 따른다.

1. source 메타데이터 등록
2. 출처 등급과 라이선스 확인
3. 원문 정제
4. category/tag 지정
5. chunk 생성
6. embedding 생성
7. PostgreSQL chunk 저장
8. OpenSearch 색인
9. active 전환
10. ingest job 결과 기록

추가 작업은 idempotent 해야 한다. 같은 source URL과 content hash가 이미 active 상태라면 중복 등록하지 않는다.

### 10-2. 수정

문서 수정은 기존 데이터를 덮어쓰지 않는다.

정책:

- `rag_sources.version`을 증가시킨다.
- 기존 chunk는 `archived` 처리한다.
- 기존 chunk의 OpenSearch 문서는 삭제하거나 `status=archived`로 업데이트한다.
- 새 content hash 기준으로 chunk를 다시 생성한다.
- 변경되지 않은 chunk는 embedding을 재사용할 수 있다.
- 새 chunk는 OpenSearch에 새 document id로 색인한다.
- 과거 AI 추천이 참조한 source/chunk 정보는 유지한다.

이유:

- 과거 답변의 근거를 나중에 재현할 수 있어야 한다.
- 잘못된 답변이 발생했을 때 어떤 버전의 지식이 원인이었는지 추적해야 한다.

### 10-3. 삭제

기본 삭제는 hard delete가 아니라 soft delete다.

| 상황 | 처리 |
|------|------|
| 단순 노출 중단 | `archived` |
| 잘못된 내용 발견 | `archived` + reason 기록 |
| 법적/저작권 문제 | `deleted` + 본문 제거 + 메타데이터 최소 보존 |
| 테스트 데이터 정리 | 참조 이력이 없을 때만 hard delete 허용 |

삭제 시 고려 사항:

- 이미 생성된 추천 결과의 `rag_sources`는 보존한다.
- retrieval trace가 참조하는 chunk는 FK 무결성을 깨지 않는다.
- 본문 삭제가 필요한 경우 chunk content는 비우고 hash/source metadata만 남긴다.
- OpenSearch에서는 삭제된 chunk가 검색되지 않도록 즉시 delete 또는 `status=deleted` 업데이트를 수행한다.

### 10-4. 동기화와 장애 처리

PostgreSQL commit과 OpenSearch 색인은 서로 다른 저장소에 대한 작업이므로 장애 경계를 명확히 둔다.

권장 방식:

```text
1. PostgreSQL transaction
   - rag_sources/rag_chunks/rag_ingest_jobs 저장
   - chunk index_status=pending

2. OpenSearch indexing
   - 성공 시 index_status=indexed, indexed_at 기록
   - 실패 시 index_status=failed, job error 기록

3. Retry worker
   - failed/pending chunk를 재색인
```

중요 원칙:

- OpenSearch 색인 실패 때문에 source/chunk 원장 데이터를 잃으면 안 된다.
- 검색 read path는 `index_status=indexed` chunk만 신뢰한다.
- OpenSearch 결과가 PostgreSQL에서 조회되지 않으면 stale index로 보고 trace에 기록한 뒤 제외한다.
- stale index 문서는 후속 cleanup job으로 삭제한다.

---

## 11. Retrieval 정책

검색은 "사용자 질문" 그대로만 수행하지 않는다. 기능별로 사용자 상황을 반영한 검색 query를 만든다.

검색 backend 우선순위:

1. OpenSearch hybrid search
2. OpenSearch vector search
3. OpenSearch keyword search
4. PostgreSQL/pgvector fallback

OpenSearch hybrid search는 keyword relevance와 vector similarity를 함께 사용한다. 정확한 weight는 evaluation 결과로 조정한다.

권장 초기값:

| Score | Weight |
|-------|--------|
| keyword score | 0.35 |
| vector score | 0.65 |

### 11-1. 식단 추천 query

입력:

- 사용자 목표
- 남은 칼로리
- 부족한 매크로
- 알레르기
- 선호 식품

예시:

```text
다이어트 목표, 단백질 부족, 한국 식단, 저지방 식사 추천
```

기본 필터:

- `category = nutrition`
- 필요 시 `goal_strategy`, `safety` 추가 검색

### 11-2. 운동 추천 query

입력:

- 사용자 목표
- 근육군
- 최근 3회 운동 기록
- 최근 중량/반복 변화

예시:

```text
벌크업 목표, chest 근육군, 벤치프레스 점진적 과부하, 근비대 반복 범위
```

기본 필터:

- `category = exercise`
- 필요 시 `anatomy`, `safety` 추가 검색

### 11-3. 채팅 query

채팅은 질문 의도를 먼저 분류한다.

| 질문 의도 | 검색 category |
|-----------|---------------|
| 식단/음식 | `nutrition` |
| 운동 루틴 | `exercise` |
| 통증/부상 | `safety`, `anatomy` |
| 목표 전략 | `goal_strategy` |
| 앱 사용/정책 | `app_policy` |

통증, 질병, 약물, 진단 관련 질문은 안전 정책 chunk를 우선 포함한다.

---

## 12. AI 답변 생성 규칙

LLM prompt에는 다음 정보가 분리되어 들어가야 한다.

| 입력 블록 | 내용 |
|-----------|------|
| System/role | AI 헬스 코치 역할, 의료 진단 금지, 한국어 답변 |
| User context | 프로필, 목표, 알레르기, 선호 식품 |
| User logs | 식단/운동/체중 기록 요약 |
| RAG context | 검색된 chunk 제목, 본문, source |
| Output schema | JSON 응답 형식 |
| Safety rules | 위험 질문 fallback, 전문가 상담 안내 |

응답 원칙:

- 사용자의 실제 기록을 우선 반영한다.
- RAG 문서와 충돌하는 추천은 하지 않는다.
- RAG context가 부족하면 "근거 부족" 상태를 내부적으로 기록하고 보수적으로 답한다.
- 칼로리, 매크로, 세트, 반복, 중량처럼 실행 가능한 수치를 포함한다.
- 의료 진단처럼 보일 수 있는 표현은 피한다.
- 추천 결과에는 사용한 source title을 포함한다.

응답 저장 시 필수 기록:

- request type
- user context summary
- prompt version
- model used
- retrieved chunk ids
- source titles
- similarity scores
- OpenSearch index name/version
- search backend/mode
- final answer
- latency/error 정보

---

## 13. 품질 평가 정책

RAG 품질은 "검색 품질"과 "생성 품질"을 분리해서 평가한다.

### 13-1. Retrieval evaluation

평가셋 예시:

| Query | 기대 category | 기대 tag |
|-------|---------------|----------|
| 다이어트 중 단백질이 부족할 때 저녁 추천 | `nutrition` | `protein`, `diet` |
| 벤치프레스 중량을 언제 올려야 하나 | `exercise` | `progressive_overload`, `strength` |
| 스쿼트할 때 무릎 통증이 있으면? | `safety` | `pain`, `injury_prevention` |
| 벌크업 칼로리는 얼마나 늘려야 하나 | `goal_strategy` | `bulk`, `calorie_surplus` |

지표:

- top-1 category match
- top-3 expected source 포함 여부
- 평균 similarity
- hybrid score 분포
- stale index hit 비율
- PostgreSQL fallback 발생 비율
- no-result 비율
- 안전 질문에서 safety 문서 포함 여부

### 13-2. Generation evaluation

평가 기준:

- 사용자 기록 반영 여부
- RAG 근거 반영 여부
- 수치의 현실성
- 알레르기/선호 식품 준수
- 운동 목표별 세트/반복 적합성
- 의료 진단/과장 표현 회피
- JSON schema 준수

회귀 테스트:

- 주요 prompt와 샘플 사용자 context를 고정한다.
- RAG 데이터나 prompt 변경 시 동일 질문에 대한 결과를 비교한다.
- parse error, no-context, safety fallback 케이스를 테스트한다.

---

## 14. 운영 체크리스트

새 RAG 문서를 active 처리하기 전:

- [ ] 출처 URL 또는 내부 문서 위치가 기록되어 있는가
- [ ] source grade가 A/B 또는 승인된 C인가
- [ ] category와 tag가 지정되어 있는가
- [ ] 저작권/라이선스 문제가 없는가
- [ ] 의료 진단/치료 지시로 오해될 표현이 제거되었는가
- [ ] chunk가 하나의 주제를 담고 있는가
- [ ] 수치에는 단위와 조건이 포함되어 있는가
- [ ] embedding 생성이 성공했는가
- [ ] PostgreSQL chunk가 저장되었는가
- [ ] OpenSearch 색인이 성공했는가
- [ ] 샘플 query에서 OpenSearch 검색되는가

추천 답변 운영 점검:

- [ ] retrieval trace가 남는가
- [ ] source title이 응답에 포함되는가
- [ ] model/prompt version이 저장되는가
- [ ] search backend/mode/index version이 저장되는가
- [ ] OpenSearch 장애 시 fallback 또는 degraded trace가 남는가
- [ ] parse 실패가 error code로 분리되는가
- [ ] 안전 질문에 fallback이 적용되는가
- [ ] 사용자별 호출 제한과 timeout이 동작하는가

---

## 15. 현재 구현과 다음 단계

### 현재 구현

- `backend/app/models/rag.py`
  - `rag_sources`, `rag_chunks`, `rag_ingest_jobs`, `rag_retrieval_traces`, `ai_generation_traces`
  - `rag_chunks.embedding`은 pgvector `Vector(3072)`

- `backend/app/services/rag_index_service.py`
  - OpenSearch `rag_chunks_v1` index mapping
  - `rag_chunks_current` alias 생성
  - chunk 색인/삭제와 keyword/vector search

- `backend/app/services/rag_service.py`
  - 문서 chunking, Gemini embedding 생성, source/chunk 저장
  - OpenSearch hybrid retrieval 기본 경로
  - PostgreSQL/pgvector fallback
  - retrieval trace 저장

- `backend/app/cli/rag.py`
  - `ensure-index`, `delete-index`, `ingest`, `reindex`, `archive`, `evaluate`

- `backend/app/services/rag_evaluation.py`, `backend/rag_eval/retrieval_cases.json`
  - retrieval evaluation case loading, top-k result scoring, category/tag/source keyword match summary

- `backend/app/services/recommendation_service.py`, `backend/app/services/chat_service.py`
  - 식단 추천, 운동 추천, AI 채팅이 v2 RAG 검색 경로 사용
  - AI 생성 후 generation trace 저장

- legacy `rag_documents` 테이블과 `RagDocument` 모델은 v2 전환으로 제거되었다.

### 다음 구현 우선순위

1. `docs/RAG_ADVANCED_PORTFOLIO_ROADMAP.md` 기준으로 고급 RAG/AI 백엔드 포트폴리오 backlog를 계속 추적한다.
2. `docs/RAG_DECISION_POLICY.md` 기준으로 상황별 refresh/reindex/fallback 의사결정을 trace로 남긴다.
3. `docs/RAG_PIPELINE_ARCHITECTURE.md` 기준으로 RAG Pipeline Control Plane을 구현한다.
4. 문서/PDF vertical slice를 먼저 완성한다: source registry, parser/chunker, refresh CLI, reindex, evaluation report.
5. OpenSearch E2E ingest/evaluate를 실행하고 `docs/RAG_EVALUATION_REPORT.md`로 결과를 남긴다.
6. trace/debug CLI 또는 Admin API를 추가해 AI 답변의 source/chunk/model/prompt 근거를 조회할 수 있게 한다.
7. 이후 URL/API connector, scheduler/worker, image OCR/vision, video transcript/timestamp RAG로 확장한다.

---

## 16. 설계 원칙 요약

- RAG 데이터는 "문서"가 아니라 운영되는 지식 자산이다.
- PostgreSQL은 source of truth, OpenSearch는 retrieval index로 분리한다.
- 원문, chunk, embedding, index status, 검색 trace, 생성 trace를 분리한다.
- 삭제보다 archive를 기본으로 하여 과거 답변의 근거를 보존한다.
- embedding model, prompt version, source version을 기록해 재현성을 확보한다.
- OpenSearch index는 언제든 PostgreSQL 원장으로부터 재생성 가능해야 한다.
- OpenSearch 장애나 stale index는 trace에 남기고 fallback 정책으로 처리한다.
- AI 답변은 사용자 기록과 RAG 근거를 함께 사용해야 하며, 둘 중 하나가 부족하면 보수적으로 답한다.
- 건강/운동 코칭은 생활 습관 안내 범위로 제한하고, 의료 판단은 전문가 상담으로 연결한다.
