from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai_service import AIInvocationResult, FOOD_ANALYSIS_SCHEMA_VERSION
from app.services.ai_quota_service import AIQuotaError

MOCK_ANALYSIS = {
    "foods": [
        {
            "food_name": "kimchi_stew",
            "serving_size": "1 bowl",
            "calories": 200,
            "protein_g": 12,
            "carbs_g": 10,
            "fat_g": 13,
            "confidence": 0.85,
        }
    ],
    "total": {
        "calories": 200,
        "protein_g": 12,
        "carbs_g": 10,
        "fat_g": 13,
    },
}

MOCK_INVOCATION = AIInvocationResult(
    payload={"foods": MOCK_ANALYSIS["foods"]},
    model="gemini-test",
    response_schema_version=FOOD_ANALYSIS_SCHEMA_VERSION,
    response_id="food-response-id",
    tokens_input=10,
    tokens_output=20,
    finish_reason="STOP",
    latency_ms=25,
    raw_response_hash="a" * 64,
)


@pytest.mark.asyncio
@patch("app.api.v1.diet.AIService")
async def test_analyze_food_image_success(mock_ai_class, client, register_and_get_token, auth_headers):
    mock_ai = mock_ai_class.return_value
    mock_ai.analyze_food_image = AsyncMock(return_value=MOCK_INVOCATION)
    mock_ai.check_rate_limit = AsyncMock(return_value=False)
    mock_ai.start_generation_trace = AsyncMock(
        return_value=SimpleNamespace(id=101)
    )
    mock_ai.complete_generation_trace = AsyncMock(return_value=True)

    token, _ = await register_and_get_token(client, "food-analysis-success@example.com")
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 128

    response = await client.post(
        "/api/v1/diet/analyze-image",
        files={"image": ("test.jpg", fake_jpeg, "image/jpeg")},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert len(body["data"]["foods"]) == 1
    assert body["data"]["foods"][0]["food_name"] == "kimchi_stew"
    assert mock_ai.start_generation_trace.await_count == 1
    assert mock_ai.complete_generation_trace.await_count == 1
    assert "attempt_recorder" in mock_ai.analyze_food_image.await_args.kwargs


@pytest.mark.asyncio
@patch("app.api.v1.diet.AIService")
async def test_analyze_invalid_file_type(mock_ai_class, client, register_and_get_token, auth_headers):
    mock_ai = mock_ai_class.return_value
    mock_ai.check_rate_limit = AsyncMock(return_value=False)

    token, _ = await register_and_get_token(client, "food-analysis-invalid-type@example.com")
    fake_pdf = b"%PDF-1.7\n" + b"\x00" * 64

    response = await client.post(
        "/api/v1/diet/analyze-image",
        files={"image": ("test.pdf", fake_pdf, "application/pdf")},
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
@patch("app.api.v1.diet.AIService")
async def test_analyze_oversized_image(mock_ai_class, client, register_and_get_token, auth_headers):
    mock_ai = mock_ai_class.return_value
    mock_ai.check_rate_limit = AsyncMock(return_value=False)

    token, _ = await register_and_get_token(client, "food-analysis-oversized@example.com")
    oversized_image = b"\xff\xd8\xff\xe0" + b"\x00" * (11 * 1024 * 1024)

    response = await client.post(
        "/api/v1/diet/analyze-image",
        files={"image": ("big.jpg", oversized_image, "image/jpeg")},
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_analyze_without_auth(client):
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 128
    response = await client.post(
        "/api/v1/diet/analyze-image",
        files={"image": ("test.jpg", fake_jpeg, "image/jpeg")},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
@patch("app.api.v1.diet.AIService")
async def test_analyze_rate_limited(
    mock_ai_class,
    client,
    register_and_get_token,
    auth_headers,
    quota_service,
):
    mock_ai = mock_ai_class.return_value
    mock_ai.analyze_food_image = AsyncMock(return_value=MOCK_INVOCATION)
    mock_ai.start_generation_trace = AsyncMock(return_value=SimpleNamespace(id=901))
    quota_service.reserve.side_effect = AIQuotaError(
        429,
        "DAILY_LIMIT_EXCEEDED",
        "일일 AI 사용 한도에 도달했습니다",
        stage="quota_admission",
    )

    token, _ = await register_and_get_token(client, "food-analysis-rate-limit@example.com")
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 128
    response = await client.post(
        "/api/v1/diet/analyze-image",
        files={"image": ("test.jpg", fake_jpeg, "image/jpeg")},
        headers=auth_headers(token),
    )

    assert response.status_code == 429
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "DAILY_LIMIT_EXCEEDED"
