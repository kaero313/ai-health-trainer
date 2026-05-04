# AI Health Trainer - Owner Guide

> **Audience:** 사용자 본인(개발자, 설계자, 운영자)
> **Purpose:** 제품 방향, 구현 현황, 개발/운영 방법을 한 문서에서 관리한다.
> **AI worker guide:** `AGENTS.md`
> **Last updated:** 2026-05-01

---

## 0. Document Map

| Document | Role |
|----------|------|
| `AGENTS.md` | AI 작업자용 실행 규칙 |
| `docs/OWNER_GUIDE.md` | 현재 상태와 의사결정의 기준 문서 |
| `docs/API_SPECIFICATION.md` | API 상세 명세와 요청/응답 예시 |
| `docs/DATABASE_SCHEMA.md` | DB 테이블/관계/계산식 상세 |
| `docs/AI_RAG_STRATEGY.md` | AI 프롬프트, Gemini/RAG 전략 |
| `docs/RAG_OPERATIONS.md` | RAG 지식 수집/정제/버전/OpenSearch 색인/삭제/추적 운영 정책 |
| `docs/RAG_ADVANCED_PORTFOLIO_ROADMAP.md` | 고급 RAG/AI 백엔드 포트폴리오 고도화 로드맵 |
| `docs/RAG_PIPELINE_ARCHITECTURE.md` | RAG source registry, parser/chunker, refresh/reindex 파이프라인 기준 |
| `docs/RAG_DECISION_POLICY.md` | RAG 변경 감지, 재임베딩, fallback 상황별 의사결정 정책 |
| `docs/RAG_CATALOG_CONTROL_PLANE.md` | 공식 URL catalog 변경 감지, plan/apply, section/chunk diff 운영 기준 |
| `docs/FLUTTER_UI_DESIGN.md` | Flutter 화면별 UI/UX 상세 설계 |
| `docs/DEPLOYMENT.md` | Docker/Nginx/배포 상세 |
| `docs/DEVELOPMENT_GUIDE.md` | 개발 컨벤션과 구현 순서 기록 |
| `docs/PROJECT_OVERVIEW.md` | 초기 프로젝트 개요와 역할 분담 |

세부 설계 문서는 기능 구현 근거로 유지한다. 최신 Phase 상태와 다음 의사결정은 이 문서를 우선한다.

---

## 1. Product Direction

AI Health Trainer는 사진 한 장과 운동/체중 기록을 바탕으로 현재 상태를 평가하고, 벌크/다이어트/유지 목표에 맞춘 다음 행동을 추천하는 개인 맞춤형 건강/피트니스 AI 코칭 앱이다.

목표:

- 모바일 우선 Flutter 앱
- Google Play Store 배포 가능한 포트폴리오 품질
- 실사용 가능한 식단/운동 기록 + AI 추천 경험
- 문서와 코드가 새 AI 세션에서도 바로 이어질 만큼 단순한 구조

현재 상태:

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | 인프라 + 인증 + 프로필 | 완료 |
| Phase 2 | 식단/운동 CRUD + 대시보드 | 완료 |
| Phase 3 | AI 서비스 + RAG + 추천 + 채팅 | 완료 |
| Phase 4 | Flutter 프론트엔드 전체 플로우 | 완료 |
| Phase 5 | 배포/운영 기반 | 완료 |
| Phase 6 | 월간 리포트, 체중 히스토리, 멀티 에이전트, OpenSearch compose | 완료 |

검증 기준:

- Backend tests: 64 PASS
- Flutter: `flutter analyze` 0 issues

다음 작업은 Phase 7 또는 릴리스 후보 작업으로 새로 정의한다.

---

## 2. Product Surface

구현된 사용자 기능:

- 인증: 회원가입, 로그인, JWT 갱신
- 프로필: 키, 몸무게, 나이, 성별, 목표, 활동량, 알레르기, 선호 식품
- 체중 히스토리: 날짜별 체중 기록과 월간 추이
- 식단: 날짜/식사 유형별 CRUD, 음식 항목 관리, 스와이프 삭제
- AI 음식 사진 분석: 이미지 업로드 후 영양소 추정
- 운동: 운동명, 근육군, 세트, 반복, 중량 기록
- 대시보드: 오늘 영양/운동 현황, 주간 요약, AI 코칭 카드
- 월간 리포트: 월간 영양/운동/체중 추이
- AI 추천: 식단/운동 추천, RAG 출처 표시, 일괄 저장
- AI 채팅: context type 기반 개인화 코칭

주요 화면:

- 온보딩
- 로그인/회원가입
- 프로필 설정/편집
- 대시보드
- 식단 목록/추가/사진 분석/추천
- 운동 목록/추가/추천
- AI 채팅
- 월간 리포트

---

## 3. Architecture

| Area | Stack |
|------|-------|
| Backend | Python 3.12, FastAPI, SQLAlchemy Async, Alembic |
| Frontend | Flutter, Riverpod, GoRouter, Dio |
| Database | PostgreSQL 17, pgvector |
| Cache | Redis |
| Search/Observability | OpenSearch 2.19.3 development service |
| AI | Gemini 2.5 Flash/Pro, `gemini-embedding-001` |
| Infra | Docker Compose, Nginx, GitHub Actions, backup script |

Runtime services:

- `db`: `pgvector/pgvector:pg17`
- `redis`: `redis:7-alpine`
- `opensearch`: `opensearchproject/opensearch:2.19.3`
- `backend`: FastAPI app

Backend structure:

```text
backend/app/
├── api/v1/        # FastAPI routers
├── core/          # config, database, security, deps
├── models/        # SQLAlchemy models
├── schemas/       # Pydantic schemas
├── services/      # business logic
└── main.py
```

Frontend structure:

```text
frontend/lib/
├── core/          # router, theme, network, storage
├── features/      # auth, profile, dashboard, diet, exercise, chat
└── main.dart
```

---

## 4. Data Contract

Core tables:

| Table | Purpose |
|-------|---------|
| `users` | 사용자 계정 |
| `user_profiles` | 신체/목표 프로필과 TDEE/목표 매크로 |
| `weight_logs` | 날짜별 체중 기록 |
| `diet_logs` | 식사 단위 식단 기록 |
| `diet_log_items` | 식단별 음식 항목 |
| `exercise_logs` | 운동 기록 헤더 |
| `exercise_sets` | 운동별 세트 상세 |
| `refresh_tokens` | JWT refresh token |
| `ai_recommendations` | AI 추천/코칭 기록 |
| `rag_sources` | RAG 지식 출처/버전/status 원장 |
| `rag_chunks` | RAG 검색 청크와 3072차원 embedding |
| `rag_ingest_jobs` | RAG ingest/reindex/archive 작업 이력 |
| `rag_catalog_plan_runs` | 공식 source catalog plan 실행 단위와 summary |
| `rag_catalog_plan_items` | source별 diff, planned action, apply 결과 |
| `rag_retrieval_traces` | AI 답변 생성 시 검색된 chunk trace |
| `ai_generation_traces` | prompt/model/source 기반 AI 생성 trace |

Important DB rules:

- `rag_chunks.embedding`은 `VECTOR(3072)`이다.
- OpenSearch `rag_chunks_current` alias가 기본 retrieval index다.
- embedding 모델은 `gemini-embedding-001`이다.
- `weight_logs`는 `(user_id, log_date)` unique index를 가진다.
- TDEE와 목표 칼로리/매크로는 서버에서 계산한다.

TDEE baseline:

```python
if gender == "male":
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
else:
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

target_protein_g = weight_kg * 1.8
target_fat_g = target_calories * 0.25 / 9
target_carbs_g = (target_calories - target_protein_g * 4 - target_fat_g * 9) / 4
```

---

## 5. API Contract

Base URL:

- Local backend: `http://localhost:8000/api/v1`
- Flutter web local: configured to call `http://localhost:8000/api/v1`
- Android emulator: configured to call `http://10.0.2.2:8000/api/v1`

Endpoints:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/register` | No | 회원가입 |
| POST | `/auth/login` | No | 로그인 |
| POST | `/auth/refresh` | No | access token 갱신 |
| GET | `/profile` | Yes | 프로필 조회 |
| PUT | `/profile` | Yes | 프로필 설정/수정 |
| GET | `/profile/check` | Yes | 프로필 존재 여부 |
| POST | `/profile/weight` | Yes | 체중 기록 추가/수정 |
| GET | `/profile/weight-history` | Yes | 체중 히스토리 |
| POST | `/diet/logs` | Yes | 식단 기록 추가 |
| GET | `/diet/logs` | Yes | 식단 기록 조회 |
| PUT | `/diet/logs/{id}` | Yes | 식단 기록 수정 |
| DELETE | `/diet/logs/{id}` | Yes | 식단 기록 삭제 |
| POST | `/diet/analyze-image` | Yes | 음식 사진 AI 분석 |
| GET | `/diet/recommend` | Yes | AI 식단 추천 |
| POST | `/exercise/logs` | Yes | 운동 기록 추가 |
| GET | `/exercise/logs` | Yes | 운동 기록 조회 |
| PUT | `/exercise/logs/{id}` | Yes | 운동 기록 수정 |
| DELETE | `/exercise/logs/{id}` | Yes | 운동 기록 삭제 |
| GET | `/exercise/history/{muscle}` | Yes | 근육군 히스토리 |
| GET | `/exercise/recommend` | Yes | AI 운동 추천 |
| GET | `/dashboard/today` | Yes | 오늘 현황 |
| GET | `/dashboard/weekly` | Yes | 주간 요약 |
| GET | `/dashboard/monthly` | Yes | 월간 리포트 |
| POST | `/ai/chat` | Yes | AI 코칭 채팅 |
| GET | `/health` | No | 앱/DB/Redis 헬스체크 |

Response shape:

```json
{"status": "success", "data": {}}
```

```json
{"status": "error", "error": {"code": "ERROR_CODE", "message": "..."}}
```

---

## 6. AI And RAG

Models:

| Use | Model |
|-----|-------|
| General generation | `gemini-3-flash-preview` |
| Advanced reasoning | `gemini-2.5-pro` |
| Embedding | `gemini-embedding-001` |

RAG data:

```text
backend/rag_data/
├── nutrition_basics.md
├── nutrition_bulking_guide.md
├── nutrition_cutting_guide.md
├── nutrition_korean_foods.md
├── nutrition_maintain_guide.md
├── nutrition_supplement_guide.md
├── exercise_lower_body.md
├── exercise_progressive_overload.md
└── exercise_upper_body.md
```

RAG management:

```bash
docker compose exec backend python scripts/reset_rag_data.py
docker compose exec backend python scripts/ingest_rag_data.py --dir rag_data/
docker compose exec backend python -m app.cli.rag catalog-plan --file rag_sources/catalog.json --report-path /workspace/docs/RAG_CATALOG_PLAN_REPORT.md
docker compose exec backend python -m app.cli.rag catalog-apply --run-id <run_id>
```

Known AI maintenance item:

- Gemini SDK uses `google.genai`.

---

## 7. Design Standard

Design direction:

- Mobile-first
- Dark mode default
- Material 3 tone
- Primary accent: vibrant green
- Secondary accents: blue/teal/yellow/orange for nutrition and state
- Dense but readable health dashboard, not a marketing landing page

Important UI rules:

- On-screen text is Korean.
- Components should match current theme files in `frontend/lib/core/theme/`.
- Dashboard and tools should be information-first.
- Use Browser Use side panel after UI changes.
- Avoid adding explanatory in-app text about features unless the screen naturally needs it.

Current visual language:

- Background: deep navy
- Surface cards: dark blue-gray
- Main action color: green
- Rounded cards/buttons consistent with existing Flutter theme

---

## 8. Development Workflow

Start local services:

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
```

Run Flutter web:

```bash
cd frontend
flutter run -d web-server --web-hostname 127.0.0.1 --web-port 3000
```

Backend tests:

```bash
docker compose exec \
  -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/health_trainer_test \
  -e TEST_DATABASE_ADMIN_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres \
  backend pytest tests/ -v --tb=short
```

Flutter analysis:

```bash
cd frontend
flutter analyze
```

Commit convention:

```text
<type>(<scope>): <description>
```

Examples:

- `feat(dashboard): add monthly report card`
- `fix(auth): remove local login defaults`
- `docs(project): update phase status`

---

## 9. Operations

Production deployment:

```bash
cp .env.example .env.prod
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

GitHub Actions:

- `ci.yml`: backend pytest + Flutter analyze
- `cd.yml`: CI success after main branch workflow triggers SSH deploy

Required GitHub secrets:

- `SSH_HOST`
- `SSH_USERNAME`
- `SSH_KEY`
- `SSH_PORT`

Backup:

```bash
bash scripts/backup.sh
```

Health:

- Local API docs: `http://localhost:8000/docs`
- Health endpoint: `GET /api/v1/health`
- Healthy response includes `status`, `version`, `db`, `redis`

---

## 10. Release Risks And Next Decisions

Before public release:

- Remove local testing login defaults from Flutter auth screen.
- Monitor Gemini 3 Flash Preview response quality and token usage.
- Confirm production `.env.prod` values and CORS origins.
- Validate Nginx HTTPS flow.
- Decide whether OpenSearch is only development tooling or part of production observability.
- Prepare Play Store assets, metadata, privacy policy, and test track.

Potential Phase 7 directions:

- Release candidate hardening
- Production observability/log ingestion
- AI response quality evaluation
- Better onboarding/profile UX
- Play Store deployment
