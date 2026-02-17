# AI Health Trainer - 데이터베이스 스키마 명세

> **이 문서의 목적:** Codex가 SQLAlchemy 모델을 작성할 때 참조하는 DB 설계 명세서.  
> **관리:** Claude Opus 4.6 (설계/수정), Codex 5.3 (구현)

---

## 1. 기술 선택

| 항목 | 선택 | 비고 |
|------|------|------|
| RDBMS | PostgreSQL 16+ | Docker 공식 이미지 사용 |
| Vector Extension | pgvector | RAG 임베딩 저장/검색 |
| ORM | SQLAlchemy 2.0 | async 지원 (asyncpg) |
| Migration | Alembic | 버전 관리형 마이그레이션 |

---

## 2. 테이블 상세 명세

### 2-1. `users` — 사용자 계정

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | `SERIAL` | PK | 자동 증가 |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL | 로그인 이메일 |
| `password_hash` | `VARCHAR(255)` | NOT NULL | bcrypt 해시 |
| `is_active` | `BOOLEAN` | DEFAULT true | 계정 활성 여부 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | 가입 일시 |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() | 수정 일시 |

**인덱스:**
- `ix_users_email` — email (UNIQUE)

---

### 2-2. `user_profiles` — 사용자 신체/목표 프로필

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | `SERIAL` | PK | |
| `user_id` | `INTEGER` | FK → users.id, UNIQUE | 1:1 관계 |
| `height_cm` | `DECIMAL(5,1)` | | 키 (cm) |
| `weight_kg` | `DECIMAL(5,1)` | | 몸무게 (kg) |
| `age` | `INTEGER` | | 나이 |
| `gender` | `VARCHAR(10)` | | 'male' / 'female' / 'other' |
| `goal` | `VARCHAR(20)` | NOT NULL | 'bulk' / 'diet' / 'maintain' |
| `activity_level` | `VARCHAR(20)` | | 아래 ENUM 참조 |
| `allergies` | `JSONB` | DEFAULT '[]' | 알레르기 목록 |
| `food_preferences` | `JSONB` | DEFAULT '[]' | 선호 식품 목록 |
| `tdee_kcal` | `INTEGER` | | 계산된 TDEE (서버 계산) |
| `target_calories` | `INTEGER` | | 목표 칼로리 (TDEE 기반) |
| `target_protein_g` | `DECIMAL(5,1)` | | 목표 단백질 (g) |
| `target_carbs_g` | `DECIMAL(5,1)` | | 목표 탄수화물 (g) |
| `target_fat_g` | `DECIMAL(5,1)` | | 목표 지방 (g) |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() | |

**activity_level 허용값:**
```
'sedentary'      — 비활동적 (사무직)
'light'          — 가벼운 운동 (주 1~3회)
'moderate'       — 보통 (주 3~5회)
'active'         — 활발 (주 6~7회)
'very_active'    — 매우 활발 (운동선수급)
```

**TDEE 계산 공식 (서버 측):**
```python
# Mifflin-St Jeor 공식
if gender == 'male':
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
else:
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

activity_multiplier = {
    'sedentary': 1.2,
    'light': 1.375,
    'moderate': 1.55,
    'active': 1.725,
    'very_active': 1.9,
}

tdee = bmr * activity_multiplier[activity_level]

# 목표별 칼로리 조정
if goal == 'bulk':
    target_calories = tdee + 300  # 잉여 칼로리
elif goal == 'diet':
    target_calories = tdee - 500  # 결손 칼로리
else:
    target_calories = tdee

# 매크로 비율 (기본값)
target_protein_g = weight_kg * 1.8   # 체중 1kg당 1.8g
target_fat_g = target_calories * 0.25 / 9  # 총 칼로리의 25%
target_carbs_g = (target_calories - target_protein_g * 4 - target_fat_g * 9) / 4
```

---

### 2-3. `exercise_logs` — 운동 기록 (운동 단위 헤더)

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | `SERIAL` | PK | |
| `user_id` | `INTEGER` | FK → users.id, NOT NULL | |
| `exercise_date` | `DATE` | NOT NULL | 운동 날짜 |
| `exercise_name` | `VARCHAR(100)` | NOT NULL | 운동명 (예: '벤치프레스') |
| `muscle_group` | `VARCHAR(50)` | NOT NULL | 근육군 (아래 참조) |
| `duration_min` | `INTEGER` | | 운동 시간 (분, 유산소용) |
| `memo` | `TEXT` | | 메모 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |

**muscle_group 허용값:**
```
'chest'       — 가슴
'back'        — 등
'shoulder'    — 어깨
'legs'        — 하체
'arms'        — 팔
'core'        — 코어
'cardio'      — 유산소
'full_body'   — 전신
```

**인덱스:**
- `ix_exercise_logs_user_date` — (user_id, exercise_date)
- `ix_exercise_logs_user_muscle` — (user_id, muscle_group)

---

### 2-4. `exercise_sets` — 운동 세트 상세 (exercise_logs의 하위 테이블)

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | `SERIAL` | PK | |
| `exercise_log_id` | `INTEGER` | FK → exercise_logs.id, NOT NULL, ON DELETE CASCADE | |
| `set_number` | `INTEGER` | NOT NULL | 세트 번호 (1, 2, 3...) |
| `reps` | `INTEGER` | NOT NULL | 반복 횟수 |
| `weight_kg` | `DECIMAL(5,1)` | | 사용 중량 (kg) |
| `is_completed` | `BOOLEAN` | DEFAULT true | 세트 완료 여부 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |

**인덱스:**
- `ix_exercise_sets_log_id` — exercise_log_id

**관계:** `exercise_logs` 1 : N `exercise_sets`

---

### 2-5. `diet_logs` — 식단 기록 (식사 단위 헤더)

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | `SERIAL` | PK | |
| `user_id` | `INTEGER` | FK → users.id, NOT NULL | |
| `log_date` | `DATE` | NOT NULL | 식사 날짜 |
| `meal_type` | `VARCHAR(20)` | NOT NULL | 식사 유형 (아래 참조) |
| `image_url` | `VARCHAR(500)` | NULLABLE | 음식 사진 경로 |
| `ai_analyzed` | `BOOLEAN` | DEFAULT false | AI 분석 여부 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |

**meal_type 허용값:**
```
'breakfast'   — 아침
'lunch'       — 점심
'dinner'      — 저녁
'snack'       — 간식
```

**인덱스:**
- `ix_diet_logs_user_date` — (user_id, log_date)

---

### 2-6. `diet_log_items` — 식단 항목 상세 (diet_logs의 하위 테이블)

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | `SERIAL` | PK | |
| `diet_log_id` | `INTEGER` | FK → diet_logs.id, NOT NULL, ON DELETE CASCADE | |
| `food_name` | `VARCHAR(200)` | NOT NULL | 음식명 |
| `serving_size` | `VARCHAR(50)` | | 1인분 기준 (예: '1공기', '200g') |
| `calories` | `DECIMAL(7,1)` | NOT NULL | 칼로리 (kcal) |
| `protein_g` | `DECIMAL(6,1)` | DEFAULT 0 | 단백질 (g) |
| `carbs_g` | `DECIMAL(6,1)` | DEFAULT 0 | 탄수화물 (g) |
| `fat_g` | `DECIMAL(6,1)` | DEFAULT 0 | 지방 (g) |
| `confidence` | `DECIMAL(3,2)` | | AI 신뢰도 (0.00~1.00) |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |

**인덱스:**
- `ix_diet_log_items_log_id` — diet_log_id

**관계:** `diet_logs` 1 : N `diet_log_items`

---

### 2-7. `ai_recommendations` — AI 추천 기록

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | `SERIAL` | PK | |
| `user_id` | `INTEGER` | FK → users.id, NOT NULL | |
| `type` | `VARCHAR(20)` | NOT NULL | 'diet' / 'exercise' / 'coaching' |
| `context_summary` | `TEXT` | | 프롬프트에 사용된 사용자 컨텍스트 |
| `prompt_used` | `TEXT` | | 실제 전송된 프롬프트 |
| `recommendation` | `TEXT` | NOT NULL | AI 응답 내용 |
| `rag_sources` | `JSONB` | DEFAULT '[]' | 사용된 RAG 문서 ID/제목 목록 |
| `model_used` | `VARCHAR(50)` | | 사용된 모델명 (예: 'gpt-4o') |
| `tokens_used` | `INTEGER` | | 사용된 토큰 수 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |

**인덱스:**
- `ix_ai_recommendations_user_type` — (user_id, type)

---

### 2-8. `rag_documents` — RAG 지식 저장소

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | `SERIAL` | PK | |
| `title` | `VARCHAR(500)` | NOT NULL | 문서 제목 |
| `source` | `VARCHAR(500)` | | 출처 (논문 DOI, URL 등) |
| `category` | `VARCHAR(50)` | NOT NULL | 카테고리 (아래 참조) |
| `content` | `TEXT` | NOT NULL | 문서 본문 (청크) |
| `embedding` | `VECTOR(768)` | NOT NULL | Gemini text-embedding-004 |
| `metadata` | `JSONB` | DEFAULT '{}' | 추가 메타데이터 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |

**category 허용값:**
```
'nutrition'       — 영양학
'exercise_science' — 운동 과학
'muscle_growth'   — 근성장
'diet_plan'       — 식단 계획
'supplement'      — 보충제
```

**인덱스:**
- `ix_rag_documents_category` — category
- `ix_rag_documents_embedding` — embedding (ivfflat, lists=100)

---

### 2-9. `refresh_tokens` — JWT Refresh Token 저장

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | `SERIAL` | PK | |
| `user_id` | `INTEGER` | FK → users.id, NOT NULL | |
| `token` | `VARCHAR(500)` | UNIQUE, NOT NULL | Refresh Token 값 |
| `expires_at` | `TIMESTAMPTZ` | NOT NULL | 만료 일시 |
| `is_revoked` | `BOOLEAN` | DEFAULT false | 폐기 여부 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |

**인덱스:**
- `ix_refresh_tokens_token` — token (UNIQUE)
- `ix_refresh_tokens_user` — user_id

---

## 3. ERD (Entity Relationship Diagram)

```
┌──────────────┐     1:1     ┌──────────────────┐
│    users     │─────────────│  user_profiles   │
│──────────────│             │──────────────────│
│ id (PK)      │             │ id (PK)          │
│ email (UQ)   │             │ user_id (FK, UQ) │
│ password_hash│             │ height_cm        │
│ is_active    │             │ weight_kg, goal   │
│ created_at   │             │ activity_level   │
│ updated_at   │             │ tdee_kcal        │
└──────┬───────┘             └──────────────────┘
       │ 1:N
       ├─────────────────┬───────────────────┐
       ▼                 ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌───────────────────┐
│exercise_logs │  │  diet_logs   │  │ai_recommendations │
│──────────────│  │──────────────│  │───────────────────│
│ id (PK)      │  │ id (PK)      │  │ id, user_id (FK) │
│ user_id (FK) │  │ user_id (FK) │  │ type             │
│ exercise_date│  │ log_date     │  │ recommendation   │
│ exercise_name│  │ meal_type    │  │ model_used       │
│ muscle_group │  │ image_url    │  └───────────────────┘
│ duration_min │  │ ai_analyzed  │
│ memo         │  └──────┬───────┘
└──────┬───────┘         │ 1:N
       │ 1:N            ▼
       ▼           ┌──────────────┐
┌──────────────┐ │diet_log_items│
│exercise_sets │ │──────────────│
│──────────────│ │ id (PK)      │
│ id (PK)      │ │ diet_log_id  │
│ exercise_log │ │  (FK)        │
│  _id (FK)    │ │ food_name    │
│ set_number   │ │ calories     │
│ reps         │ │ protein_g    │
│ weight_kg    │ │ carbs_g      │
│ is_completed │ │ fat_g        │
└──────────────┘ │ confidence   │
                  └──────────────┘

┌──────────────────┐  ┌──────────────────┐
│  refresh_tokens  │  │  rag_documents   │
│──────────────────│  │──────────────────│
│ id, user_id (FK) │  │ id (PK)          │
│ token (UQ)       │  │ title, category  │
│ expires_at       │  │ content          │
│ is_revoked       │  │ embedding (VEC)  │
└──────────────────┘  └──────────────────┘
```

---

## 4. Codex 구현 가이드

### SQLAlchemy 모델 작성 위치
```
backend/app/models/
├── __init__.py          # 모든 모델 import
├── user.py              # User, UserProfile
├── exercise.py          # ExerciseLog, ExerciseSet
├── diet.py              # DietLog, DietLogItem
├── ai_recommendation.py # AIRecommendation
├── rag_document.py      # RAGDocument
└── token.py             # RefreshToken
```

### 모델 작성 규칙
1. **Base 클래스** 사용: `from app.core.database import Base`
2. **명명 규칙**: 테이블명은 snake_case, 클래스명은 PascalCase
3. **타임스탬프**: 모든 테이블에 `created_at` 필수, `updated_at`은 수정 가능한 테이블만
4. **관계**: `relationship()`으로 정의, `back_populates` 사용
5. **JSONB 기본값**: `server_default=text("'[]'::jsonb")`
6. **pgvector**: `from pgvector.sqlalchemy import Vector` 사용

### Alembic 마이그레이션 명령
```bash
# 마이그레이션 파일 생성
cd backend
alembic revision --autogenerate -m "설명"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```
