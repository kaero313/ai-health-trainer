from unittest.mock import AsyncMock, patch

import pytest

MOCK_CHAT_RESULT = {
    "answer": "Reduce pork belly to 150g and add vegetables.",
    "context_used": {
        "profile_loaded": True,
        "today_diet_records": 2,
        "today_exercise_records": 0,
    },
    "sources": ["nutrition_basics"],
}


@pytest.mark.asyncio
@patch("app.api.v1.ai_chat.ChatService")
@patch("app.api.v1.ai_chat.RAGService")
@patch("app.api.v1.ai_chat.AIService")
async def test_chat_diet_context(
    mock_ai_class,
    mock_rag_class,
    mock_chat_class,
    client,
    register_and_get_token,
    auth_headers,
):
    _ = mock_rag_class
    mock_ai = mock_ai_class.return_value
    mock_ai.check_rate_limit = AsyncMock(return_value=False)

    mock_chat = mock_chat_class.return_value
    mock_chat.chat = AsyncMock(return_value=MOCK_CHAT_RESULT)

    token, _ = await register_and_get_token(client, "chat-diet@example.com")
    response = await client.post(
        "/api/v1/ai/chat",
        json={"message": "What should I eat today?", "context_type": "diet"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "Reduce pork belly" in body["data"]["answer"]


@pytest.mark.asyncio
@patch("app.api.v1.ai_chat.ChatService")
@patch("app.api.v1.ai_chat.RAGService")
@patch("app.api.v1.ai_chat.AIService")
async def test_chat_exercise_context(
    mock_ai_class,
    mock_rag_class,
    mock_chat_class,
    client,
    register_and_get_token,
    auth_headers,
):
    _ = mock_rag_class
    mock_ai = mock_ai_class.return_value
    mock_ai.check_rate_limit = AsyncMock(return_value=False)

    mock_chat = mock_chat_class.return_value
    mock_chat.chat = AsyncMock(return_value=MOCK_CHAT_RESULT)

    token, _ = await register_and_get_token(client, "chat-exercise@example.com")
    response = await client.post(
        "/api/v1/ai/chat",
        json={"message": "How should I train chest?", "context_type": "exercise"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["sources"] == ["nutrition_basics"]


@pytest.mark.asyncio
@patch("app.api.v1.ai_chat.ChatService")
@patch("app.api.v1.ai_chat.RAGService")
@patch("app.api.v1.ai_chat.AIService")
async def test_chat_general_context(
    mock_ai_class,
    mock_rag_class,
    mock_chat_class,
    client,
    register_and_get_token,
    auth_headers,
):
    _ = mock_rag_class
    mock_ai = mock_ai_class.return_value
    mock_ai.check_rate_limit = AsyncMock(return_value=False)

    mock_chat = mock_chat_class.return_value
    mock_chat.chat = AsyncMock(return_value=MOCK_CHAT_RESULT)

    token, _ = await register_and_get_token(client, "chat-general@example.com")
    response = await client.post(
        "/api/v1/ai/chat",
        json={"message": "Any health tips?", "context_type": "general"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["context_used"]["profile_loaded"] is True


@pytest.mark.asyncio
async def test_chat_without_auth(client):
    response = await client.post(
        "/api/v1/ai/chat",
        json={"message": "test", "context_type": "general"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
@patch("app.api.v1.ai_chat.ChatService")
@patch("app.api.v1.ai_chat.RAGService")
@patch("app.api.v1.ai_chat.AIService")
async def test_chat_rate_limited(
    mock_ai_class,
    mock_rag_class,
    mock_chat_class,
    client,
    register_and_get_token,
    auth_headers,
):
    _ = mock_rag_class
    _ = mock_chat_class
    mock_ai = mock_ai_class.return_value
    mock_ai.check_rate_limit = AsyncMock(return_value=True)

    token, _ = await register_and_get_token(client, "chat-rate-limit@example.com")
    response = await client.post(
        "/api/v1/ai/chat",
        json={"message": "test", "context_type": "general"},
        headers=auth_headers(token),
    )

    assert response.status_code == 429
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "DAILY_LIMIT_EXCEEDED"
