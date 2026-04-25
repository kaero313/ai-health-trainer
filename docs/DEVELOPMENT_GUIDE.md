# AI Health Trainer - 개발 가이드라인

> **이 문서의 목적:** Codex가 코드를 작성할 때 따라야 하는 규칙, 컨벤션, 실행 방법 안내.
> **관리:** Claude Opus 4.6 (설계/수정), Codex 5.3 (구현)
> **현재 기준:** 최신 프로젝트 상태와 다음 의사결정은 `docs/OWNER_GUIDE.md`를 우선한다.

---

## 1. 개발 환경 설정

### 필수 도구
- Python 3.12+
- Flutter SDK (최신 stable)
- Docker & Docker Compose
- Git

### 로컬 실행 (Docker Compose)

```bash
# 전체 서비스 시작
docker-compose up -d

# 백엔드만 개발 모드 실행 (핫 리로드)
docker-compose up -d db redis
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Flutter 앱 실행
cd frontend
flutter run
```

### 환경 변수 (.env)
```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/health_trainer
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/health_trainer

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# AI Settings
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

## 2. 백엔드 코딩 컨벤션 (Python/FastAPI)

### 2-1. 파일/디렉토리 명명

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일명 | snake_case | `exercise_log.py` |
| 클래스명 | PascalCase | `ExerciseLog` |
| 함수명 | snake_case | `create_exercise_log` |
| 상수 | UPPER_SNAKE_CASE | `MAX_IMAGE_SIZE` |
| 변수명 | snake_case | `user_profile` |

### 2-2. 레이어 분리 패턴

```
API Layer (api/v1/*.py)
    │  - HTTP 요청/응답 처리
    │  - 입력 검증 (Pydantic)
    │  - 인증 확인
    ▼
Service Layer (services/*.py)
    │  - 비즈니스 로직
    │  - 외부 API 호출 (Gemini 등)
    │  - 트랜잭션 관리
    ▼
Model Layer (models/*.py)
    │  - DB 테이블 정의 (SQLAlchemy)
    ▼
Schema Layer (schemas/*.py)
       - 요청/응답 데이터 구조 (Pydantic)
```

**규칙:**
- API 라우터에 비즈니스 로직을 직접 쓰지 않는다
- Service에서 DB 쿼리를 직접 쓰지 않고, ORM 모델/쿼리를 통해 접근한다
- 외부 API 호출은 반드시 Service 레이어에서만 수행한다

### 2-3. Pydantic 스키마 작성 규칙

```python
# backend/app/schemas/exercise.py

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class ExerciseLogCreate(BaseModel):
    """운동 기록 생성 요청"""
    exercise_date: date
    exercise_name: str = Field(..., min_length=1, max_length=100)
    muscle_group: str = Field(..., pattern=r'^(chest|back|shoulder|legs|arms|core|cardio|full_body)$')
    sets: int = Field(..., ge=1, le=100)
    reps: int = Field(..., ge=1, le=1000)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    duration_min: Optional[int] = Field(None, ge=1, le=600)
    memo: Optional[str] = Field(None, max_length=500)

class ExerciseLogResponse(BaseModel):
    """운동 기록 응답"""
    id: int
    exercise_date: date
    exercise_name: str
    muscle_group: str
    sets: int
    reps: int
    weight_kg: Optional[float]
    duration_min: Optional[int]
    memo: Optional[str]

    model_config = {"from_attributes": True}
```

**패턴:**
- `*Create` — 생성 요청 스키마
- `*Update` — 수정 요청 스키마 (모든 필드 Optional)
- `*Response` — 응답 스키마
- `model_config = {"from_attributes": True}` — ORM 모델 → Pydantic 변환

### 2-4. 의존성 주입 패턴

```python
# 인증된 사용자 주입
from app.core.deps import get_current_user
current_user: User = Depends(get_current_user)

# DB 세션 주입
from app.core.database import get_db
db: AsyncSession = Depends(get_db)

# AI 서비스 주입
from app.services.ai_service import get_ai_service
ai_service: AIService = Depends(get_ai_service)
```

### 2-5. 에러 처리 패턴

```python
from fastapi import HTTPException, status

# 리소스 없음
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "NOT_FOUND", "message": "운동 기록을 찾을 수 없습니다."}
)

# 권한 없음
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "FORBIDDEN", "message": "본인의 기록만 수정할 수 있습니다."}
)
```

### 2-6. 비동기 DB 쿼리 패턴

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_exercise_logs_by_date(
    db: AsyncSession, user_id: int, log_date: date
) -> list[ExerciseLog]:
    result = await db.execute(
        select(ExerciseLog)
        .where(ExerciseLog.user_id == user_id)
        .where(ExerciseLog.exercise_date == log_date)
        .order_by(ExerciseLog.created_at)
    )
    return result.scalars().all()
```

---

## 3. 프론트엔드 코딩 컨벤션 (Flutter/Dart)

### 3-1. 상태 관리: Riverpod

```dart
// 상태 관리는 Riverpod 사용
// flutter_riverpod 패키지

// Provider 정의 예시
final exerciseLogsProvider = FutureProvider.autoDispose
    .family<List<ExerciseLog>, DateTime>((ref, date) async {
  final service = ref.read(exerciseServiceProvider);
  return service.getLogsByDate(date);
});
```

### 3-2. API 통신: Dio

```dart
// HTTP 클라이언트는 Dio 사용
// 인터셉터로 JWT 자동 첨부 및 갱신 처리

class ApiClient {
  final Dio _dio;

  ApiClient() : _dio = Dio(BaseOptions(
    baseUrl: 'http://YOUR_SERVER/api/v1',
    connectTimeout: Duration(seconds: 10),
  )) {
    _dio.interceptors.add(AuthInterceptor());
  }
}
```

### 3-3. 파일 명명

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일명 | snake_case | `exercise_screen.dart` |
| 클래스명 | PascalCase | `ExerciseScreen` |
| 변수/함수명 | camelCase | `exerciseLogs` |
| 상수 | camelCase (k 접두사) | `kMaxImageSize` |

### 3-4. 화면 구조

```
lib/screens/
├── auth/
│   ├── login_screen.dart
│   └── register_screen.dart
├── dashboard/
│   └── dashboard_screen.dart
├── diet/
│   ├── diet_log_screen.dart
│   ├── diet_image_analyze_screen.dart
│   └── diet_recommend_screen.dart
├── exercise/
│   ├── exercise_log_screen.dart
│   └── exercise_recommend_screen.dart
└── profile/
    └── profile_screen.dart
```

---

## 4. 테스트 전략

### 4-1. 백엔드 테스트 (pytest)

```
backend/tests/
├── conftest.py              # 공통 fixture (테스트 DB, 클라이언트)
├── test_auth.py             # 인증 API 테스트
├── test_profile.py          # 프로필 API 테스트
├── test_diet.py             # 식단 API 테스트
├── test_exercise.py         # 운동 API 테스트
├── test_dashboard.py        # 대시보드 API 테스트
├── test_ai_service.py       # AI 서비스 테스트 (Mock)
└── test_rag_service.py      # RAG 서비스 테스트
```

**테스트 실행:**
```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
```

**conftest.py 구현 가이드:**
```python
"""
Codex 구현 가이드:
- httpx.AsyncClient + ASGITransport 사용
- 테스트용 PostgreSQL DB (docker-compose.test.yml)
- 각 테스트 함수마다 트랜잭션 롤백 (테스트 격리)
- Gemini API는 Mock 처리 (실제 호출 금지)
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
```

### 4-2. 최소 테스트 케이스 (반드시 구현)

| 모듈 | 테스트 |
|------|--------|
| Auth | 회원가입 성공/중복이메일/약한비밀번호, 로그인 성공/실패, 토큰갱신 |
| Profile | 프로필 생성/조회/수정, TDEE 계산 정확성 |
| Diet | CRUD 전체, 날짜별 조회, 일일 합계 계산 |
| Exercise | CRUD 전체, 근육군별 히스토리 |
| Dashboard | 오늘/주간 데이터 정확성 |
| AI Service | Mock 응답 파싱, 에러 처리 |

---

## 5. Git 브랜치 전략

```
main           ← 배포 가능한 안정 버전
  └── develop  ← 개발 통합
       ├── feature/auth          ← 인증 기능
       ├── feature/profile       ← 프로필 기능
       ├── feature/exercise      ← 운동 기능
       ├── feature/diet          ← 식단 기능
       ├── feature/dashboard     ← 대시보드
       └── feature/ai-coaching   ← AI 코칭
```

**커밋 메시지 컨벤션:**
```
feat: 운동 기록 CRUD API 구현
fix: 토큰 갱신 시 만료 처리 버그 수정
docs: API 명세서 업데이트
test: 식단 API 테스트 추가
refactor: AI 서비스 에러 처리 개선
```

---

## 6. Codex 구현 현황 (Phase별)

### Phase 1: 기반 구축 - 완료

1. **Docker 환경**
   - `docker-compose.yml` — PostgreSQL(pgvector), Redis, Backend
   - `backend/Dockerfile` — Python 3.12 기반 이미지
   - 참조: `DEPLOYMENT.md`

2. **FastAPI 앱 초기화**
   - `backend/app/main.py` — FastAPI 앱, CORS, 라우터 등록
   - `backend/app/core/config.py` — 환경변수 로드 (Pydantic Settings)
   - `backend/app/core/database.py` — async SQLAlchemy 엔진 + 세션

3. **DB 모델 + 마이그레이션**
   - 인증, 프로필, 식단, 운동, AI/RAG 기본 모델 작성
   - Alembic 초기화 + 마이그레이션
   - 참조: `DATABASE_SCHEMA.md`

4. **JWT 인증**
   - `backend/app/core/security.py` — 토큰 생성/검증, 비밀번호 해싱
   - `backend/app/core/deps.py` — 인증 의존성 (`get_current_user`)
   - `backend/app/api/v1/auth.py` — 회원가입/로그인/토큰갱신
   - 참조: `API_SPECIFICATION.md` 섹션 2

### Phase 2: 핵심 CRUD - 완료

5. **프로필 API** — `API_SPECIFICATION.md` 섹션 3
6. **운동 기록 API** — `API_SPECIFICATION.md` 섹션 5
7. **식단 기록 API** — `API_SPECIFICATION.md` 섹션 4
8. **대시보드 API** — `API_SPECIFICATION.md` 섹션 7

### Phase 3: AI 통합 - 완료

9. **AI 서비스** — `AI_RAG_STRATEGY.md` 섹션 3
10. **RAG 서비스** — `AI_RAG_STRATEGY.md` 섹션 5
11. **음식 사진 분석** — `AI_RAG_STRATEGY.md` 섹션 4-1
12. **식단/운동 추천 + AI 채팅** — `AI_RAG_STRATEGY.md` 섹션 4-2, 4-3

### Phase 4: Flutter 프론트엔드 - 완료

13. **공통 기반** — 디자인 시스템, Riverpod, GoRouter, Dio/Auth Interceptor
14. **주요 화면** — 온보딩, 로그인/회원가입, 프로필, 대시보드, 식단, 운동
15. **AI 화면** — 음식 사진 분석, 식단/운동 추천, AI 코칭 채팅
16. **UX 마감** — FAB 바텀시트, 화면 전환, 대시보드 AI 코칭 카드, `flutter analyze` 0건

### Phase 5: 배포/운영 기반 - 완료

17. **프로덕션 구성** — `docker-compose.prod.yml`, 멀티스테이지 Dockerfile, Nginx/SSL 템플릿
18. **자동화** — GitHub Actions CI/CD, PostgreSQL 백업 스크립트
19. **운영 진단** — `/api/v1/health`, DB/Redis 상태 확인, 네트워크 타임아웃/로그 개선
20. **RAG 운영** — 한국 음식/보충제 데이터 추가, reset/ingest 스크립트 정비

### Phase 6: 월간 리포트/체중 추적/개발 운영 고도화 - 완료

21. **프로필 Guard** — `/profile/check` API + Flutter 라우터 Guard
22. **체중 히스토리** — `weight_logs` 모델/마이그레이션, `/profile/weight`, `/profile/weight-history`
23. **월간 리포트** — `/dashboard/monthly`, Flutter 월간 리포트 화면, 대시보드 진입 카드
24. **개발 운영** — Codex subagent 설정, HITL Gate 템플릿, OpenSearch compose 서비스

### 다음 작업 기준

Phase 1~6은 완료 상태로 취급한다. 새 작업은 Phase 7 또는 릴리스 후보 작업으로 별도 정의하고, 릴리스 전에는 로컬 테스트용 로그인 기본값 제거, Gemini SDK `google.genai` 전환, Play Store/운영 배포 검증을 확인한다.
