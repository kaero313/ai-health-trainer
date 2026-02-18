from datetime import date, timedelta

import pytest


async def _setup_profile(client, token: str, auth_headers) -> dict[str, object]:
    response = await client.put(
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
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    return response.json()["data"]


async def _create_exercise(
    client,
    token: str,
    date_str: str,
    name: str,
    muscle_group: str,
    sets_data: list[dict[str, object]],
    auth_headers,
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/exercise/logs",
        json={
            "exercise_date": date_str,
            "exercise_name": name,
            "muscle_group": muscle_group,
            "sets": sets_data,
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()["data"]


async def _create_diet(
    client,
    token: str,
    date_str: str,
    meal_type: str,
    items_data: list[dict[str, object]],
    auth_headers,
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": date_str,
            "meal_type": meal_type,
            "items": items_data,
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()["data"]


@pytest.mark.asyncio
async def test_today_dashboard_empty(client, register_and_get_token, auth_headers):
    token, _ = await register_and_get_token(client, "dash-empty@example.com")
    await _setup_profile(client, token, auth_headers)
    today_str = date.today().isoformat()

    response = await client.get(
        "/api/v1/dashboard/today",
        params={"date": today_str},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    consumed = body["data"]["nutrition"]["consumed"]
    assert consumed["calories"] == 0.0
    assert consumed["protein_g"] == 0.0
    assert consumed["carbs_g"] == 0.0
    assert consumed["fat_g"] == 0.0
    assert body["data"]["exercise"]["completed"] is False
    assert body["data"]["streak"]["exercise_days"] == 0
    assert body["data"]["streak"]["diet_logging_days"] == 0


@pytest.mark.asyncio
async def test_today_dashboard_with_data(client, register_and_get_token, auth_headers):
    token, _ = await register_and_get_token(client, "dash-data@example.com")
    await _setup_profile(client, token, auth_headers)
    today_str = date.today().isoformat()

    await _create_exercise(
        client,
        token,
        today_str,
        "Bench Press",
        "chest",
        [
            {"set_number": 1, "reps": 10, "weight_kg": 60.0, "is_completed": True},
            {"set_number": 2, "reps": 8, "weight_kg": 62.5, "is_completed": True},
            {"set_number": 3, "reps": 6, "weight_kg": 65.0, "is_completed": True},
        ],
        auth_headers,
    )

    lunch_items = [
        {"food_name": "Chicken Salad", "calories": 350.0, "protein_g": 40.0, "carbs_g": 15.0, "fat_g": 12.0},
        {"food_name": "Brown Rice", "calories": 220.0, "protein_g": 5.0, "carbs_g": 45.0, "fat_g": 2.0},
    ]
    await _create_diet(client, token, today_str, "lunch", lunch_items, auth_headers)

    response = await client.get(
        "/api/v1/dashboard/today",
        params={"date": today_str},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    consumed = body["data"]["nutrition"]["consumed"]
    assert consumed["calories"] == 570.0
    assert body["data"]["exercise"]["completed"] is True
    assert body["data"]["exercise"]["total_sets"] == 3
    assert body["data"]["exercise"]["muscle_groups_trained"] == ["chest"]


@pytest.mark.asyncio
async def test_today_dashboard_progress_percent(client, register_and_get_token, auth_headers):
    token, _ = await register_and_get_token(client, "dash-progress@example.com")
    profile_data = await _setup_profile(client, token, auth_headers)
    today_str = date.today().isoformat()

    consumed_values = {
        "calories": 500.0,
        "protein_g": 50.0,
        "carbs_g": 40.0,
        "fat_g": 20.0,
    }
    await _create_diet(
        client,
        token,
        today_str,
        "lunch",
        [
            {
                "food_name": "Salad",
                "calories": consumed_values["calories"],
                "protein_g": consumed_values["protein_g"],
                "carbs_g": consumed_values["carbs_g"],
                "fat_g": consumed_values["fat_g"],
            }
        ],
        auth_headers,
    )

    response = await client.get(
        "/api/v1/dashboard/today",
        params={"date": today_str},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    progress = body["data"]["nutrition"]["progress_percent"]
    assert progress is not None

    expected_calories = round(consumed_values["calories"] / float(profile_data["target_calories"]) * 100, 1)
    expected_protein = round(consumed_values["protein_g"] / float(profile_data["target_protein_g"]) * 100, 1)
    expected_carbs = round(consumed_values["carbs_g"] / float(profile_data["target_carbs_g"]) * 100, 1)
    expected_fat = round(consumed_values["fat_g"] / float(profile_data["target_fat_g"]) * 100, 1)

    assert progress["calories"] == expected_calories
    assert progress["protein_g"] == expected_protein
    assert progress["carbs_g"] == expected_carbs
    assert progress["fat_g"] == expected_fat


@pytest.mark.asyncio
async def test_weekly_dashboard(client, register_and_get_token, auth_headers):
    token, _ = await register_and_get_token(client, "dash-weekly@example.com")
    await _setup_profile(client, token, auth_headers)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    active_days = {week_start, week_start + timedelta(days=2), week_start + timedelta(days=4)}

    for active_day in active_days:
        day_str = active_day.isoformat()
        await _create_exercise(
            client,
            token,
            day_str,
            "Squat",
            "legs",
            [{"set_number": 1, "reps": 8, "weight_kg": 100.0, "is_completed": True}],
            auth_headers,
        )
        await _create_diet(
            client,
            token,
            day_str,
            "lunch",
            [{"food_name": "Meal", "calories": 500.0, "protein_g": 40.0, "carbs_g": 50.0, "fat_g": 10.0}],
            auth_headers,
        )

    response = await client.get(
        "/api/v1/dashboard/weekly",
        params={"week_start": week_start.isoformat()},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["exercise_summary"]["total_days"] == 3
    assert len(body["data"]["daily_breakdown"]) == 7

    breakdown_by_date = {entry["date"]: entry for entry in body["data"]["daily_breakdown"]}
    for day_offset in range(7):
        current_date = (week_start + timedelta(days=day_offset)).isoformat()
        expected_exercised = current_date in {d.isoformat() for d in active_days}
        assert breakdown_by_date[current_date]["exercised"] is expected_exercised


@pytest.mark.asyncio
async def test_streak_calculation(client, register_and_get_token, auth_headers):
    token, _ = await register_and_get_token(client, "dash-streak@example.com")
    await _setup_profile(client, token, auth_headers)

    today = date.today()
    for day_offset in range(3):
        target_day = (today - timedelta(days=day_offset)).isoformat()
        await _create_exercise(
            client,
            token,
            target_day,
            "Pull Up",
            "back",
            [{"set_number": 1, "reps": 10, "weight_kg": None, "is_completed": True}],
            auth_headers,
        )

    response = await client.get(
        "/api/v1/dashboard/today",
        params={"date": today.isoformat()},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["streak"]["exercise_days"] == 3
