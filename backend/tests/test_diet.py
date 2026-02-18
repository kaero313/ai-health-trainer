import pytest


async def _register_and_get_token(client, email: str) -> tuple[str, int]:
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


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_diet_log_success(client):
    access_token, _ = await _register_and_get_token(client, "diet-create@example.com")

    response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [
                {
                    "food_name": "Chicken Salad",
                    "serving_size": "1 bowl",
                    "calories": 350.0,
                    "protein_g": 40.0,
                    "carbs_g": 15.0,
                    "fat_g": 12.0,
                },
                {
                    "food_name": "Brown Rice",
                    "serving_size": "1 cup",
                    "calories": 220.0,
                    "protein_g": 5.0,
                    "carbs_g": 45.0,
                    "fat_g": 2.0,
                },
            ],
        },
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["meal_type"] == "lunch"
    assert len(body["data"]["items"]) == 2


@pytest.mark.asyncio
async def test_create_diet_log_without_auth_returns_401(client):
    response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [{"food_name": "Food", "calories": 100.0}],
        },
    )

    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_get_diet_logs_by_date_with_daily_total(client):
    access_token, _ = await _register_and_get_token(client, "diet-get-total@example.com")

    breakfast_payload = {
        "log_date": "2026-02-17",
        "meal_type": "breakfast",
        "items": [
            {
                "food_name": "Oatmeal",
                "serving_size": "1 bowl",
                "calories": 300.0,
                "protein_g": 12.0,
                "carbs_g": 50.0,
                "fat_g": 6.0,
            }
        ],
    }
    lunch_payload = {
        "log_date": "2026-02-17",
        "meal_type": "lunch",
        "items": [
            {
                "food_name": "Chicken Breast",
                "serving_size": "150g",
                "calories": 250.0,
                "protein_g": 40.0,
                "carbs_g": 0.0,
                "fat_g": 5.0,
            },
            {
                "food_name": "Rice",
                "serving_size": "1 cup",
                "calories": 210.0,
                "protein_g": 4.0,
                "carbs_g": 45.0,
                "fat_g": 1.0,
            },
        ],
    }

    await client.post("/api/v1/diet/logs", json=breakfast_payload, headers=_auth_headers(access_token))
    await client.post("/api/v1/diet/logs", json=lunch_payload, headers=_auth_headers(access_token))

    response = await client.get(
        "/api/v1/diet/logs",
        params={"date": "2026-02-17"},
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert len(body["data"]["meals"]["breakfast"]) == 1
    assert len(body["data"]["meals"]["lunch"]) == 1
    assert body["data"]["daily_total"]["calories"] == 760.0
    assert body["data"]["daily_total"]["protein_g"] == 56.0
    assert body["data"]["daily_total"]["carbs_g"] == 95.0
    assert body["data"]["daily_total"]["fat_g"] == 12.0


@pytest.mark.asyncio
async def test_get_diet_logs_with_target_remaining(client):
    access_token, _ = await _register_and_get_token(client, "diet-target@example.com")

    profile_response = await client.put(
        "/api/v1/profile",
        json={
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "age": 28,
            "gender": "male",
            "goal": "bulk",
            "activity_level": "moderate",
            "allergies": [],
            "food_preferences": [],
        },
        headers=_auth_headers(access_token),
    )
    assert profile_response.status_code == 200
    targets = profile_response.json()["data"]

    await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [
                {
                    "food_name": "Salad",
                    "calories": 500.0,
                    "protein_g": 50.0,
                    "carbs_g": 40.0,
                    "fat_g": 20.0,
                }
            ],
        },
        headers=_auth_headers(access_token),
    )

    response = await client.get(
        "/api/v1/diet/logs",
        params={"date": "2026-02-17"},
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    remaining = body["data"]["target_remaining"]
    assert remaining is not None
    assert remaining["calories"] == round(float(targets["target_calories"]) - 500.0, 1)
    assert remaining["protein_g"] == round(float(targets["target_protein_g"]) - 50.0, 1)
    assert remaining["carbs_g"] == round(float(targets["target_carbs_g"]) - 40.0, 1)
    assert remaining["fat_g"] == round(float(targets["target_fat_g"]) - 20.0, 1)


@pytest.mark.asyncio
async def test_get_diet_logs_without_profile_target_remaining_null(client):
    access_token, _ = await _register_and_get_token(client, "diet-no-profile@example.com")

    await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "breakfast",
            "items": [{"food_name": "Egg", "calories": 150.0}],
        },
        headers=_auth_headers(access_token),
    )

    response = await client.get(
        "/api/v1/diet/logs",
        params={"date": "2026-02-17"},
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["target_remaining"] is None


@pytest.mark.asyncio
async def test_update_diet_log_success(client):
    access_token, _ = await _register_and_get_token(client, "diet-update@example.com")
    create_response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [
                {"food_name": "Food A", "calories": 100.0, "protein_g": 10.0, "carbs_g": 10.0, "fat_g": 1.0},
                {"food_name": "Food B", "calories": 200.0, "protein_g": 20.0, "carbs_g": 20.0, "fat_g": 2.0},
            ],
        },
        headers=_auth_headers(access_token),
    )
    assert create_response.status_code == 201
    log_id = create_response.json()["data"]["id"]

    update_response = await client.put(
        f"/api/v1/diet/logs/{log_id}",
        json={
            "items": [
                {
                    "food_name": "Food C",
                    "calories": 300.0,
                    "protein_g": 30.0,
                    "carbs_g": 30.0,
                    "fat_g": 3.0,
                }
            ]
        },
        headers=_auth_headers(access_token),
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["status"] == "success"
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["food_name"] == "Food C"


@pytest.mark.asyncio
async def test_update_other_users_log_returns_403(client):
    owner_token, _ = await _register_and_get_token(client, "diet-owner@example.com")
    other_token, _ = await _register_and_get_token(client, "diet-other@example.com")

    create_response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [{"food_name": "Owner Food", "calories": 100.0}],
        },
        headers=_auth_headers(owner_token),
    )
    assert create_response.status_code == 201
    log_id = create_response.json()["data"]["id"]

    update_response = await client.put(
        f"/api/v1/diet/logs/{log_id}",
        json={"meal_type": "dinner"},
        headers=_auth_headers(other_token),
    )

    assert update_response.status_code == 403
    body = update_response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_delete_diet_log_success(client):
    access_token, _ = await _register_and_get_token(client, "diet-delete@example.com")
    create_response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "snack",
            "items": [{"food_name": "Protein Bar", "calories": 210.0}],
        },
        headers=_auth_headers(access_token),
    )
    assert create_response.status_code == 201
    log_id = create_response.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/diet/logs/{log_id}",
        headers=_auth_headers(access_token),
    )

    assert delete_response.status_code == 200
    body = delete_response.json()
    assert body["status"] == "success"
