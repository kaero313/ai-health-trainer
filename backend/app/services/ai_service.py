import asyncio
import json
import re
from datetime import datetime, timezone

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.ai_recommendation import AIRecommendation

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

FOOD_ANALYSIS_PROMPT = """당신은 전문 영양사입니다. 음식 사진을 보고 아래 정보를 JSON 형식으로 추출하세요.

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
"""

DIET_RECOMMEND_PROMPT = """당신은 AI 헬스 코치입니다. 사용자의 신체 정보, 목표, 오늘의 식단 기록을 보고 
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
"""

EXERCISE_RECOMMEND_PROMPT = """당신은 AI 헬스 코치입니다. 사용자의 운동 목표와 과거 운동 기록을 분석하여 
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
"""

CHAT_PROMPT = """당신은 AI 헬스 코치입니다. 사용자의 질문에 개인화된 답변을 제공합니다.
사용자 프로필과 기록 데이터를 참고하되, 질문 범위를 벗어나지 마세요.
답변은 한국어로, 구체적 수치를 포함하여 실용적으로 작성하세요.

참고 자료 (RAG):
{rag_context}

---

[사용자 정보]
{user_context}

[사용자 질문]
{user_message}

응답 JSON 형식:
{{"answer": "답변 텍스트", "sources": ["참고한 RAG 문서 제목"]}}"""


class AIServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class AIService:
    def __init__(self, settings: Settings) -> None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.flash_model = genai.GenerativeModel(settings.AI_DEFAULT_MODEL)
        self.pro_model = genai.GenerativeModel(settings.AI_ADVANCED_MODEL)
        self.settings = settings

    async def analyze_food_image(self, image_bytes: bytes, mime_type: str) -> dict:
        image_part = {"mime_type": mime_type, "data": image_bytes}
        contents = [FOOD_ANALYSIS_PROMPT, image_part]
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=self.settings.AI_MAX_OUTPUT_TOKENS,
            temperature=0.3,
        )
        parsed = await self._request_and_parse(self.flash_model, contents, generation_config)
        foods = parsed.get("foods")
        if not isinstance(foods, list) or len(foods) == 0:
            raise AIServiceError(400, "FOOD_NOT_RECOGNIZED", "음식을 인식할 수 없습니다")
        return parsed

    async def recommend_diet(self, user_context: dict, rag_context: str) -> dict:
        try:
            prompt = DIET_RECOMMEND_PROMPT.format(**user_context, rag_context=rag_context)
        except KeyError as exc:
            raise AIServiceError(503, "AI_SERVICE_ERROR", f"AI 서비스에 문제가 발생했습니다: {exc}") from exc

        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=self.settings.AI_MAX_OUTPUT_TOKENS,
            temperature=0.7,
        )
        return await self._request_and_parse(self.flash_model, [prompt], generation_config)

    async def recommend_exercise(self, user_context: dict, rag_context: str) -> dict:
        try:
            prompt = EXERCISE_RECOMMEND_PROMPT.format(**user_context, rag_context=rag_context)
        except KeyError as exc:
            raise AIServiceError(503, "AI_SERVICE_ERROR", f"AI 서비스에 문제가 발생했습니다: {exc}") from exc

        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=self.settings.AI_MAX_OUTPUT_TOKENS,
            temperature=0.7,
        )
        return await self._request_and_parse(self.flash_model, [prompt], generation_config)

    async def chat(self, user_message: str, user_context: str, rag_context: str) -> dict:
        prompt = CHAT_PROMPT.format(
            rag_context=rag_context,
            user_context=user_context,
            user_message=user_message,
        )
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=self.settings.AI_MAX_OUTPUT_TOKENS,
            temperature=0.7,
        )
        return await self._request_and_parse(self.flash_model, [prompt], generation_config)

    async def check_rate_limit(self, db: AsyncSession, user_id: int) -> bool:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count()).where(
            AIRecommendation.user_id == user_id,
            AIRecommendation.created_at >= today_start,
        )
        result = await db.execute(stmt)
        count = result.scalar_one()
        return count >= self.settings.AI_DAILY_REQUEST_LIMIT

    async def _request_and_parse(self, model, contents: list, generation_config, parse_retries: int = 1) -> dict:
        for attempt in range(parse_retries + 1):
            response_text = await self._call_with_retry(model, contents, generation_config)
            try:
                return self._parse_response(response_text)
            except AIServiceError as exc:
                if exc.code == "AI_PARSE_ERROR" and attempt < parse_retries:
                    continue
                raise
        raise AIServiceError(502, "AI_PARSE_ERROR", "AI 응답을 처리할 수 없습니다")

    def _parse_response(self, response_text: str) -> dict:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise AIServiceError(502, "AI_PARSE_ERROR", "AI 응답을 처리할 수 없습니다")

    async def _call_with_retry(self, model, contents: list, generation_config, max_retries: int = 1) -> str:
        for attempt in range(max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    model.generate_content_async(
                        contents,
                        generation_config=generation_config,
                        safety_settings=SAFETY_SETTINGS,
                    ),
                    timeout=30.0,
                )
                response_text = self._extract_response_text(response)
                if not response_text:
                    raise AIServiceError(400, "AI_BLOCKED", "AI가 해당 요청을 처리할 수 없습니다")
                return response_text
            except AIServiceError:
                raise
            except asyncio.TimeoutError as exc:
                if attempt < max_retries:
                    continue
                raise AIServiceError(503, "AI_TIMEOUT", "AI 서비스가 응답하지 않습니다") from exc
            except Exception as exc:
                message = str(exc)
                exc_name = type(exc).__name__
                if "429" in message or "ResourceExhausted" in exc_name:
                    raise AIServiceError(503, "AI_RATE_LIMITED", "AI 서비스가 일시적으로 제한되었습니다") from exc
                if attempt < max_retries:
                    continue
                raise AIServiceError(503, "AI_SERVICE_ERROR", f"AI 서비스에 문제가 발생했습니다: {exc}") from exc

        raise AIServiceError(503, "AI_SERVICE_ERROR", "AI 서비스에 문제가 발생했습니다")

    @staticmethod
    def _extract_response_text(response: object) -> str | None:
        try:
            text = getattr(response, "text", None)
        except Exception:
            return None
        if text is None:
            return None
        return str(text)
