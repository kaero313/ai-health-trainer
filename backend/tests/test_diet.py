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
async def test_create_diet_log_success(client):
    access_token, _ = await _register_user_and_get_token(client, "diet-create@example.com")
    payload = {
        "log_date": "2026-02-17",
        "meal_type": "lunch",
        "image_url": None,
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
    }

    response = await client.post(
        "/api/v1/diet/logs",
        json=payload,
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["meal_type"] == "lunch"
    assert body["data"]["ai_analyzed"] is False
    assert len(body["data"]["items"]) == 2


@pytest.mark.asyncio
async def test_get_diet_logs_by_date_group_and_daily_total_without_profile(client):
    access_token, _ = await _register_user_and_get_token(client, "diet-list@example.com")
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
            }
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
    assert set(body["data"]["meals"].keys()) == {"breakfast", "lunch", "dinner", "snack"}
    assert len(body["data"]["meals"]["breakfast"]) == 1
    assert len(body["data"]["meals"]["lunch"]) == 1
    assert body["data"]["meals"]["dinner"] == []
    assert body["data"]["meals"]["snack"] == []
    assert body["data"]["daily_total"]["calories"] == 550.0
    assert body["data"]["daily_total"]["protein_g"] == 52.0
    assert body["data"]["daily_total"]["carbs_g"] == 50.0
    assert body["data"]["daily_total"]["fat_g"] == 11.0
    assert body["data"]["target_remaining"] is None


@pytest.mark.asyncio
async def test_get_diet_logs_target_remaining_with_profile(client):
    access_token, _ = await _register_user_and_get_token(client, "diet-target@example.com")

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
                    "serving_size": "1 bowl",
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
    assert remaining["calories"] == pytest.approx(targets["target_calories"] - 500.0, abs=0.01)
    assert remaining["protein_g"] == pytest.approx(targets["target_protein_g"] - 50.0, abs=0.01)
    assert remaining["carbs_g"] == pytest.approx(targets["target_carbs_g"] - 40.0, abs=0.01)
    assert remaining["fat_g"] == pytest.approx(targets["target_fat_g"] - 20.0, abs=0.01)


@pytest.mark.asyncio
async def test_update_diet_log_partial_and_replace_items(client):
    access_token, _ = await _register_user_and_get_token(client, "diet-update@example.com")

    create_response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [
                {
                    "food_name": "Food A",
                    "serving_size": "1",
                    "calories": 100.0,
                    "protein_g": 10.0,
                    "carbs_g": 10.0,
                    "fat_g": 1.0,
                },
                {
                    "food_name": "Food B",
                    "serving_size": "1",
                    "calories": 200.0,
                    "protein_g": 20.0,
                    "carbs_g": 20.0,
                    "fat_g": 2.0,
                },
            ],
        },
        headers=_auth_headers(access_token),
    )
    assert create_response.status_code == 201
    log_id = create_response.json()["data"]["id"]

    partial_response = await client.put(
        f"/api/v1/diet/logs/{log_id}",
        json={"meal_type": "dinner", "image_url": "https://example.com/image.jpg"},
        headers=_auth_headers(access_token),
    )
    assert partial_response.status_code == 200
    assert partial_response.json()["data"]["meal_type"] == "dinner"
    assert partial_response.json()["data"]["image_url"] == "https://example.com/image.jpg"
    assert len(partial_response.json()["data"]["items"]) == 2

    replace_response = await client.put(
        f"/api/v1/diet/logs/{log_id}",
        json={
            "items": [
                {
                    "food_name": "Food C",
                    "serving_size": "1",
                    "calories": 300.0,
                    "protein_g": 30.0,
                    "carbs_g": 30.0,
                    "fat_g": 3.0,
                }
            ]
        },
        headers=_auth_headers(access_token),
    )
    assert replace_response.status_code == 200
    assert len(replace_response.json()["data"]["items"]) == 1
    assert replace_response.json()["data"]["items"][0]["food_name"] == "Food C"


@pytest.mark.asyncio
async def test_delete_diet_log_success(client):
    access_token, _ = await _register_user_and_get_token(client, "diet-delete@example.com")
    create_response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "snack",
            "items": [
                {
                    "food_name": "Protein Bar",
                    "serving_size": "1 bar",
                    "calories": 210.0,
                    "protein_g": 20.0,
                    "carbs_g": 23.0,
                    "fat_g": 7.0,
                }
            ],
        },
        headers=_auth_headers(access_token),
    )
    log_id = create_response.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/diet/logs/{log_id}",
        headers=_auth_headers(access_token),
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "success"

    list_response = await client.get(
        "/api/v1/diet/logs",
        params={"date": "2026-02-17"},
        headers=_auth_headers(access_token),
    )
    assert list_response.status_code == 200
    assert list_response.json()["data"]["meals"]["snack"] == []


@pytest.mark.asyncio
async def test_update_and_delete_forbidden_for_other_user(client):
    owner_token, _ = await _register_user_and_get_token(client, "diet-owner@example.com")
    other_token, _ = await _register_user_and_get_token(client, "diet-other@example.com")

    create_response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [{"food_name": "Food", "calories": 100.0}],
        },
        headers=_auth_headers(owner_token),
    )
    log_id = create_response.json()["data"]["id"]

    update_response = await client.put(
        f"/api/v1/diet/logs/{log_id}",
        json={"meal_type": "dinner"},
        headers=_auth_headers(other_token),
    )
    assert update_response.status_code == 403
    assert update_response.json()["error"]["code"] == "FORBIDDEN"

    delete_response = await client.delete(
        f"/api/v1/diet/logs/{log_id}",
        headers=_auth_headers(other_token),
    )
    assert delete_response.status_code == 403
    assert delete_response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_update_and_delete_not_found(client):
    access_token, _ = await _register_user_and_get_token(client, "diet-notfound@example.com")

    update_response = await client.put(
        "/api/v1/diet/logs/999999",
        json={"meal_type": "dinner"},
        headers=_auth_headers(access_token),
    )
    assert update_response.status_code == 404
    assert update_response.json()["error"]["code"] == "NOT_FOUND"

    delete_response = await client.delete(
        "/api/v1/diet/logs/999999",
        headers=_auth_headers(access_token),
    )
    assert delete_response.status_code == 404
    assert delete_response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_diet_log_validation_error_for_empty_items(client):
    access_token, _ = await _register_user_and_get_token(client, "diet-invalid@example.com")

    response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [],
        },
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "VALIDATION_ERROR"
