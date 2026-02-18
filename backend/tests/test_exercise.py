from datetime import date

import pytest


async def _register_user_and_get_token(client, email: str) -> tuple[str, int]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
        },
    )
    assert response.status_code == 201
    payload = response.json()["data"]
    return payload["access_token"], payload["user"]["id"]


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.asyncio
async def test_create_exercise_log_success(client):
    access_token, _ = await _register_user_and_get_token(client, "exercise-create@example.com")
    payload = {
        "exercise_date": "2026-02-17",
        "exercise_name": "Bench Press",
        "muscle_group": "chest",
        "duration_min": 45,
        "memo": "Good session",
        "sets": [
            {"set_number": 1, "reps": 10, "weight_kg": 60.0, "is_completed": True},
            {"set_number": 2, "reps": 8, "weight_kg": 62.5, "is_completed": True},
        ],
    }

    response = await client.post(
        "/api/v1/exercise/logs",
        json=payload,
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["exercise_name"] == "Bench Press"
    assert body["data"]["muscle_group"] == "chest"
    assert len(body["data"]["sets"]) == 2
    assert body["data"]["sets"][0]["set_number"] == 1


@pytest.mark.asyncio
async def test_get_exercise_logs_by_date_returns_logs_and_muscle_groups(client):
    access_token, _ = await _register_user_and_get_token(client, "exercise-list@example.com")
    payload_one = {
        "exercise_date": "2026-02-17",
        "exercise_name": "Bench Press",
        "muscle_group": "chest",
        "sets": [{"set_number": 1, "reps": 10, "weight_kg": 60.0, "is_completed": True}],
    }
    payload_two = {
        "exercise_date": "2026-02-17",
        "exercise_name": "Barbell Row",
        "muscle_group": "back",
        "sets": [{"set_number": 1, "reps": 12, "weight_kg": 50.0, "is_completed": True}],
    }

    await client.post("/api/v1/exercise/logs", json=payload_one, headers=_auth_headers(access_token))
    await client.post("/api/v1/exercise/logs", json=payload_two, headers=_auth_headers(access_token))

    response = await client.get(
        "/api/v1/exercise/logs",
        params={"date": "2026-02-17"},
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["date"] == "2026-02-17"
    assert len(body["data"]["exercises"]) == 2
    assert set(body["data"]["muscle_groups_trained"]) == {"chest", "back"}


@pytest.mark.asyncio
async def test_update_exercise_log_partial_success(client):
    access_token, _ = await _register_user_and_get_token(client, "exercise-update-partial@example.com")
    create_payload = {
        "exercise_date": "2026-02-17",
        "exercise_name": "Squat",
        "muscle_group": "legs",
        "duration_min": 40,
        "memo": "Initial memo",
        "sets": [{"set_number": 1, "reps": 8, "weight_kg": 80.0, "is_completed": True}],
    }
    create_response = await client.post(
        "/api/v1/exercise/logs",
        json=create_payload,
        headers=_auth_headers(access_token),
    )
    log_id = create_response.json()["data"]["id"]

    update_response = await client.put(
        f"/api/v1/exercise/logs/{log_id}",
        json={"memo": "Updated memo", "duration_min": 50},
        headers=_auth_headers(access_token),
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["status"] == "success"
    assert body["data"]["memo"] == "Updated memo"
    assert body["data"]["duration_min"] == 50
    assert len(body["data"]["sets"]) == 1


@pytest.mark.asyncio
async def test_update_exercise_log_replace_sets_success(client):
    access_token, _ = await _register_user_and_get_token(client, "exercise-update-sets@example.com")
    create_payload = {
        "exercise_date": "2026-02-17",
        "exercise_name": "Overhead Press",
        "muscle_group": "shoulder",
        "sets": [
            {"set_number": 1, "reps": 10, "weight_kg": 30.0, "is_completed": True},
            {"set_number": 2, "reps": 8, "weight_kg": 32.5, "is_completed": True},
        ],
    }
    create_response = await client.post(
        "/api/v1/exercise/logs",
        json=create_payload,
        headers=_auth_headers(access_token),
    )
    log_id = create_response.json()["data"]["id"]

    update_response = await client.put(
        f"/api/v1/exercise/logs/{log_id}",
        json={
            "sets": [{"set_number": 1, "reps": 12, "weight_kg": 27.5, "is_completed": True}],
            "memo": "Replaced sets",
        },
        headers=_auth_headers(access_token),
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["status"] == "success"
    assert body["data"]["memo"] == "Replaced sets"
    assert len(body["data"]["sets"]) == 1
    assert body["data"]["sets"][0]["reps"] == 12
    assert body["data"]["sets"][0]["weight_kg"] == 27.5


@pytest.mark.asyncio
async def test_delete_exercise_log_success(client):
    access_token, _ = await _register_user_and_get_token(client, "exercise-delete@example.com")
    create_payload = {
        "exercise_date": "2026-02-17",
        "exercise_name": "Deadlift",
        "muscle_group": "back",
        "sets": [{"set_number": 1, "reps": 5, "weight_kg": 120.0, "is_completed": True}],
    }
    create_response = await client.post(
        "/api/v1/exercise/logs",
        json=create_payload,
        headers=_auth_headers(access_token),
    )
    log_id = create_response.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/exercise/logs/{log_id}",
        headers=_auth_headers(access_token),
    )

    assert delete_response.status_code == 200
    delete_body = delete_response.json()
    assert delete_body["status"] == "success"

    list_response = await client.get(
        "/api/v1/exercise/logs",
        params={"date": "2026-02-17"},
        headers=_auth_headers(access_token),
    )
    assert list_response.status_code == 200
    assert list_response.json()["data"]["exercises"] == []


@pytest.mark.asyncio
async def test_update_and_delete_forbidden_for_other_user(client):
    owner_token, _ = await _register_user_and_get_token(client, "exercise-owner@example.com")
    other_token, _ = await _register_user_and_get_token(client, "exercise-other@example.com")
    create_payload = {
        "exercise_date": "2026-02-17",
        "exercise_name": "Pull Up",
        "muscle_group": "back",
        "sets": [{"set_number": 1, "reps": 10, "weight_kg": None, "is_completed": True}],
    }
    create_response = await client.post(
        "/api/v1/exercise/logs",
        json=create_payload,
        headers=_auth_headers(owner_token),
    )
    log_id = create_response.json()["data"]["id"]

    update_response = await client.put(
        f"/api/v1/exercise/logs/{log_id}",
        json={"memo": "Malicious update"},
        headers=_auth_headers(other_token),
    )
    assert update_response.status_code == 403
    assert update_response.json()["error"]["code"] == "FORBIDDEN"

    delete_response = await client.delete(
        f"/api/v1/exercise/logs/{log_id}",
        headers=_auth_headers(other_token),
    )
    assert delete_response.status_code == 403
    assert delete_response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_update_and_delete_not_found(client):
    access_token, _ = await _register_user_and_get_token(client, "exercise-notfound@example.com")

    update_response = await client.put(
        "/api/v1/exercise/logs/999999",
        json={"memo": "No log"},
        headers=_auth_headers(access_token),
    )
    assert update_response.status_code == 404
    assert update_response.json()["error"]["code"] == "NOT_FOUND"

    delete_response = await client.delete(
        "/api/v1/exercise/logs/999999",
        headers=_auth_headers(access_token),
    )
    assert delete_response.status_code == 404
    assert delete_response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_history_by_muscle_with_progress(client):
    access_token, _ = await _register_user_and_get_token(client, "exercise-history@example.com")

    logs = [
        {
            "exercise_date": "2026-02-17",
            "exercise_name": "Bench Press",
            "muscle_group": "chest",
            "sets": [
                {"set_number": 1, "reps": 10, "weight_kg": 60.0, "is_completed": True},
                {"set_number": 2, "reps": 10, "weight_kg": 57.5, "is_completed": True},
            ],
        },
        {
            "exercise_date": "2026-02-17",
            "exercise_name": "Dumbbell Fly",
            "muscle_group": "chest",
            "sets": [
                {"set_number": 1, "reps": 12, "weight_kg": 14.0, "is_completed": True},
                {"set_number": 2, "reps": 12, "weight_kg": 14.0, "is_completed": True},
            ],
        },
        {
            "exercise_date": "2026-02-14",
            "exercise_name": "Bench Press",
            "muscle_group": "chest",
            "sets": [
                {"set_number": 1, "reps": 10, "weight_kg": 57.5, "is_completed": True},
                {"set_number": 2, "reps": 10, "weight_kg": 55.0, "is_completed": True},
            ],
        },
    ]

    for payload in logs:
        create_response = await client.post(
            "/api/v1/exercise/logs",
            json=payload,
            headers=_auth_headers(access_token),
        )
        assert create_response.status_code == 201

    history_response = await client.get(
        "/api/v1/exercise/history/chest",
        params={"limit": 10},
        headers=_auth_headers(access_token),
    )

    assert history_response.status_code == 200
    body = history_response.json()
    assert body["status"] == "success"
    assert body["data"]["muscle_group"] == "chest"
    assert len(body["data"]["history"]) == 2
    assert body["data"]["history"][0]["date"] == str(date(2026, 2, 17))
    assert len(body["data"]["history"][0]["exercises"]) == 2
    assert body["data"]["progress"]["Bench Press"]["weight_change"] == "+2.5kg"
    assert body["data"]["progress"]["Bench Press"]["trend"] == "increasing"


@pytest.mark.asyncio
async def test_create_exercise_log_validation_error_for_empty_sets(client):
    access_token, _ = await _register_user_and_get_token(client, "exercise-invalid@example.com")

    response = await client.post(
        "/api/v1/exercise/logs",
        json={
            "exercise_date": "2026-02-17",
            "exercise_name": "Bench Press",
            "muscle_group": "chest",
            "sets": [],
        },
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "VALIDATION_ERROR"
