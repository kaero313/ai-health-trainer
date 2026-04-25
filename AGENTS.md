# AI Health Trainer — Codex Agent 가이드

> **이 문서의 목적:** Codex가 새 세션에서도 프로젝트를 완벽히 이해하고 일관된 코드를 생성할 수 있도록 하는 종합 참조 문서.

---

## 1. 프로젝트 개요

**AI Health Trainer**는 개인 맞춤형 건강/피트니스 코칭 앱이다.

| 항목 | 설명 |
|------|------|
| **백엔드** | Python FastAPI + PostgreSQL + Redis |
| **프론트엔드** | Flutter (Phase 4에서 구현 예정) |
| **AI** | Google Gemini API (2.5 Flash/Pro) |
| **RAG** | pgvector 기반 벡터 검색 |
| **컨테이너** | Docker Compose (db, redis, backend) |

### 핵심 기능
1. **인증**: 회원가입, 로그인, JWT 토큰 갱신
2. **프로필**: 신체정보, 목표, 알레르기, 식품선호도, TDEE 자동 계산
3. **식단 관리**: CRUD + AI 음식사진 분석 (Gemini Vision)
4. **운동 관리**: CRUD + 세트/반복 기록
5. **대시보드**: 오늘 현황, 주간 요약, 연속기록(streak)
6. **AI 추천**: RAG 기반 식단/운동 추천
7. **AI 채팅**: 개인화된 건강 코칭 대화

---

## 2. 디렉토리 구조

```
ai-health-trainer/
├── AGENTS.md                    # 이 파일
├── COMMIT_CONVENTION.md         # 커밋 컨벤션 가이드
├── docker-compose.yml           # Docker 서비스 (db, redis, backend)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env                     # 환경변수 (gitignore 대상)
│   │
│   ├── alembic/                 # DB 마이그레이션
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 265e405ccf13_initial_schema.py
│   │       └── 0e0918445906_add_rag_documents_table.py
│   │
│   ├── app/
│   │   ├── main.py              # FastAPI 앱 진입점
│   │   │
│   │   ├── core/
│   │   │   ├── config.py        # Settings (pydantic-settings)
│   │   │   ├── database.py      # 비동기 DB 엔진 + 세션
│   │   │   └── security.py      # JWT 생성/검증, get_current_user
│   │   │
│   │   ├── models/              # SQLAlchemy ORM 모델
│   │   │   ├── __init__.py      # 모든 모델 re-export
│   │   │   ├── user.py          # User, UserProfile, Enum들
│   │   │   ├── diet.py          # DietLog, DietLogItem
│   │   │   ├── exercise.py      # ExerciseLog, ExerciseSet
│   │   │   ├── token.py         # RefreshToken
│   │   │   ├── ai_recommendation.py  # AIRecommendation
│   │   │   └── rag_document.py  # RagDocument (pgvector)
│   │   │
│   │   ├── schemas/             # Pydantic 요청/응답 스키마
│   │   │   ├── ai.py            # AI 관련 (분석, 추천, 채팅)
│   │   │   ├── auth.py          # 인증 (회원가입, 로그인, 토큰)
│   │   │   ├── dashboard.py     # 대시보드
│   │   │   ├── diet.py          # 식단
│   │   │   ├── exercise.py      # 운동
│   │   │   └── profile.py       # 프로필
│   │   │
│   │   ├── api/v1/              # API 라우터
│   │   │   ├── router.py        # 통합 라우터 (모든 라우터 include)
│   │   │   ├── auth.py          # /api/v1/auth/*
│   │   │   ├── profile.py       # /api/v1/profile/*
│   │   │   ├── diet.py          # /api/v1/diet/*
│   │   │   ├── exercise.py      # /api/v1/exercise/*
│   │   │   ├── dashboard.py     # /api/v1/dashboard/*
│   │   │   └── ai_chat.py       # /api/v1/ai/*
│   │   │
│   │   └── services/            # 비즈니스 로직 서비스
│   │       ├── auth_service.py
│   │       ├── profile_service.py
│   │       ├── diet_service.py
│   │       ├── exercise_service.py
│   │       ├── dashboard_service.py
│   │       ├── ai_service.py         # Gemini API 래퍼
│   │       ├── rag_service.py        # 벡터 임베딩 + 검색
│   │       ├── recommendation_service.py  # 식단/운동 AI 추천
│   │       └── chat_service.py       # AI 채팅 컨텍스트 수집
│   │
│   ├── rag_data/                # RAG 원본 문서 (7개)
│   │   ├── nutrition_basics.md
│   │   ├── nutrition_bulking_guide.md
│   │   ├── nutrition_cutting_guide.md
│   │   ├── nutrition_maintain_guide.md
│   │   ├── exercise_upper_body.md
│   │   ├── exercise_lower_body.md
│   │   └── exercise_progressive_overload.md
│   │
│   ├── scripts/
│   │   └── ingest_rag_data.py   # RAG 데이터 인제스트 CLI
│   │
│   └── tests/                   # pytest 테스트 (54개)
│       ├── conftest.py          # 테스트 DB 설정, fixtures
│       ├── test_auth.py
│       ├── test_profile.py
│       ├── test_diet.py
│       ├── test_exercise.py
│       ├── test_dashboard.py
│       ├── test_ai_service.py
│       ├── test_food_analysis.py
│       ├── test_recommendation.py
│       └── test_ai_chat.py
│
├── frontend/                    # Flutter (Phase 4 — 4-4B 완료)
│
└── docs/
    ├── PROJECT_OVERVIEW.md      # 프로젝트 전체 설계
    ├── DATABASE_SCHEMA.md       # DB 스키마 및 계산 공식
    ├── API_SPECIFICATION.md     # RESTful API 전체 명세
    ├── AI_RAG_STRATEGY.md       # AI/RAG 전략 및 프롬프트
    └── DEPLOYMENT.md            # 배포 가이드
```

---

## 3. 기술 스택 상세

### 백엔드
| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.12 | 런타임 |
| FastAPI | ≥0.115 | 웹 프레임워크 |
| SQLAlchemy | ≥2.0 (async) | ORM |
| asyncpg | ≥0.30 | PostgreSQL 비동기 드라이버 |
| Alembic | ≥1.14 | DB 마이그레이션 |
| pgvector | ≥0.3 | 벡터 유사도 검색 |
| Pydantic v2 | ≥2.0 | 데이터 검증 |
| pydantic-settings | ≥2.0 | 환경변수 기반 설정 |
| python-jose | ≥3.3 | JWT 토큰 |
| passlib+bcrypt | ≥1.7 | 비밀번호 해싱 |
| google-generativeai | ≥0.8 | Gemini AI SDK |
| Redis | ≥5.0 | 캐시/Rate Limit |
| pytest-asyncio | ≥0.24 | 비동기 테스트 |

### 인프라
| 기술 | 이미지/설정 |
|------|------------|
| PostgreSQL | `pgvector/pgvector:pg17` |
| Redis | `redis:7-alpine` |
| Backend | `python:3.12-slim` |

### AI 모델
| 용도 | 모델 |
|------|------|
| 일반 생성 | `gemini-2.5-flash` |
| 고급 생성 | `gemini-2.5-pro` |
| 임베딩 | `gemini-embedding-001` (3072차원) |

---

## 4. 코딩 규칙

### 4.1 Python 백엔드

#### 아키텍처 패턴
```
Router → Service → Repository(ORM)
```
- **Router**: HTTP 요청 처리, 인증 확인, 에러 변환
- **Service**: 비즈니스 로직 전담 (DB 직접 사용)
- **모든 DB 작업**: `async` 함수 사용

#### API 라우터 패턴
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.diet import DietLogCreate, DietLogResponse

router = APIRouter(prefix="/diet", tags=["diet"])

@router.post("/logs", response_model=DietLogResponse, status_code=status.HTTP_201_CREATED)
async def create_diet_log(
    data: DietLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DietLogResponse:
    service = DietService(db)
    result = await service.create(current_user.id, data)
    return DietLogResponse(status="success", data=result)
```

#### 서비스 패턴
```python
class DietService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: DietLogCreate) -> dict:
        # 비즈니스 로직
        ...
```

#### 공통 응답 형식
```json
// 성공
{"status": "success", "data": {...}}

// 에러
{"status": "error", "error": {"code": "ERROR_CODE", "message": "..."}}
```

#### 에러 코드
| HTTP Status | 코드 | 설명 |
|-------------|------|------|
| 400 | `VALIDATION_ERROR` | 요청 검증 실패 |
| 400 | `AI_BLOCKED` | AI 안전 필터 차단 |
| 401 | `UNAUTHORIZED` | 인증 실패 |
| 404 | `NOT_FOUND` | 리소스 없음 |
| 409 | `CONFLICT` | 중복 |
| 429 | `DAILY_LIMIT_EXCEEDED` | AI 일일 한도 초과 |
| 502 | `AI_PARSE_ERROR` | AI 응답 파싱 실패 |
| 503 | `AI_TIMEOUT` / `AI_RATE_LIMITED` / `AI_SERVICE_ERROR` | AI 서비스 오류 |

#### Import 규칙
- **모듈 상단에 모든 import 배치** (함수/메서드 내부 import 금지)
- 표준 라이브러리 → 서드파티 → 프로젝트 내부 순서
- `from __future__ import annotations` 사용 (순환 참조 방지)

#### 타입 힌트
- `Mapped[]` 타입으로 SQLAlchemy 모델 정의
- `str | None` 유니온 문법 사용 (Python 3.12)
- Pydantic v2 스타일 (`model_validator`, `field_validator`)

### 4.2 테스트 규칙

#### 테스트 실행
```bash
# Docker 내에서 실행 (DB 환경변수 필수)
docker compose exec \
  -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/health_trainer_test \
  -e TEST_DATABASE_ADMIN_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres \
  backend pytest tests/ -v --tb=short
```

#### 테스트 구조
- `conftest.py`: 세션 범위 DB 생성/삭제, `db_session` 및 `client` fixture
- `register_and_get_token`: 사용자 등록 후 토큰 반환 헬퍼
- 모든 테스트: `AsyncClient` 기반 통합 테스트
- AI 테스트: `unittest.mock.patch`로 AI 서비스 Mocking

#### 테스트 파일 명명
```
tests/test_{domain}.py
```

### 4.3 커밋 컨벤션

```
<type>(<scope>): <description>
```

**Type**: feat, fix, docs, style, refactor, test, chore, perf, ci, build
**Scope**: auth, profile, diet, exercise, dashboard, ai, db, ui

예시: `feat(diet): AI 음식 사진 분석 엔드포인트 구현`

---

## 5. DB 스키마 요약

| 테이블 | 설명 | 주요 필드 |
|--------|------|----------|
| `users` | 사용자 | email, password_hash, is_active |
| `user_profiles` | 프로필 (1:1) | height_cm, weight_kg, goal, tdee_kcal, target_* |
| `diet_logs` | 식단 기록 | user_id, log_date, meal_type |
| `diet_log_items` | 음식 항목 | diet_log_id, food_name, calories, protein/carbs/fat |
| `exercise_logs` | 운동 기록 | user_id, exercise_date, muscle_group |
| `exercise_sets` | 운동 세트 | exercise_log_id, reps, weight_kg |
| `refresh_tokens` | 리프레시 토큰 | user_id, token, expires_at |
| `ai_recommendations` | AI 추천 기록 | user_id, type(diet/exercise/coaching), recommendation |
| `rag_documents` | RAG 문서 | title, content, category, embedding(vector 3072) |

**Goal Enum**: `bulk`, `diet`, `maintain`
**Meal Type Enum**: `breakfast`, `lunch`, `dinner`, `snack`
**Muscle Group Enum**: `chest`, `back`, `shoulder`, `legs`, `arms`, `core`, `cardio`, `full_body`

---

## 6. API 엔드포인트 요약

| Method | Path | 인증 | 설명 |
|--------|------|------|------|
| POST | `/api/v1/auth/register` | ❌ | 회원가입 |
| POST | `/api/v1/auth/login` | ❌ | 로그인 |
| POST | `/api/v1/auth/refresh` | ❌ | 토큰 갱신 |
| GET | `/api/v1/profile` | ✅ | 프로필 조회 |
| PUT | `/api/v1/profile` | ✅ | 프로필 설정/수정 |
| POST | `/api/v1/diet/logs` | ✅ | 식단 기록 추가 |
| GET | `/api/v1/diet/logs` | ✅ | 식단 기록 조회 |
| PUT | `/api/v1/diet/logs/{id}` | ✅ | 식단 기록 수정 |
| DELETE | `/api/v1/diet/logs/{id}` | ✅ | 식단 기록 삭제 |
| POST | `/api/v1/diet/analyze-image` | ✅ | 음식 사진 AI 분석 |
| GET | `/api/v1/diet/recommend` | ✅ | AI 식단 추천 |
| POST | `/api/v1/exercise/logs` | ✅ | 운동 기록 추가 |
| GET | `/api/v1/exercise/logs` | ✅ | 운동 기록 조회 |
| PUT | `/api/v1/exercise/logs/{id}` | ✅ | 운동 기록 수정 |
| DELETE | `/api/v1/exercise/logs/{id}` | ✅ | 운동 기록 삭제 |
| GET | `/api/v1/exercise/history/{muscle}` | ✅ | 근육군별 히스토리 |
| GET | `/api/v1/exercise/recommend` | ✅ | AI 운동 추천 |
| GET | `/api/v1/dashboard/today` | ✅ | 오늘 현황 |
| GET | `/api/v1/dashboard/weekly` | ✅ | 주간 요약 |
| POST | `/api/v1/ai/chat` | ✅ | AI 코칭 채팅 |

---

## 7. 환경변수

```env
# App
PROJECT_NAME=AI Health Trainer
API_V1_PREFIX=/api/v1
DEBUG=true
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/health_trainer
DATABASE_URL_SYNC=postgresql://postgres:postgres@db:5432/health_trainer

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET_KEY=<secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI
GEMINI_API_KEY=<api-key>
AI_DEFAULT_MODEL=gemini-2.5-flash
AI_ADVANCED_MODEL=gemini-2.5-pro
AI_EMBEDDING_MODEL=gemini-embedding-001
AI_MAX_OUTPUT_TOKENS=1000
AI_TEMPERATURE=0.7
AI_DAILY_REQUEST_LIMIT=30

# Upload
UPLOAD_DIR=/data/uploads
MAX_IMAGE_SIZE_MB=10
```

---

## 8. 개발 상태

### 완료된 Phase
| Phase | 내용 | 테스트 |
|-------|------|--------|
| Phase 1 | 인증 + 프로필 + DB/Docker 기반 | 13개 PASS |
| Phase 2 | 식단/운동 CRUD + 대시보드 | 20개 PASS |
| Phase 3 | AI 서비스 + RAG + 추천 + 채팅 | 21개 PASS |
| **합계** | **전체** | **54개 PASS** |

### 다음 Phase
- **Phase 4**: Flutter 프론트엔드 — **4-4B까지 완료, 4-4C(lint+AI카드) 남음**
- **Phase 5**: 배포 (CI/CD, 클라우드)

---

## 9. 참조 문서

상세 설계가 필요할 때 아래 문서를 참조하라:
- `docs/PROJECT_OVERVIEW.md` — 프로젝트 전체 설계, 기술 스택 선정 이유
- `docs/DATABASE_SCHEMA.md` — DB 스키마 상세, TDEE 계산 공식
- `docs/API_SPECIFICATION.md` — RESTful API 전체 명세 (요청/응답 예시)
- `docs/AI_RAG_STRATEGY.md` — AI 프롬프트, RAG 전략, 안전 설정
- `COMMIT_CONVENTION.md` — 커밋 메시지 규칙

---

## 10. Codex 작업 시 주의사항

1. **모든 import는 모듈 상단에** — 함수 내부 import 절대 금지
2. **`from __future__ import annotations`** — 순환 참조 방지용, 모든 모델 파일에 사용
3. **비동기 함수** — DB 접근 함수는 반드시 `async def`
4. **Pydantic v2** — `BaseModel` 사용, `model_config` 방식
5. **SQLAlchemy 2.0** — `Mapped[]` 타입 힌트, `mapped_column()` 사용
6. **테스트는 conftest.py fixture 활용** — `client`, `db_session`, `register_and_get_token`
7. **에러는 HTTPException으로** — `detail={"code": "...", "message": "..."}`
8. **한국어 사용** — 사용자 대면 메시지는 한국어, 코드/변수명은 영어
9. **pgvector Vector 차원은 3072** — `gemini-embedding-001` 모델 기준
10. **Safety 설정** — `BLOCK_ONLY_HIGH` (모든 카테고리)

---

## 11. Codex 멀티 에이전트 운영 규칙

이 저장소에서 멀티 에이전트는 **앱 기능이 아니라 Codex 개발 워크플로우**를 의미한다.

### 기본 발동 정책

- 이 저장소의 기본값은 **메인 Codex 자동 라우팅**이다. 사용자가 작업을 요청하면, 별도로 “멀티 에이전트로 해줘”라고 말하지 않아도 메인 Codex가 `explorer` / `worker` / `reviewer` 사용 여부를 먼저 판단한다.
- 메인 Codex는 작은 단일 파일 수정, 단순 커밋, 명확한 문서 수정처럼 병렬화 이득이 없는 작업은 단독 처리할 수 있다. 이 경우에도 “작업이 작아서 메인 단독으로 처리한다”는 판단을 사용자에게 짧게 알려야 한다.
- 영향 범위가 불명확하거나, backend/frontend가 같이 걸리거나, DB/auth/API/AI/배포처럼 회귀 위험이 있는 작업은 기본적으로 subagent 사용을 검토한다.
- 사용자는 특정 agent 이름을 외울 필요가 없다. 사용자는 목표와 제약을 말하고, agent 라우팅은 메인 Codex가 책임진다.
- 사용자가 “단독으로 해줘”, “subagent 쓰지 마”, “빠르게 메인만 처리해”라고 명시하면 그 지시를 우선한다.

### 기본 구조

| 역할 | 권장 agent type | 책임 |
|------|------------------|------|
| **메인 Codex** | 기본 세션 | 요청 해석, critical path 처리, 하위 에이전트 위임, 결과 통합, 최종 승인 |
| **탐색 에이전트** | `explorer` | 관련 파일/제약/리스크 파악, 구현 방향 제안 |
| **구현 에이전트** | `worker` | 명시된 write scope 안에서만 코드 수정 |
| **리뷰 에이전트** | `reviewer` | findings-first 코드 리뷰, 회귀 리스크/누락 테스트 점검 |

### 운영 원칙

1. **메인 Codex가 항상 먼저 라우팅한다.** 사용자의 일반 작업 요청을 멀티 에이전트 라우팅 대상으로 보고, 병렬화 가치와 리스크에 따라 하위 에이전트 사용 여부를 결정한다.
2. **critical path는 메인 Codex가 직접 처리한다.** 메인 작업을 막는 급한 분석/수정은 위임하지 않는다.
3. **병렬 가능한 부수 작업만 위임한다.** 예: 코드 탐색, 독립 구현, 리뷰, 회귀 확인.
4. **같은 파일이나 같은 모듈 소유권을 두 `worker`에 동시에 주지 않는다.**
5. **프로젝트 제한값은 `agents.max_threads = 4`, `agents.max_depth = 1`**로 두고, 일반 작업에서는 2~3개 병렬을 권장한다.
6. **기존 변경사항은 존중한다.** dirty worktree가 있어도 다른 사람이 만든 변경을 되돌리지 않는다.
7. **`wait_agent`는 필요한 순간에만 호출한다.** 대기 중에는 메인 Codex가 비중복 작업을 계속 수행한다.
8. **라우팅 판단을 최종 응답에 남긴다.** subagent를 사용했으면 어떤 역할을 왜 썼는지, 사용하지 않았으면 왜 메인 단독으로 충분했는지 짧게 기록한다.

### 역할별 사용 기준

- `explorer`: “어디를 바꿔야 하는지”, “현재 로직이 어떻게 연결되는지”처럼 읽기 중심 질문에 사용한다.
- `worker`: 수정 범위를 명확히 지정할 수 있을 때만 사용한다. 반드시 파일/디렉터리 ownership을 함께 준다.
- `reviewer` 리뷰 에이전트: 비사소한 변경 뒤 회귀 가능성, 누락 테스트, 설계 일관성을 확인할 때 사용한다.

### write scope 규칙

- backend와 frontend는 서로 다른 `worker`에 병렬 할당할 수 있다.
- 같은 도메인이라도 파일 겹침 가능성이 있으면 한 `worker`만 수정한다.
- `worker`에게는 반드시 “지정된 파일 외 변경 금지”, “다른 사람이 만든 수정 revert 금지”를 명시한다.

### 표준 출력 계약

- `explorer` 결과: 관련 파일, 현재 동작, 제약/리스크, 추천 구현 경로
- `worker` 결과: 변경 파일, 구현 요약, 실행한 검증, 남은 리스크
- 리뷰 에이전트 결과: findings first, 심각도 순, 파일/라인 근거, 누락 테스트와 잔여 리스크

### 실제 운영 파일

- 프로젝트 subagent 설정: `.codex/config.toml`
- 역할 정의: `.codex/agents/explorer.toml`, `.codex/agents/worker.toml`, `.codex/agents/reviewer.toml`
- HITL Gate 1 템플릿: `.agent/workflows/task-spec-template.md`
- HITL Gate 2 체크리스트: `.agent/workflows/review-gate-checklist.md`
- `/plugins`용 `aiht-*` manifest는 제거하고, 현재는 `.codex/agents/*.toml`만 `/subagents` 기준으로 유지한다.
- Ralph loop 자동화는 **후속 단계**로 두고, 현재는 사람이 Gate 1/2를 직접 승인한다.

### 권장 패턴

- **작은 수정**: 메인 Codex 단독, 필요 시 `explorer` 1개만 추가
- **단일 도메인 기능/버그**: `explorer` 1 + `worker` 1 + 리뷰 에이전트 1
- **백엔드/프론트 병렬 작업**: backend `worker` 1 + frontend `worker` 1 + 리뷰 에이전트 1
