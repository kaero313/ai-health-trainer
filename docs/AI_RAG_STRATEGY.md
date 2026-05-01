# AI Health Trainer - AI/RAG 전략 명세

> **이 문서의 목적:** Codex가 AI 서비스 레이어를 구현할 때 참조하는 설계서.
> **관리:** Claude Opus 4.6 (설계/수정), Codex 5.3 (구현)
> **현재 기준:** 최신 프로젝트 상태와 다음 의사결정은 `docs/OWNER_GUIDE.md`를 우선한다.
> **RAG 운영 기준:** 지식 수집, 정제, 버전 관리, OpenSearch 색인, 삭제, 재색인, trace 정책은 `docs/RAG_OPERATIONS.md`를 우선한다.

---

## 1. AI 서비스 구성도

```
사용자 요청
    │
    ▼
┌─────────────────────────────────────────┐
│             AI Service Layer            │
│                                         │
│  ┌─────────────┐   ┌────────────────┐   │
│  │ RAG Service  │   │ LLM Gateway    │   │
│  │             │   │                │   │
│  │ - 문서 검색  │──→│ - 프롬프트 조합 │   │
│  │ - 임베딩     │   │ - API 호출     │   │
│  │ - pgvector  │   │ - 응답 파싱     │   │
│  └─────────────┘   └────────────────┘   │
│                           │              │
└───────────────────────────┼──────────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │  Gemini API    │
                    │  (Google AI)   │
                    └────────────────┘
```

---

## 2. Google Gemini API 설정

### 왜 Gemini인가?

| 항목 | Gemini API | OpenAI API |
|------|-----------|-----------|
| **무료 티어** | ✅ 있음 (시간/일 제한) | ❌ 없음 (토큰당 과금) |
| **멀티모달** | ✅ (이미지+텍스트) | ✅ (이미지+텍스트) |
| **임베딩** | ✅ 무료 티어 포함 | 토큰당 과금 |
| **포트폴리오 비용** | $0 (무료 티어) | $5~15/month 예상 |

### 사용 모델

| 용도 | 모델 | 무료 티어 제한 | 비고 |
|------|------|--------------|------|
| 음식 사진 분석 | `gemini-3-flash-preview` | 10 RPM, 250 RPD | 멀티모달 (Vision), 빠른 응답 |
| 식단/운동 추천 | `gemini-3-flash-preview` | 10 RPM, 250 RPD | 텍스트 생성, 충분한 품질 |
| 고급 코칭 (복잡한 추론) | `gemini-2.5-pro` | 5 RPM, 25 RPD | 복잡한 분석 시 사용 |
| 임베딩 | `gemini-embedding-001` | 무료 | 3072 차원 |

> **RPM** = 분당 요청 수, **RPD** = 일당 요청 수

### API 키 발급 방법
1. [Google AI Studio](https://aistudio.google.com/) 접속
2. Google 계정으로 로그인
3. "Get API Key" 클릭 → API Key 생성
4. **무료 — 신용카드 불필요**

### 비용 관리 전략

```python
# backend/app/core/config.py 에 설정
AI_CONFIG = {
    # 모델 설정
    "default_model": "gemini-3-flash-preview",        # 일반 요청용 (빠르고 무료 한도 넉넉)
    "advanced_model": "gemini-2.5-pro",          # 복잡한 추론용 (무료 한도 적음)
    "embedding_model": "gemini-embedding-001",   # 임베딩용

    # 생성 설정
    "max_output_tokens": 4096,           # 응답 최대 토큰
    "temperature": 0.7,                  # 창의성 수준

    # 사용량 제한 (무료 티어 보호)
    "daily_request_limit_per_user": 30,  # 사용자당 일일 AI 호출 제한
    "cache_ttl_seconds": 3600,           # 동일 요청 캐시 1시간
}
```

**무료 티어 최대 활용 방법:**
1. 기본 모델은 `gemini-3-flash-preview` 사용 (일 250회 허용, 충분)
2. 복잡한 코칭만 `gemini-2.5-pro` 사용 (일 25회 제한, 아껴서 사용)
3. 동일/유사한 요청에 Redis 캐싱
4. 사용자당 일일 AI 호출 횟수 제한
5. `ai_recommendations` 테이블에 사용량 기록 → 모니터링
6. 임베딩은 문서 등록 시 1회만 생성

---

## 3. LLM Gateway 구현 명세

### 파일 위치
```
backend/app/services/
├── ai_service.py      # LLM 호출 통합
└── rag_service.py     # RAG 파이프라인
```

### ai_service.py 구조

```python
"""
Codex 구현 가이드:
- Google Generative AI Python SDK (google-genai >= 1.33.0) 사용
- 비동기 호출 지원
- 모든 LLM 호출은 이 서비스를 통해서만 수행
- 호출 결과를 ai_recommendations 테이블에 저장
"""

import google.generativeai as genai

class AIService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.flash_model = genai.GenerativeModel("gemini-3-flash-preview")
        self.pro_model = genai.GenerativeModel("gemini-2.5-pro")

    async def analyze_food_image(self, image_bytes: bytes, mime_type: str) -> dict:
        """
        음식 사진 분석 - Gemini 2.5 Flash (Vision)

        Codex 구현 가이드:
        - image_bytes: 원본 이미지 바이트
        - mime_type: "image/jpeg" 또는 "image/png"
        - Gemini는 바이트를 직접 처리 가능 (base64 불필요)
        """
        image_part = {"mime_type": mime_type, "data": image_bytes}
        response = await self.flash_model.generate_content_async(
            [FOOD_ANALYSIS_PROMPT, image_part],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                max_output_tokens=1000,
                temperature=0.3,
            ),
        )
        return json.loads(response.text)

    async def recommend_diet(self, user_context: dict, rag_context: str) -> dict:
        """AI 식단 추천 - Gemini 2.5 Flash"""
        ...

    async def recommend_exercise(self, user_context: dict, rag_context: str) -> dict:
        """AI 운동 추천 - Gemini 2.5 Flash"""
        ...

    async def advanced_coaching(self, user_context: dict, rag_context: str) -> dict:
        """고급 AI 코칭 - Gemini 2.5 Pro (복잡한 추론 필요 시)"""
        ...
```

### Gemini vs OpenAI SDK 차이점 (Codex 참조)

| 항목 | Gemini SDK | OpenAI SDK |
|------|-----------|-----------|
| 패키지 | `google-genai` | `openai` |
| 초기화 | `genai.configure(api_key=...)` | `AsyncOpenAI(api_key=...)` |
| 모델 생성 | `genai.GenerativeModel("gemini-3-flash-preview")` | `client.chat.completions.create(model=...)` |
| 이미지 입력 | 바이트 직접 전달 `{"mime_type": ..., "data": ...}` | base64 인코딩 필요 |
| JSON 출력 | `response_mime_type="application/json"` | `response_format={"type": "json_object"}` |
| 비동기 호출 | `generate_content_async()` | `await client.chat.completions.create()` |
| 임베딩 | `genai.embed_content()` | `client.embeddings.create()` |

---

## 4. 프롬프트 템플릿

### 4-1. 음식 사진 분석 프롬프트

```
당신은 전문 영양사입니다. 음식 사진을 보고 아래 정보를 JSON 형식으로 추출하세요.

규칙:
1. 사진에 보이는 모든 음식을 개별적으로 분석하세요.
2. 각 음식의 종류, 대략적인 양, 영양소를 추정하세요.
3. 한국 음식에 특히 정확해야 합니다.
4. 확실하지 않은 경우 confidence를 낮게 설정하세요.

응답 JSON 형식:
{
  "foods": [
    {
      "food_name": "음식명 (한국어)",
      "serving_size": "대략적 양 (예: 1공기, 200g)",
      "calories": 숫자,
      "protein_g": 숫자,
      "carbs_g": 숫자,
      "fat_g": 숫자,
      "confidence": 0.0~1.0
    }
  ]
}
```

### 4-2. 식단 추천 프롬프트

```
당신은 AI 헬스 코치입니다. 사용자의 신체 정보, 목표, 오늘의 식단 기록을 보고
남은 영양소를 채울 수 있는 식단을 추천하세요.

규칙:
1. 사용자의 알레르기와 선호 식품을 반드시 고려하세요.
2. 실현 가능하고 구체적인 음식을 추천하세요.
3. 한국에서 쉽게 구할 수 있는 음식 위주로 추천하세요.
4. 추천 이유를 간결하게 설명하세요.
5. 아래 참고 자료를 활용하세요.

참고 자료 (RAG):
{rag_context}

---

[사용자 프로필]
- 키: {height_cm}cm, 몸무게: {weight_kg}kg
- 목표: {goal} ({goal_description})
- 활동 수준: {activity_level}
- 알레르기: {allergies}
- 선호 식품: {food_preferences}
- 목표 칼로리: {target_calories}kcal
- 목표 매크로: 단백질 {target_protein_g}g / 탄수화물 {target_carbs_g}g / 지방 {target_fat_g}g

[오늘 섭취 현황]
- 칼로리: {consumed_calories}kcal / {target_calories}kcal
- 단백질: {consumed_protein}g / {target_protein_g}g
- 탄수화물: {consumed_carbs}g / {target_carbs_g}g
- 지방: {consumed_fat}g / {target_fat_g}g

남은 영양소를 채울 수 있는 다음 식사를 추천해주세요.

응답 JSON 형식:
{
  "recommendation": "추천 설명 텍스트",
  "suggested_foods": [
    {
      "food_name": "음식명",
      "serving_size": "1인분",
      "calories": 숫자,
      "protein_g": 숫자,
      "carbs_g": 숫자,
      "fat_g": 숫자,
      "reason": "추천 이유"
    }
  ]
}
```

### 4-3. 운동 추천 프롬프트

```
당신은 AI 헬스 코치입니다. 사용자의 운동 목표와 과거 운동 기록을 분석하여
다음 운동 계획을 추천하세요.

규칙:
1. 점진적 과부하 원칙을 적용하세요 (무게 2.5~5% 증량 또는 반복 횟수 증가).
2. 근육군 밸런스를 고려하세요.
3. 사용자의 목표(벌크업/다이어트/유지)에 맞는 세트/반복 범위를 추천하세요.
4. 구체적인 수치(무게, 세트, 횟수)를 제시하세요.
5. 아래 참고 자료를 활용하여 근거 기반 추천을 하세요.

참고 자료 (RAG):
{rag_context}

목표별 가이드:
- 벌크업: 중량 위주 (3~6회 x 4~5세트), 점진적 증량
- 다이어트: 중간 무게 고반복 (12~15회 x 3~4세트), 슈퍼세트 활용
- 유지: 현재 중량 유지 (8~12회 x 3~4세트)

---

[사용자 정보]
- 목표: {goal}
- 체중: {weight_kg}kg

[최근 {muscle_group} 운동 기록 (최근 3회)]
{exercise_history}

다음 {muscle_group} 운동을 추천해주세요.

응답 JSON 형식:
{
  "recommendation": "전체 추천 설명",
  "suggested_exercises": [
    {
      "exercise_name": "운동명",
      "muscle_group": "근육군",
      "sets": 숫자,
      "reps": 숫자,
      "weight_kg": 숫자,
      "reason": "추천 이유"
    }
  ]
}
```

---

## 5. RAG 파이프라인 구현 명세

### 5-1. 임베딩과 검색 저장소

| 항목 | 선택 |
|------|------|
| 임베딩 모델 | `gemini-embedding-001` |
| 차원 | 3072 |
| PostgreSQL 컬럼 | `rag_chunks.embedding VECTOR(3072)` |
| Retrieval index | OpenSearch `rag_chunks_current` alias |
| Source of truth | PostgreSQL `rag_sources`, `rag_chunks` |

> **중요:** RAG v2의 기본 검색 경로는 OpenSearch hybrid retrieval이다.
> PostgreSQL/pgvector는 source of truth와 장애 fallback 역할을 맡는다.

### 5-2. 데이터 인제스트 단계

```
RAG 데이터 소스 (rag_data/ 폴더)
    │
    ├── 영양학 가이드라인 (.md, .txt)
    ├── 운동 과학 논문 요약 (.md, .txt)
    ├── 식품 영양 데이터 (.csv, .json)
    └── 근성장/다이어트 가이드 (.md, .txt)
    │
    ▼
[청킹] 문서를 500~1000자 단위로 분할
    │
    ▼
[임베딩] Gemini Embedding (`gemini-embedding-001`) → 3072차원 벡터
    │
    ▼
[저장] PostgreSQL rag_sources/rag_chunks 원장
    │
    ▼
[색인] OpenSearch rag_chunks_current retrieval index
```

### 5-3. 검색 단계

```python
"""
Codex 구현 가이드:
rag_service.py에 아래 로직 구현
"""

import google.generativeai as genai

class RAGService:
    async def get_embedding(self, text: str) -> list[float]:
        """Gemini 임베딩 생성"""
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
        )
        return result['embedding']  # 3072차원 벡터

    async def search(self, query: str, category: str = None, top_k: int = 3) -> list:
        """
        1. query를 gemini-embedding-001로 임베딩
        2. OpenSearch hybrid/vector 검색
        3. 장애 시 pgvector fallback
        4. retrieval trace 저장
        5. 상위 top_k개 문서 반환
        """
        query_embedding = await self.get_embedding(query)

        # SQL 예시:
        # SELECT id, title, content, 1 - (embedding <=> :query_vec) as similarity
        # FROM rag_chunks
        # WHERE category = :category (optional)
        # ORDER BY embedding <=> :query_vec
        # LIMIT :top_k;
        ...

    async def ingest_document(self, title: str, content: str, category: str, source: str):
        """
        1. content를 청크로 분할 (500~1000자)
        2. 각 청크를 gemini-embedding-001로 임베딩
        3. rag_sources/rag_chunks에 저장
        4. OpenSearch rag_chunks_current에 색인
        """
        ...
```

### 5-4. RAG 데이터 관리 CLI

```python
"""
Codex 구현 가이드:
backend/scripts/ingest_rag_data.py 로 CLI 스크립트 작성

사용법:
  python scripts/ingest_rag_data.py --dir rag_data/
  python scripts/ingest_rag_data.py --file rag_data/nutrition_guide.md --category nutrition
"""
```

---

## 6. AI 응답 파싱 가이드

### Gemini JSON 모드 활용

```python
"""
Codex 구현 가이드:
Gemini는 response_mime_type="application/json" 설정으로 JSON 출력을 강제할 수 있다.
이 설정을 사용하면 별도의 JSON 파싱 안전장치가 대부분 불필요하지만,
만약을 위한 폴백 로직도 구현한다.
"""

import json
import re

def parse_ai_response(response_text: str) -> dict:
    """
    1. Gemini JSON 모드 응답은 대부분 바로 파싱 가능
    2. 실패 시 정규식으로 JSON 블록 추출 시도
    3. 최종 실패 시 에러 처리
    """
    # 1차: 직접 파싱
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # 2차: ```json ... ``` 블록 추출
    match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # 3차: { ... } 블록 추출
    match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("AI 응답에서 JSON을 파싱할 수 없습니다.")
```

---

## 7. 에러 처리 및 폴백

| 상황 | 처리 |
|------|------|
| Gemini API 타임아웃 | 30초 타임아웃, 재시도 1회 |
| Gemini API 에러 (5xx) | 재시도 1회, 실패 시 503 반환 |
| Rate Limit (429) | 사용자에게 "잠시 후 다시 시도" 메시지 |
| 무료 티어 일일 한도 초과 | 429 반환, "일일 AI 사용 한도에 도달했습니다" |
| JSON 파싱 실패 | 재시도 1회 (JSON 모드 재요청) |
| 이미지 분석 실패 | "음식을 인식할 수 없습니다. 직접 입력해주세요" |
| Safety Filter 차단 | 프롬프트 수정 후 재시도, 실패 시 일반 응답 반환 |

> **Gemini 고유 주의사항:**
> Gemini는 Safety Filter가 있어 특정 콘텐츠를 차단할 수 있습니다.
> 음식/운동 추천은 건강 관련이므로 Safety 설정을 `BLOCK_ONLY_HIGH`로 설정하세요.

```python
# Safety 설정 예시
from google.generativeai.types import HarmCategory, HarmBlockThreshold

safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}
```
