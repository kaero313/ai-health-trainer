# AI Health Trainer - RESTful API 명세

> **이 문서의 목적:** Codex가 FastAPI 라우터를 구현할 때 참조하는 API 설계 명세서.  
> **관리:** Claude Opus 4.6 (설계/수정), Codex 5.3 (구현)

---

## 1. 공통 사항

### Base URL
```
/api/v1
```

### 인증 헤더
JWT가 필요한 엔드포인트는 아래 헤더를 포함해야 한다:
```
Authorization: Bearer <access_token>
```

### 공통 응답 형식

**성공 응답:**
```json
{
  "status": "success",
  "data": { ... },
  "message": "optional message"
}
```

**에러 응답:**
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "사람이 읽을 수 있는 에러 메시지"
  }
}
```

### 공통 에러 코드

| HTTP Status | 에러 코드 | 설명 |
|-------------|----------|------|
| 400 | `VALIDATION_ERROR` | 요청 데이터 검증 실패 |
| 401 | `UNAUTHORIZED` | 인증 실패 / 토큰 만료 |
| 403 | `FORBIDDEN` | 권한 없음 |
| 404 | `NOT_FOUND` | 리소스 없음 |
| 409 | `CONFLICT` | 중복 데이터 (이메일 등) |
| 422 | `UNPROCESSABLE_ENTITY` | 처리 불가 |
| 429 | `RATE_LIMITED` | API 호출 제한 초과 |
| 500 | `INTERNAL_ERROR` | 서버 내부 오류 |

### 페이지네이션 (목록 조회 시)

**요청 파라미터:**
```
?page=1&size=20
```

**응답에 포함:**
```json
{
  "status": "success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "size": 20,
    "pages": 5
  }
}
```

---

## 2. 인증 API (`/api/v1/auth`)

### POST `/auth/register` — 회원가입

**인증:** 불필요

**요청:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!"
}
```

**검증 규칙:**
- `email`: 유효한 이메일 형식, 255자 이내
- `password`: 최소 8자, 영문+숫자+특수문자 포함
- `password_confirm`: password와 일치해야 함

**성공 응답 (201):**
```json
{
  "status": "success",
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "created_at": "2026-02-17T10:00:00Z"
    },
    "access_token": "eyJhbG...",
    "refresh_token": "eyJhbG...",
    "token_type": "bearer"
  }
}
```

**에러:**
- 409: 이미 가입된 이메일

---

### POST `/auth/login` — 로그인

**인증:** 불필요

**요청:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbG...",
    "refresh_token": "eyJhbG...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

**에러:**
- 401: 이메일 또는 비밀번호 불일치

---

### POST `/auth/refresh` — 토큰 갱신

**인증:** 불필요 (Refresh Token 사용)

**요청:**
```json
{
  "refresh_token": "eyJhbG..."
}
```

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbG...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

### JWT 토큰 설정

| 항목 | 값 | 비고 |
|------|-----|------|
| Access Token 유효기간 | 30분 | |
| Refresh Token 유효기간 | 7일 | |
| 알고리즘 | HS256 | |
| 페이로드 | `{"sub": user_id, "exp": expiry}` | |

---

## 3. 프로필 API (`/api/v1/profile`)

### GET `/profile` — 프로필 조회

**인증:** 필요

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "user_id": 1,
    "height_cm": 175.0,
    "weight_kg": 70.0,
    "age": 28,
    "gender": "male",
    "goal": "bulk",
    "activity_level": "moderate",
    "allergies": ["우유", "땅콩"],
    "food_preferences": ["닭가슴살", "고구마"],
    "tdee_kcal": 2500,
    "target_calories": 2800,
    "target_protein_g": 126.0,
    "target_carbs_g": 350.0,
    "target_fat_g": 77.8
  }
}
```

**에러:**
- 404: 프로필 미설정 (최초 가입 후)

---

### PUT `/profile` — 프로필 설정/수정

**인증:** 필요

**요청:**
```json
{
  "height_cm": 175.0,
  "weight_kg": 70.0,
  "age": 28,
  "gender": "male",
  "goal": "bulk",
  "activity_level": "moderate",
  "allergies": ["우유", "땅콩"],
  "food_preferences": ["닭가슴살", "고구마"]
}
```

**검증 규칙:**
- `height_cm`: 100.0 ~ 250.0
- `weight_kg`: 30.0 ~ 300.0
- `age`: 10 ~ 100
- `gender`: 'male' / 'female' / 'other'
- `goal`: 'bulk' / 'diet' / 'maintain'
- `activity_level`: 'sedentary' / 'light' / 'moderate' / 'active' / 'very_active'

**성공 응답 (200):** 프로필 조회와 동일한 형식

**비즈니스 로직:**
- 서버에서 TDEE, target_calories, target_protein_g, target_carbs_g, target_fat_g 자동 계산
- 계산 공식은 `DATABASE_SCHEMA.md` 참조

---

## 4. 식단 API (`/api/v1/diet`)

### POST `/diet/logs` — 식단 기록 추가

**인증:** 필요

**요청:**
```json
{
  "log_date": "2026-02-17",
  "meal_type": "lunch",
  "food_name": "닭가슴살 샐러드",
  "serving_size": "1인분",
  "calories": 350.0,
  "protein_g": 40.0,
  "carbs_g": 15.0,
  "fat_g": 12.0,
  "image_url": null
}
```

**성공 응답 (201):**
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "log_date": "2026-02-17",
    "meal_type": "lunch",
    "food_name": "닭가슴살 샐러드",
    "calories": 350.0,
    "protein_g": 40.0,
    "carbs_g": 15.0,
    "fat_g": 12.0,
    "ai_analyzed": false,
    "created_at": "2026-02-17T12:30:00Z"
  }
}
```

---

### GET `/diet/logs` — 식단 기록 조회

**인증:** 필요

**쿼리 파라미터:**
| 파라미터 | 필수 | 설명 |
|---------|------|------|
| `date` | ✅ | 조회 날짜 (YYYY-MM-DD) |

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "date": "2026-02-17",
    "meals": {
      "breakfast": [...],
      "lunch": [...],
      "dinner": [...],
      "snack": [...]
    },
    "daily_total": {
      "calories": 1850.0,
      "protein_g": 120.0,
      "carbs_g": 200.0,
      "fat_g": 55.0
    },
    "target_remaining": {
      "calories": 950.0,
      "protein_g": 6.0,
      "carbs_g": 150.0,
      "fat_g": 22.8
    }
  }
}
```

---

### PUT `/diet/logs/{log_id}` — 식단 기록 수정

**인증:** 필요 (본인 기록만)

**요청:** POST와 동일한 형식 (부분 업데이트 지원)

---

### DELETE `/diet/logs/{log_id}` — 식단 기록 삭제

**인증:** 필요 (본인 기록만)

**성공 응답 (200):**
```json
{
  "status": "success",
  "message": "식단 기록이 삭제되었습니다."
}
```

---

### POST `/diet/analyze-image` — 음식 사진 AI 분석

**인증:** 필요

**요청:** `multipart/form-data`
| 필드 | 타입 | 설명 |
|------|------|------|
| `image` | file | 음식 사진 (JPEG/PNG, 최대 10MB) |
| `meal_type` | string | 식사 유형 (optional) |

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "foods": [
      {
        "food_name": "김치찌개",
        "serving_size": "1그릇 (300g)",
        "calories": 200.0,
        "protein_g": 12.0,
        "carbs_g": 10.0,
        "fat_g": 13.0,
        "confidence": 0.85
      },
      {
        "food_name": "흰쌀밥",
        "serving_size": "1공기 (200g)",
        "calories": 300.0,
        "protein_g": 5.0,
        "carbs_g": 68.0,
        "fat_g": 0.5,
        "confidence": 0.92
      }
    ],
    "total": {
      "calories": 500.0,
      "protein_g": 17.0,
      "carbs_g": 78.0,
      "fat_g": 13.5
    }
  }
}
```

**비즈니스 로직:**
- Gemini 2.5 Flash Vision API로 이미지 전송
- 프롬프트는 `AI_RAG_STRATEGY.md` 참조
- 분석 결과를 반환만 하고, 사용자가 확인 후에 식단 기록으로 저장하는 것은 별도 POST 호출

---

### GET `/diet/recommend` — AI 식단 추천

**인증:** 필요

**쿼리 파라미터:**
| 파라미터 | 필수 | 설명 |
|---------|------|------|
| `date` | ❌ | 기준 날짜 (기본: 오늘) |

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "remaining_nutrients": {
      "calories": 950.0,
      "protein_g": 6.0,
      "carbs_g": 150.0,
      "fat_g": 22.8
    },
    "recommendation": "오늘 단백질은 거의 목표를 달성했습니다. 저녁에는 탄수화물 위주의 식사를 추천합니다. 고구마(200g, 170kcal) + 연어구이(150g, 250kcal)로 남은 칼로리와 지방을 채울 수 있습니다.",
    "suggested_foods": [
      {
        "food_name": "고구마",
        "serving_size": "200g",
        "calories": 170,
        "reason": "탄수화물 보충"
      }
    ],
    "sources": ["영양학 가이드라인 - 벌크업 식단 구성"]
  }
}
```

**비즈니스 로직:**
- 사용자 프로필 + 오늘/최근 식단 기록 → 프롬프트 구성
- RAG 검색 → 관련 영양 지식 추가
- Gemini 2.5 Flash로 추천 생성
- 결과를 `ai_recommendations` 테이블에 저장

---

## 5. 운동 API (`/api/v1/exercise`)

### POST `/exercise/logs` — 운동 기록 추가

**인증:** 필요

**요청:**
```json
{
  "exercise_date": "2026-02-17",
  "exercise_name": "벤치프레스",
  "muscle_group": "chest",
  "sets": 4,
  "reps": 10,
  "weight_kg": 60.0,
  "memo": "마지막 세트 힘들었음"
}
```

**성공 응답 (201):** 생성된 기록 반환

---

### GET `/exercise/logs` — 운동 기록 조회

**인증:** 필요

**쿼리 파라미터:**
| 파라미터 | 필수 | 설명 |
|---------|------|------|
| `date` | ✅ | 조회 날짜 (YYYY-MM-DD) |

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "date": "2026-02-17",
    "exercises": [
      {
        "id": 1,
        "exercise_name": "벤치프레스",
        "muscle_group": "chest",
        "sets": 4,
        "reps": 10,
        "weight_kg": 60.0,
        "memo": "마지막 세트 힘들었음"
      }
    ],
    "muscle_groups_trained": ["chest"]
  }
}
```

---

### PUT `/exercise/logs/{log_id}` — 운동 기록 수정

**인증:** 필요 (본인 기록만)

---

### DELETE `/exercise/logs/{log_id}` — 운동 기록 삭제

**인증:** 필요 (본인 기록만)

---

### GET `/exercise/history/{muscle_group}` — 근육군별 히스토리

**인증:** 필요

**쿼리 파라미터:**
| 파라미터 | 필수 | 설명 |
|---------|------|------|
| `limit` | ❌ | 최근 N건 (기본: 10) |

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "muscle_group": "chest",
    "history": [
      {
        "date": "2026-02-17",
        "exercises": [
          {"exercise_name": "벤치프레스", "sets": 4, "reps": 10, "weight_kg": 60.0},
          {"exercise_name": "덤벨플라이", "sets": 3, "reps": 12, "weight_kg": 14.0}
        ]
      },
      {
        "date": "2026-02-14",
        "exercises": [
          {"exercise_name": "벤치프레스", "sets": 4, "reps": 10, "weight_kg": 57.5}
        ]
      }
    ],
    "progress": {
      "벤치프레스": {
        "weight_change": "+2.5kg",
        "trend": "increasing"
      }
    }
  }
}
```

---

### GET `/exercise/recommend` — AI 운동 추천

**인증:** 필요

**쿼리 파라미터:**
| 파라미터 | 필수 | 설명 |
|---------|------|------|
| `muscle_group` | ❌ | 특정 근육군 (미지정 시 전체 고려) |

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "recommendation": "지난 가슴 운동에서 벤치프레스 60kg x 10회를 성공하셨습니다. 오늘은 62.5kg으로 도전해보세요. 점진적 과부하 원칙에 따라 5% 이내의 증량이 적절합니다.",
    "suggested_exercises": [
      {
        "exercise_name": "벤치프레스",
        "muscle_group": "chest",
        "sets": 4,
        "reps": 8,
        "weight_kg": 62.5,
        "reason": "이전 기록 대비 2.5kg 점진적 증량"
      },
      {
        "exercise_name": "인클라인 덤벨프레스",
        "muscle_group": "chest",
        "sets": 3,
        "reps": 12,
        "weight_kg": 16.0,
        "reason": "상부 가슴 자극을 위한 보조 운동"
      }
    ],
    "sources": ["운동 과학 - 점진적 과부하 원칙 연구"]
  }
}
```

---

## 6. AI 채팅 API (`/api/v1/ai`)

### POST `/ai/chat` — AI 코칭 채팅

**인증:** 필요

**요청:**
```json
{
  "message": "오늘 저녁 뭘 먹으면 좋을까요?",
  "context_type": "diet"
}
```

**필드 설명:**
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `message` | string | ✅ | 사용자 질문 (1~1000자) |
| `context_type` | string | ❌ | `diet` / `exercise` / `general` (기본: `general`) |

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "answer": "오늘 저녁은 고구마 200g과 닭가슴살 150g을 추천합니다. 현재 탄수화물이 부족하므로...",
    "context_used": {
      "profile_loaded": true,
      "today_diet_records": 2,
      "today_exercise_records": 0
    },
    "sources": ["벌크업 영양 가이드"]
  }
}
```

**AI 에러 코드:**
| HTTP Status | 에러 코드 | 설명 |
|-------------|----------|------|
| 400 | `AI_BLOCKED` | AI가 해당 요청을 처리할 수 없음 (안전 필터) |
| 429 | `DAILY_LIMIT_EXCEEDED` | 일일 AI 사용 한도 초과 |
| 502 | `AI_PARSE_ERROR` | AI 응답 파싱 실패 |
| 503 | `AI_TIMEOUT` | AI 서비스 응답 없음 |
| 503 | `AI_RATE_LIMITED` | AI 서비스 일시 제한 (Google API) |
| 503 | `AI_SERVICE_ERROR` | AI 서비스 내부 오류 |

**비즈니스 로직:**
- `context_type`에 따라 프로필 + 식단/운동 기록을 자동 수집
- RAG 검색으로 관련 영양/운동 지식 참조
- Gemini 2.5 Flash로 개인화된 답변 생성
- 결과를 `ai_recommendations` 테이블에 저장 (type: `coaching`)

---

## 7. 대시보드 API (`/api/v1/dashboard`)

### GET `/dashboard/today` — 오늘의 종합 현황

**인증:** 필요

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "date": "2026-02-17",
    "nutrition": {
      "target": {
        "calories": 2800,
        "protein_g": 126.0,
        "carbs_g": 350.0,
        "fat_g": 77.8
      },
      "consumed": {
        "calories": 1850,
        "protein_g": 120.0,
        "carbs_g": 200.0,
        "fat_g": 55.0
      },
      "remaining": {
        "calories": 950,
        "protein_g": 6.0,
        "carbs_g": 150.0,
        "fat_g": 22.8
      },
      "progress_percent": {
        "calories": 66.1,
        "protein_g": 95.2,
        "carbs_g": 57.1,
        "fat_g": 70.7
      }
    },
    "exercise": {
      "completed": true,
      "muscle_groups_trained": ["chest", "arms"],
      "total_sets": 15,
      "exercises_count": 4
    },
    "streak": {
      "exercise_days": 5,
      "diet_logging_days": 12
    }
  }
}
```

---

### GET `/dashboard/weekly` — 주간 요약

**인증:** 필요

**쿼리 파라미터:**
| 파라미터 | 필수 | 설명 |
|---------|------|------|
| `week_start` | ❌ | 주 시작일 (기본: 이번 주 월요일) |

**성공 응답 (200):**
```json
{
  "status": "success",
  "data": {
    "week_start": "2026-02-11",
    "week_end": "2026-02-17",
    "nutrition_avg": {
      "calories": 2650,
      "protein_g": 118.0,
      "carbs_g": 320.0,
      "fat_g": 72.0
    },
    "exercise_summary": {
      "total_days": 5,
      "muscle_groups": {
        "chest": 2,
        "back": 1,
        "legs": 1,
        "shoulder": 1
      }
    },
    "daily_breakdown": [
      {"date": "2026-02-11", "calories": 2700, "exercised": true},
      {"date": "2026-02-12", "calories": 2600, "exercised": true}
    ]
  }
}
```

---

## 8. Codex 구현 가이드

### 파일 구조
```
backend/app/api/v1/
├── __init__.py
├── ai_chat.py       # AI 채팅 엔드포인트
├── auth.py          # 인증 관련 엔드포인트
├── profile.py       # 프로필 엔드포인트
├── diet.py          # 식단 + 사진분석 + 추천 엔드포인트
├── exercise.py      # 운동 + 추천 엔드포인트
├── dashboard.py     # 대시보드 엔드포인트
└── router.py        # APIRouter 통합
```

### 구현 규칙

1. **라우터 패턴:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user

router = APIRouter(prefix="/exercise", tags=["exercise"])

@router.post("/logs", status_code=status.HTTP_201_CREATED)
async def create_exercise_log(
    data: ExerciseLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ...
```

2. **응답 모델:** 모든 응답은 Pydantic 모델로 정의 (`backend/app/schemas/`)
3. **에러 처리:** `HTTPException`에 위 에러 코드 사용
4. **본인 확인:** CRUD 시 `log.user_id == current_user.id` 검증 필수
5. **날짜 파라미터:** `datetime.date` 타입, `Query()` 사용
