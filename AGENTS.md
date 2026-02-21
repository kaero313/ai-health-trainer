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
├── frontend/                    # Flutter (Phase 4 예정)
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
- **Phase 4**: Flutter 프론트엔드 (모바일 우선)
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
