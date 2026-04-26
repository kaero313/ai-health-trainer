import pytest

from app.models.diet import FoodCatalogItem


@pytest.mark.asyncio
async def test_create_diet_log_success(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "diet-create@example.com")

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
        headers=auth_headers(access_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["meal_type"] == "lunch"
    assert len(body["data"]["items"]) == 2
    assert body["data"]["items"][0]["food_catalog_item_id"] is None
    assert body["data"]["items"][0]["serving_grams"] is None
    assert body["data"]["items"][0]["sugar_g"] is None
    assert body["data"]["items"][0]["saturated_fat_g"] is None
    assert body["data"]["items"][0]["unsaturated_fat_g"] is None


@pytest.mark.asyncio
async def test_create_diet_log_with_catalog_and_optional_nutrients(
    client,
    db_session,
    register_and_get_token,
    auth_headers,
):
    access_token, _ = await register_and_get_token(
        client,
        "diet-catalog-create@example.com",
    )
    catalog_item = FoodCatalogItem(
        name="닭가슴살",
        aliases=["chicken breast", "닭가슴"],
        category="protein",
        calories=165.0,
        protein_g=31.0,
        carbs_g=0.0,
        fat_g=3.6,
        sugar_g=0.0,
        saturated_fat_g=1.0,
        unsaturated_fat_g=2.0,
    )
    db_session.add(catalog_item)
    await db_session.commit()

    response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [
                {
                    "food_catalog_item_id": catalog_item.id,
                    "food_name": "닭가슴살",
                    "serving_size": "150g",
                    "serving_grams": 150.0,
                    "calories": 247.5,
                    "protein_g": 46.5,
                    "carbs_g": 0.0,
                    "fat_g": 5.4,
                    "sugar_g": 0.0,
                    "saturated_fat_g": 1.5,
                    "unsaturated_fat_g": 3.0,
                }
            ],
        },
        headers=auth_headers(access_token),
    )

    assert response.status_code == 201
    item = response.json()["data"]["items"][0]
    assert item["food_catalog_item_id"] == catalog_item.id
    assert item["serving_grams"] == 150.0
    assert item["sugar_g"] == 0.0
    assert item["saturated_fat_g"] == 1.5
    assert item["unsaturated_fat_g"] == 3.0


@pytest.mark.asyncio
async def test_search_food_catalog_by_name_alias_limit_and_active(
    client,
    db_session,
    register_and_get_token,
    auth_headers,
):
    access_token, _ = await register_and_get_token(
        client,
        "diet-food-search@example.com",
    )
    db_session.add_all(
        [
            FoodCatalogItem(
                name="닭가슴살",
                aliases=["chicken breast", "닭가슴"],
                category="protein",
                calories=165.0,
                protein_g=31.0,
                carbs_g=0.0,
                fat_g=3.6,
                sugar_g=0.0,
                saturated_fat_g=1.0,
                unsaturated_fat_g=2.0,
            ),
            FoodCatalogItem(
                name="현미밥",
                aliases=["brown rice"],
                category="carb",
                calories=112.0,
                protein_g=2.6,
                carbs_g=23.0,
                fat_g=0.9,
                sugar_g=0.4,
                saturated_fat_g=0.2,
                unsaturated_fat_g=0.6,
            ),
            FoodCatalogItem(
                name="비활성 음식",
                aliases=["inactive food"],
                category="meal",
                calories=100.0,
                protein_g=1.0,
                carbs_g=1.0,
                fat_g=1.0,
                is_active=False,
            ),
        ]
    )
    await db_session.commit()

    name_response = await client.get(
        "/api/v1/diet/foods",
        params={"query": "닭가", "limit": 1},
        headers=auth_headers(access_token),
    )
    assert name_response.status_code == 200
    assert [item["name"] for item in name_response.json()["data"]] == ["닭가슴살"]

    alias_response = await client.get(
        "/api/v1/diet/foods",
        params={"query": "brown", "limit": 10},
        headers=auth_headers(access_token),
    )
    assert alias_response.status_code == 200
    assert [item["name"] for item in alias_response.json()["data"]] == ["현미밥"]

    empty_query_response = await client.get(
        "/api/v1/diet/foods",
        params={"query": "", "limit": 10},
        headers=auth_headers(access_token),
    )
    assert empty_query_response.status_code == 200
    names = {item["name"] for item in empty_query_response.json()["data"]}
    assert names == {"닭가슴살", "현미밥"}


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
async def test_get_diet_logs_by_date_with_daily_total(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "diet-get-total@example.com")

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

    await client.post("/api/v1/diet/logs", json=breakfast_payload, headers=auth_headers(access_token))
    await client.post("/api/v1/diet/logs", json=lunch_payload, headers=auth_headers(access_token))

    response = await client.get(
        "/api/v1/diet/logs",
        params={"date": "2026-02-17"},
        headers=auth_headers(access_token),
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
async def test_get_diet_logs_with_target_remaining(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "diet-target@example.com")

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
        headers=auth_headers(access_token),
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
        headers=auth_headers(access_token),
    )

    response = await client.get(
        "/api/v1/diet/logs",
        params={"date": "2026-02-17"},
        headers=auth_headers(access_token),
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
async def test_get_diet_logs_without_profile_target_remaining_null(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "diet-no-profile@example.com")

    await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "breakfast",
            "items": [{"food_name": "Egg", "calories": 150.0}],
        },
        headers=auth_headers(access_token),
    )

    response = await client.get(
        "/api/v1/diet/logs",
        params={"date": "2026-02-17"},
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["target_remaining"] is None


@pytest.mark.asyncio
async def test_update_diet_log_success(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "diet-update@example.com")
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
        headers=auth_headers(access_token),
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
        headers=auth_headers(access_token),
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["status"] == "success"
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["food_name"] == "Food C"


@pytest.mark.asyncio
async def test_update_other_users_log_returns_403(client, register_and_get_token, auth_headers):
    owner_token, _ = await register_and_get_token(client, "diet-owner@example.com")
    other_token, _ = await register_and_get_token(client, "diet-other@example.com")

    create_response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "lunch",
            "items": [{"food_name": "Owner Food", "calories": 100.0}],
        },
        headers=auth_headers(owner_token),
    )
    assert create_response.status_code == 201
    log_id = create_response.json()["data"]["id"]

    update_response = await client.put(
        f"/api/v1/diet/logs/{log_id}",
        json={"meal_type": "dinner"},
        headers=auth_headers(other_token),
    )

    assert update_response.status_code == 403
    body = update_response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_delete_diet_log_success(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "diet-delete@example.com")
    create_response = await client.post(
        "/api/v1/diet/logs",
        json={
            "log_date": "2026-02-17",
            "meal_type": "snack",
            "items": [{"food_name": "Protein Bar", "calories": 210.0}],
        },
        headers=auth_headers(access_token),
    )
    assert create_response.status_code == 201
    log_id = create_response.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/diet/logs/{log_id}",
        headers=auth_headers(access_token),
    )

    assert delete_response.status_code == 200
    body = delete_response.json()
    assert body["status"] == "success"
