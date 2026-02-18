from datetime import date

import pytest


@pytest.mark.asyncio
async def test_create_exercise_log_success(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "ex-create@example.com")

    response = await client.post(
        "/api/v1/exercise/logs",
        json={
            "exercise_date": "2026-02-17",
            "exercise_name": "Bench Press",
            "muscle_group": "chest",
            "duration_min": 45,
            "memo": "main lift",
            "sets": [
                {"set_number": 1, "reps": 10, "weight_kg": 60.0, "is_completed": True},
                {"set_number": 2, "reps": 8, "weight_kg": 62.5, "is_completed": True},
                {"set_number": 3, "reps": 6, "weight_kg": 65.0, "is_completed": True},
            ],
        },
        headers=auth_headers(access_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["exercise_name"] == "Bench Press"
    assert len(body["data"]["sets"]) == 3


@pytest.mark.asyncio
async def test_create_exercise_log_without_auth_returns_401(client):
    response = await client.post(
        "/api/v1/exercise/logs",
        json={
            "exercise_date": "2026-02-17",
            "exercise_name": "Squat",
            "muscle_group": "legs",
            "sets": [{"set_number": 1, "reps": 8, "weight_kg": 100.0, "is_completed": True}],
        },
    )

    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_get_exercise_logs_by_date(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "ex-get@example.com")

    payloads = [
        {
            "exercise_date": "2026-02-17",
            "exercise_name": "Bench Press",
            "muscle_group": "chest",
            "sets": [{"set_number": 1, "reps": 10, "weight_kg": 60.0, "is_completed": True}],
        },
        {
            "exercise_date": "2026-02-17",
            "exercise_name": "Barbell Row",
            "muscle_group": "back",
            "sets": [{"set_number": 1, "reps": 12, "weight_kg": 50.0, "is_completed": True}],
        },
    ]
    for payload in payloads:
        create_response = await client.post(
            "/api/v1/exercise/logs",
            json=payload,
            headers=auth_headers(access_token),
        )
        assert create_response.status_code == 201

    response = await client.get(
        "/api/v1/exercise/logs",
        params={"date": "2026-02-17"},
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert len(body["data"]["exercises"]) == 2


@pytest.mark.asyncio
async def test_get_exercise_logs_empty_date(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "ex-empty@example.com")

    response = await client.get(
        "/api/v1/exercise/logs",
        params={"date": "2026-02-20"},
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["exercises"] == []


@pytest.mark.asyncio
async def test_update_exercise_log_success(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "ex-update@example.com")
    create_response = await client.post(
        "/api/v1/exercise/logs",
        json={
            "exercise_date": "2026-02-17",
            "exercise_name": "Overhead Press",
            "muscle_group": "shoulder",
            "sets": [
                {"set_number": 1, "reps": 10, "weight_kg": 30.0, "is_completed": True},
                {"set_number": 2, "reps": 8, "weight_kg": 32.5, "is_completed": True},
            ],
        },
        headers=auth_headers(access_token),
    )
    assert create_response.status_code == 201
    log_id = create_response.json()["data"]["id"]

    update_response = await client.put(
        f"/api/v1/exercise/logs/{log_id}",
        json={
            "exercise_name": "Seated Overhead Press",
            "sets": [
                {"set_number": 1, "reps": 12, "weight_kg": 27.5, "is_completed": True},
                {"set_number": 2, "reps": 10, "weight_kg": 30.0, "is_completed": True},
            ],
        },
        headers=auth_headers(access_token),
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["status"] == "success"
    assert body["data"]["exercise_name"] == "Seated Overhead Press"
    assert len(body["data"]["sets"]) == 2
    assert body["data"]["sets"][0]["reps"] == 12


@pytest.mark.asyncio
async def test_update_other_users_log_returns_403(client, register_and_get_token, auth_headers):
    owner_token, _ = await register_and_get_token(client, "ex-owner@example.com")
    other_token, _ = await register_and_get_token(client, "ex-other@example.com")

    create_response = await client.post(
        "/api/v1/exercise/logs",
        json={
            "exercise_date": "2026-02-17",
            "exercise_name": "Deadlift",
            "muscle_group": "back",
            "sets": [{"set_number": 1, "reps": 5, "weight_kg": 120.0, "is_completed": True}],
        },
        headers=auth_headers(owner_token),
    )
    assert create_response.status_code == 201
    log_id = create_response.json()["data"]["id"]

    update_response = await client.put(
        f"/api/v1/exercise/logs/{log_id}",
        json={"exercise_name": "Hacked"},
        headers=auth_headers(other_token),
    )

    assert update_response.status_code == 403
    body = update_response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_delete_exercise_log_success(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "ex-delete@example.com")
    create_response = await client.post(
        "/api/v1/exercise/logs",
        json={
            "exercise_date": "2026-02-17",
            "exercise_name": "Pull Up",
            "muscle_group": "back",
            "sets": [{"set_number": 1, "reps": 10, "weight_kg": None, "is_completed": True}],
        },
        headers=auth_headers(access_token),
    )
    assert create_response.status_code == 201
    log_id = create_response.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/exercise/logs/{log_id}",
        headers=auth_headers(access_token),
    )
    assert delete_response.status_code == 200

    list_response = await client.get(
        "/api/v1/exercise/logs",
        params={"date": "2026-02-17"},
        headers=auth_headers(access_token),
    )
    assert list_response.status_code == 200
    exercises = list_response.json()["data"]["exercises"]
    assert all(exercise["id"] != log_id for exercise in exercises)


@pytest.mark.asyncio
async def test_get_muscle_history(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "ex-history@example.com")

    payloads = [
        {
            "exercise_date": "2026-02-17",
            "exercise_name": "Bench Press",
            "muscle_group": "chest",
            "sets": [{"set_number": 1, "reps": 10, "weight_kg": 60.0, "is_completed": True}],
        },
        {
            "exercise_date": "2026-02-14",
            "exercise_name": "Bench Press",
            "muscle_group": "chest",
            "sets": [{"set_number": 1, "reps": 10, "weight_kg": 57.5, "is_completed": True}],
        },
    ]
    for payload in payloads:
        create_response = await client.post(
            "/api/v1/exercise/logs",
            json=payload,
            headers=auth_headers(access_token),
        )
        assert create_response.status_code == 201

    history_response = await client.get(
        "/api/v1/exercise/history/chest",
        headers=auth_headers(access_token),
    )

    assert history_response.status_code == 200
    body = history_response.json()
    assert body["status"] == "success"
    assert body["data"]["muscle_group"] == "chest"
    assert len(body["data"]["history"]) == 2
    history_dates = [entry["date"] for entry in body["data"]["history"]]
    assert str(date(2026, 2, 17)) in history_dates
    assert str(date(2026, 2, 14)) in history_dates
