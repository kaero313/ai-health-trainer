# AI Health Trainer — 설계자 인수인계 문서

> **이 문서의 목적:** 설계자 역할(Opus 4.6 → Gemini 3.1 Pro 등)이 교체되어도 프로젝트의 모든 컨텍스트를 100% 이해하고 이어서 작업할 수 있게 하는 인수인계 문서.
> 
> **마지막 업데이트:** 2026-03-07  
> **작성자:** Claude Opus 4.6 (Phase 1~3) → Gemini 3.1 Pro (Phase 4 설계자)

---

## 1. 프로젝트 현황 요약

**AI Health Trainer**는 개인 맞춤형 건강/피트니스 AI 코칭 앱이다.

| Phase | 내용 | 상태 | 테스트 |
|-------|------|------|--------|
| Phase 1 | 인프라 + 인증 + 프로필 | ✅ 완료 | 13개 PASS |
| Phase 2 | 식단/운동 CRUD + 대시보드 | ✅ 완료 | 20개 PASS |
| Phase 3 | AI 서비스 + RAG + 추천 + 채팅 | ✅ 완료 | 21개 PASS |
| Phase 4 | Flutter 프론트엔드 | 🏃 진행 중 | 4-4B 완료, 4-4C 남음 |
| Phase 5 | 배포 (CI/CD, 클라우드) | ❌ 미착수 | — |

**총 테스트: 54개 전체 통과 (exit code: 0)**

---

## 2. 역할 분담

| 역할 | 담당 | 업무 |
|------|------|------|
| **설계자** | Gemini 3.1 Pro (Antigravity) | 설계, 검증, 프롬프트 작성, 코드 리뷰 |
| **구현자** | Codex | 설계 문서/프롬프트 기반 코드 생성 |
| **사용자** | 프로젝트 오너 | 방향 결정, 승인 |

---

## 3. Phase별 상세 이력

### Phase 1: 인프라 + 인증 + 프로필
- Docker Compose 구성 (PostgreSQL pgvector, Redis, Backend)
- 회원가입/로그인/토큰갱신 API
- 프로필 CRUD + TDEE 자동 계산
- Alembic 마이그레이션 초기 스키마

### Phase 2: CRUD + 대시보드
- 식단 기록 CRUD (DietLog + DietLogItem)
- 운동 기록 CRUD (ExerciseLog + ExerciseSet)
- 대시보드 (오늘 현황, 주간 요약, 연속기록 streak)
- Codex 프롬프트 4개로 구현

### Phase 3: AI 통합
- AIService (Gemini LLM Gateway) — `generate_content_async`, 3단계 JSON 폴백, 7가지 에러 매핑
- RAGService (pgvector 벡터 검색) — `gemini-embedding-001` (3072차원)
- RecommendationService (식단/운동 추천 파이프라인)
- ChatService (AI 코칭 채팅 — context_type별 데이터 수집)
- RAG 인제스트 CLI + 7개 문서 인제스트 완료 (10청크)
- Codex 프롬프트 7개(1a, 1b, 2~7)로 구현

#### Phase 3 검증 중 발견된 버그 및 수정 (교훈)
| 버그 | 원인 | 수정 |
|------|------|------|
| 테스트 DB 연결 실패 | conftest.py 기본값 `localhost`, Docker 내부는 `db` | 환경변수로 오버라이드 |
| RAG exercise 검색 불가 | ingest CLI가 `exercise_science`로 저장, API는 `exercise`로 검색 | `exercise_science` → `exercise` |
| FoodAnalysis Pydantic 에러 | AI가 `total` 미반환, 스키마는 필수 | 엔드포인트에서 total 자동 계산 |
| 임베딩 모델 404 | `text-embedding-004` 지원 중단 | `gemini-embedding-001`로 변경 |
| Vector 차원 불일치 | `gemini-embedding-001`은 3072차원, 모델은 768 | 768 → 3072로 수정 |
| rag_documents 마이그레이션 누락 | 초기 마이그레이션에 미포함 | 별도 마이그레이션 생성 |

---

## 4. Phase 4 설계 방향 (합의된 사항)

사용자와 합의된 Phase 4 방향:

| 항목 | 결정 |
|------|------|
| **플랫폼** | 모바일 우선 (iOS/Android) |
| **상태관리** | Riverpod |
| **디자인** | Material 3 + 다크모드 기본+그린/블루 액센트 |
| **진행 방식** | 하이브리드 — 설계자가 기반 구축 + Codex가 화면 구현 |

### 예상 화면 구성
| 화면 | 설명 |
|------|------|
| 로그인/회원가입 | 인증 플로우 |
| 프로필 설정 | 키/몸무게/목표 입력 |
| 대시보드 (홈) | 오늘 현황 (영양/운동/스트릭) |
| 식단 기록 | 수동 입력 + AI 사진 분석 (카메라) |
| 운동 기록 | 운동/세트/반복 입력 |
| AI 채팅 | 실시간 코칭 채팅 |
| 식단/운동 추천 | AI 추천 결과 표시 |

### Phase 4 TODO
1. ✅ Flutter 프로젝트 초기화 (`frontend/`)
2. ✅ 공통 모듈 구현 (API 클라이언트, 테마, 라우팅, Riverpod 설정)
3. ✅ 인증 플로우 (로그인/회원가입 화면 + JWT 관리)
4. ✅ 프로필 설정/편집 화면
5. ✅ 대시보드 (CalorieRing 카운트업 + NutrientBar 애니메이션)
6. ✅ 식단 기록 (CRUD + 스와이프 삭제 + 수동 추가)
7. ✅ 운동 기록 (CRUD + 세트 확장 + 수동 추가)
8. ✅ AI 사진 분석 (image_picker + multipart 업로드)
9. ✅ AI 식단/운동 추천 (추천 카드 + RAG 출처 + 일괄 저장)
10. ✅ AI 코칭 채팅 (context_type 칩 + 타이핑 인디케이터)
11. ✅ FAB 바텀시트 (4개 빠른 액션) + 화면 전환 애니메이션
12. 🏃 flutter analyze 0건 + 대시보드 AI 코칭 카드 (4-4C)

---

## 5. Codex 프롬프트 작성 패턴 (검증된 방법)

Phase 2~3에서 효과가 입증된 프롬프트 작성법:

### 구조
```
Phase X-N: [작업 제목]

## 참조 문서
- 구체적 문서명과 섹션 번호

## ⚠️ 핵심 규칙 (함정 방지)
- 반드시 지켜야 할 코드 패턴 (예시 코드 포함)
- "잘못됨" 예시와 "올바름" 예시 병렬 제시

## 구현 대상
- 파일별 상세 명세 (클래스, 메서드 시그니처, 핵심 로직)
- └ 단순 의사코드 + 주석으로 구현 흐름 안내

## 커밋
- git add / commit 명령어 그대로 제시
- "주의: backend/.env 파일은 절대 stage하지 마."
```

### 핵심 교훈
1. **⚠️ 표시로 함정 강조** — Codex가 자주 틀리는 부분을 명시적으로 경고
2. **코드 예시 필수** — 설명만으로는 부족, ✅/❌ 예시 병렬 제시
3. **프롬프트 분할** — 한 프롬프트에 너무 많으면 품질 저하. 1 프롬프트 = 1~2 파일 원칙
4. **순서 의존성** — 프롬프트 간 의존성 명시 (예: "프롬프트 1b에서 생성한 ai_service.py 참조")
5. **커밋 명령어 포함** — Codex가 커밋까지 수행하도록 정확한 명령어 제시
6. **.env 경고 필수** — 매 프롬프트마다 ".env 파일 stage 금지" 넣어야 함

### Phase 3에서 특히 효과적이었던 패턴
- `asyncio.to_thread` 패턴을 코드 블록으로 명시 → 100% 올바르게 구현됨
- pgvector SQL 쿼리 패턴(`<=>`, `::vector`)을 그대로 제시 → 정확히 복사
- AIServiceError 에러 매핑 테이블 → 7가지 모두 정확하게 구현

---

## 6. 테스트 실행 방법

```bash
# Docker 내부에서 실행 (DB 환경변수 필수)
docker compose exec \
  -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/health_trainer_test \
  -e TEST_DATABASE_ADMIN_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres \
  backend pytest tests/ -v --tb=short
```

**주의:** `conftest.py`의 기본 DB URL이 `localhost`이므로 Docker 내부에서는 반드시 위 환경변수를 지정해야 한다.

---

## 7. 주요 참조 문서 맵

| 문서 | 위치 | 내용 |
|------|------|------|
| **AGENTS.md** | 프로젝트 루트 | Codex용 종합 가이드 (구조, 코딩 규칙, API 목록) |
| PROJECT_OVERVIEW.md | `docs/` | 프로젝트 전체 설계, 기술 스택, 역할 분담 |
| DATABASE_SCHEMA.md | `docs/` | DB 스키마 상세, TDEE 계산 공식 |
| API_SPECIFICATION.md | `docs/` | RESTful API 전체 명세 (20개 엔드포인트) |
| AI_RAG_STRATEGY.md | `docs/` | AI 프롬프트, RAG 전략, 안전 설정 |
| COMMIT_CONVENTION.md | 프로젝트 루트 | 커밋 메시지 규칙 |

---

## 8. Git 커밋 이력 (Phase 3)

| 커밋 | 내용 |
|------|------|
| Phase 3 Codex 커밋 7개 | AI 서비스, RAG, 추천, 채팅, 테스트 구현 |
| `d45cccd` | 카테고리 버그, FoodAnalysis total, API 문서 수정 |
| `969f232` | 임베딩 모델 변경, Vector 차원 수정, RAG 인제스트 |

---

## 9. 아직 미구현/미설정 항목

| 항목 | 상태 | 우선순위 |
|------|------|----------|
| Phase 4-4C (lint 수정 + AI 카드) | 🏃 프롬프트 준비 완료 | **최우선** |
| flutter analyze 0건 달성 | 🏃 현재 2건 남음 | 4-4C에 포함 |
| 대시보드 AI 코칭 카드 | ❌ 미추가 | 4-4C에 포함 |
| CI/CD 및 운영 환경 분리 | ❌ Phase 5 | 배포 시 |
| Nginx 리버스 프록시 / 멀티스테이지 Dockerfile | ❌ Phase 5 | 배포 시 |
| DEVELOPMENT_GUIDE.md | ❌ 미작성 | 낮음 |
---

## 10. 설계자 교체 시 첫 번째 할 일

1. **이 문서(HANDOFF.md)** 전체 읽기
2. **AGENTS.md** 읽기 (Codex 가이드 + 기술 스택 상세)
3. **FLUTTER_UI_DESIGN.md** 읽기 (UI 설계 맥락)
4. **현재 상황**: Phase 4-4B까지 완료. 남은 작업은 **4-4C(lint 2건 수정 + AI 코칭 카드)** 1개뿐.
5. **다음 행동**: 4-4C 프롬프트를 Codex에 전달 → 검증 → Phase 4 완료 → Phase 5(배포) 시작.
6. **프롬프트 위치**: 모든 Phase 4 프롬프트는 `antigravity/brain/` 아티팩트 디렉토리에 저장됨.
7. **멀티 에이전트 사용 시**: 아래 11~12장의 운영 규칙과 템플릿을 그대로 재사용한다.

---

## 11. Codex 멀티 에이전트 운영 모델

이 프로젝트의 멀티 에이전트는 **설계자/오케스트레이터가 메인 Codex를 조종하고, 하위 에이전트는 짧고 좁은 책임만 맡는 구조**를 뜻한다.

### 권장 토폴로지

- 메인 Codex: 요구사항 해석, critical path 처리, 하위 에이전트 spawn, 결과 통합, 최종 검증
- `explorer`: 코드베이스 탐색 전용
- `worker`: 구현 전용
- `reviewer` 리뷰 에이전트: findings-first 리뷰 전용

### 기본 라우팅 규칙

- 작은 작업: 메인 Codex 단독 또는 `explorer` 1개
- 단일 도메인 작업: `explorer` 1 + `worker` 1 + 리뷰 에이전트 1
- 백엔드/프론트 동시 작업: backend `worker` 1 + frontend `worker` 1 + 리뷰 에이전트 1
- 같은 파일 또는 같은 모듈 ownership은 둘 이상의 `worker`에 주지 않는다.
- 프로젝트 제한값은 `agents.max_threads = 4`, `agents.max_depth = 1`로 두고, 일반 작업에서는 2~3개 병렬을 권장한다.

### 메인 Codex 표준 실행 순서

1. 요청을 읽고 critical path를 메인 Codex가 먼저 판단한다.
2. 바로 막는 작업은 직접 처리하고, 병렬 가능한 탐색/검증만 위임한다.
3. `spawn_agent`로 역할별 하위 에이전트를 띄운다.
4. 필요 시 `send_input`으로 추가 지시를 보낸다.
5. 당장 필요한 순간에만 `wait_agent`를 호출한다.
6. 통합이 끝나면 `close_agent`로 정리한다.

### 하위 에이전트 공통 규칙

- 너는 혼자 작업하지 않는다.
- 다른 사람이 만든 변경을 revert 하지 않는다.
- 지정된 write scope 밖은 수정하지 않는다.
- 결과는 요약이 아니라 **다음 액션에 필요한 정보** 중심으로 반환한다.

### 실제 운영 파일

- 프로젝트 subagent 설정: `.codex/config.toml`
- 역할 정의: `.codex/agents/explorer.toml`, `.codex/agents/worker.toml`, `.codex/agents/reviewer.toml`
- HITL Gate 1 템플릿: `.agent/workflows/task-spec-template.md`
- HITL Gate 2 체크리스트: `.agent/workflows/review-gate-checklist.md`
- 프로젝트 제한값: `agents.max_threads = 4`, `agents.max_depth = 1`
- Ralph loop 자동화는 아직 넣지 않았고, 실제 작업 2~3개를 돌린 뒤 후속 단계로 추가한다.

---

## 12. 역할별 프롬프트 템플릿

아래 템플릿은 설계자나 메인 Codex가 그대로 복사해 하위 에이전트에 전달해도 된다.

### `explorer` 템플릿

```text
역할: explorer
목표: [한 문장으로 작업 목적]
질문: [탐색할 질문 1~2개]
조사 범위: [파일/디렉터리/도메인]

규칙:
- 읽기 전용으로 작업한다.
- 코드 수정, 포맷팅, 리팩터링 제안만 하고 실제 변경은 하지 않는다.
- 관련 없는 파일은 넓게 훑지 말고 필요한 곳만 본다.

반환 형식:
1. 관련 파일
2. 현재 동작 요약
3. 제약/리스크
4. 추천 구현 경로
```

### `worker` 템플릿

```text
역할: worker
목표: [구현할 결과]
소유 범위: [수정 가능한 파일/디렉터리]
금지 범위: [건드리면 안 되는 파일/영역]
완료 기준: [테스트/동작 기준]

규칙:
- 너는 혼자 작업하지 않는다.
- 다른 사람이 만든 수정은 revert 하지 않는다.
- 지정된 소유 범위 밖은 수정하지 않는다.
- 필요한 경우 기존 변경을 읽고 그 위에 맞춰 구현한다.

반환 형식:
- 변경 파일
- 구현 요약
- 실행한 검증
- 남은 리스크 또는 후속 작업
```

### 리뷰 에이전트(`reviewer`) 템플릿

```text
역할: reviewer
검토 대상: [PR/변경 요약 또는 파일 범위]
검토 초점: [버그, 회귀, 테스트 누락, API 일관성 등]

규칙:
- 리뷰 전용으로 작업한다.
- 변경 요약보다 findings를 먼저 제시한다.
- 심각도와 근거가 약한 추측은 피하고, 파일/라인 근거를 우선한다.

반환 형식:
1. Findings first
2. 심각도 순 정렬
3. 파일/라인 근거
4. 누락 테스트
5. 잔여 리스크
```

### 메인 Codex 작업 지시 템플릿

```text
작업 제목: [예: profile 버그 수정]
목표:
- [필수 결과 1]
- [필수 결과 2]

성공 기준:
- [사용자 관점 동작]
- [검증 명령 또는 테스트]

제약:
- [건드리면 안 되는 파일]
- [호환성/스타일/성능 제약]

권장 분업:
- explorer: [탐색 질문]
- worker: [구현 범위]
- reviewer: [확인할 리스크]
```
