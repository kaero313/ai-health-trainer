import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["user"]["email"] == "user@example.com"
    assert payload["data"]["token_type"] == "bearer"
    assert payload["data"]["access_token"]
    assert payload["data"]["refresh_token"]


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_conflict(client):
    register_payload = {
        "email": "duplicate@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
    }

    first_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert first_response.status_code == 201

    second_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert second_response.status_code == 409
    error_payload = second_response.json()
    assert error_payload["status"] == "error"
    assert error_payload["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_register_weak_password_returns_validation_error(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "password": "12345678",
            "password_confirm": "12345678",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_register_password_confirm_mismatch_returns_validation_error(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "mismatch@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass456!",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_success(client):
    register_payload = {
        "email": "login-success@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login-success@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["token_type"] == "bearer"
    assert payload["data"]["access_token"]
    assert payload["data"]["refresh_token"]
    assert payload["data"]["expires_in"] == 1800


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_unauthorized(client):
    register_payload = {
        "email": "login-fail@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login-fail@example.com",
            "password": "WrongPass123!",
        },
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_refresh_success(client):
    register_payload = {
        "email": "refresh-success@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "refresh-success@example.com",
            "password": "SecurePass123!",
        },
    )
    refresh_token = login_response.json()["data"]["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["token_type"] == "bearer"
    assert payload["data"]["access_token"]
    assert payload["data"]["expires_in"] == 1800


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_unauthorized(client):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.value"},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "UNAUTHORIZED"
