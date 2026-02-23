# AI Health Trainer — 설계자 인수인계 문서

> **이 문서의 목적:** 설계자 역할(Opus 4.6 → Gemini 3.1 Pro 등)이 교체되어도 프로젝트의 모든 컨텍스트를 100% 이해하고 이어서 작업할 수 있게 하는 인수인계 문서.
> 
> **마지막 업데이트:** 2026-02-23  
> **작성자:** Claude Opus 4.6 (Phase 1~3 설계자)

---

## 1. 프로젝트 현황 요약

**AI Health Trainer**는 개인 맞춤형 건강/피트니스 AI 코칭 앱이다.

| Phase | 내용 | 상태 | 테스트 |
|-------|------|------|--------|
| Phase 1 | 인프라 + 인증 + 프로필 | ✅ 완료 | 13개 PASS |
| Phase 2 | 식단/운동 CRUD + 대시보드 | ✅ 완료 | 20개 PASS |
| Phase 3 | AI 서비스 + RAG + 추천 + 채팅 | ✅ 완료 | 21개 PASS |
| Phase 4 | Flutter 프론트엔드 | ❌ 미착수 | — |
| Phase 5 | 배포 (CI/CD, 클라우드) | ❌ 미착수 | — |

**총 테스트: 54개 전체 통과 (exit code: 0)**

---

## 2. 역할 분담

| 역할 | 담당 | 업무 |
|------|------|------|
| **설계자** | Opus 4.6 → Gemini 3.1 Pro | 설계, 검증, 프롬프트 작성, 코드 리뷰 |
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
1. Flutter 프로젝트 초기화 (`frontend/`)
2. 공통 모듈 구현 (API 클라이언트, 테마, 라우팅, Riverpod 설정)
3. 인증 플로우 (로그인/회원가입 화면 + JWT 관리)
4. 프로필 설정 화면
5. 대시보드 (홈 화면)
6. 식단 기록 + AI 사진 분석
7. 운동 기록
8. AI 채팅 화면
9. AI 추천 화면

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
| Flutter 프론트엔드 | ❌ Phase 4 | 다음 작업 |
| CI/CD (GitHub Actions) | ❌ Phase 5 | 배포 시 |
| 운영 환경 분리 (.env.production 등) | ❌ Phase 5 | 배포 시 |
| 프로덕션 Dockerfile (멀티스테이지) | ❌ Phase 5 | 배포 시 |
| Nginx 리버스 프록시 | ❌ Phase 5 | 배포 시 |
| DEVELOPMENT_GUIDE.md | ❌ 미작성 | 낮음 |
| FLUTTER_UI_DESIGN.md | ❌ Phase 4에서 작성 | 다음 작업 |

---

## 10. 설계자 교체 시 첫 번째 할 일

1. **이 문서(HANDOFF.md)** 전체 읽기
2. **AGENTS.md** 읽기 (Codex 가이드 + 기술 스택 상세)
3. **PROJECT_OVERVIEW.md** 읽기 (전체 설계 맥락)
4. Phase 4 implementation_plan 작성 → 사용자 승인 → Codex 프롬프트 작성
