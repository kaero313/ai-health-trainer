from decimal import Decimal, ROUND_HALF_UP

import pytest

ACTIVITY_MULTIPLIER = {
    "sedentary": Decimal("1.2"),
    "light": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "active": Decimal("1.725"),
    "very_active": Decimal("1.9"),
}


def _round_int(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _round_one(value: Decimal) -> float:
    rounded = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return float(rounded)


def _calculate_expected_targets(payload: dict[str, object]) -> dict[str, int | float]:
    weight_kg = Decimal(str(payload["weight_kg"]))
    height_cm = Decimal(str(payload["height_cm"]))
    age = Decimal(str(payload["age"]))
    gender = str(payload["gender"])
    goal = str(payload["goal"])
    activity_level = str(payload["activity_level"])

    if gender == "male":
        bmr = Decimal("10") * weight_kg + Decimal("6.25") * height_cm - Decimal("5") * age + Decimal("5")
    else:
        bmr = Decimal("10") * weight_kg + Decimal("6.25") * height_cm - Decimal("5") * age - Decimal("161")

    tdee_kcal = _round_int(bmr * ACTIVITY_MULTIPLIER[activity_level])

    if goal == "bulk":
        target_calories = tdee_kcal + 300
    elif goal == "diet":
        target_calories = tdee_kcal - 500
    else:
        target_calories = tdee_kcal

    protein_g = weight_kg * Decimal("1.8")
    fat_g = Decimal(target_calories) * Decimal("0.25") / Decimal("9")
    carbs_g = (Decimal(target_calories) - protein_g * Decimal("4") - fat_g * Decimal("9")) / Decimal("4")

    return {
        "tdee_kcal": tdee_kcal,
        "target_calories": target_calories,
        "target_protein_g": _round_one(protein_g),
        "target_carbs_g": _round_one(carbs_g),
        "target_fat_g": _round_one(fat_g),
    }




@pytest.mark.asyncio
async def test_get_profile_not_found_returns_not_found(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "profile-none@example.com")

    response = await client.get("/api/v1/profile", headers=auth_headers(access_token))

    assert response.status_code == 404
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_put_profile_creates_profile_and_calculates_targets(client, register_and_get_token, auth_headers):
    access_token, user_id = await register_and_get_token(client, "profile-create@example.com")
    request_payload = {
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "age": 28,
        "gender": "male",
        "goal": "bulk",
        "activity_level": "moderate",
        "allergies": ["milk", "peanut"],
        "food_preferences": ["chicken_breast", "sweet_potato"],
    }

    response = await client.put(
        "/api/v1/profile",
        json=request_payload,
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"

    data = payload["data"]
    expected = _calculate_expected_targets(request_payload)
    assert data["user_id"] == user_id
    assert data["height_cm"] == request_payload["height_cm"]
    assert data["weight_kg"] == request_payload["weight_kg"]
    assert data["age"] == request_payload["age"]
    assert data["gender"] == request_payload["gender"]
    assert data["goal"] == request_payload["goal"]
    assert data["activity_level"] == request_payload["activity_level"]
    assert data["allergies"] == request_payload["allergies"]
    assert data["food_preferences"] == request_payload["food_preferences"]
    assert data["tdee_kcal"] == expected["tdee_kcal"]
    assert data["target_calories"] == expected["target_calories"]
    assert data["target_protein_g"] == expected["target_protein_g"]
    assert data["target_carbs_g"] == expected["target_carbs_g"]
    assert data["target_fat_g"] == expected["target_fat_g"]


@pytest.mark.asyncio
async def test_get_profile_returns_saved_profile(client, register_and_get_token, auth_headers):
    access_token, user_id = await register_and_get_token(client, "profile-get@example.com")
    request_payload = {
        "height_cm": 165.5,
        "weight_kg": 62.5,
        "age": 34,
        "gender": "female",
        "goal": "maintain",
        "activity_level": "light",
        "allergies": [],
        "food_preferences": ["salmon", "tofu"],
    }

    put_response = await client.put(
        "/api/v1/profile",
        json=request_payload,
        headers=auth_headers(access_token),
    )
    assert put_response.status_code == 200

    get_response = await client.get("/api/v1/profile", headers=auth_headers(access_token))

    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["status"] == "success"
    data = payload["data"]
    expected = _calculate_expected_targets(request_payload)
    assert data["user_id"] == user_id
    assert data["goal"] == "maintain"
    assert data["food_preferences"] == ["salmon", "tofu"]
    assert data["tdee_kcal"] == expected["tdee_kcal"]
    assert data["target_calories"] == expected["target_calories"]


@pytest.mark.asyncio
async def test_put_profile_updates_existing_profile_and_recalculates_targets(client, register_and_get_token, auth_headers):
    access_token, _ = await register_and_get_token(client, "profile-update@example.com")
    first_payload = {
        "height_cm": 180.0,
        "weight_kg": 80.0,
        "age": 30,
        "gender": "male",
        "goal": "maintain",
        "activity_level": "moderate",
        "allergies": [],
        "food_preferences": ["chicken_breast"],
    }
    second_payload = {
        "height_cm": 180.0,
        "weight_kg": 82.0,
        "age": 30,
        "gender": "male",
        "goal": "diet",
        "activity_level": "active",
        "allergies": ["milk"],
        "food_preferences": ["brown_rice", "egg"],
    }

    first_response = await client.put(
        "/api/v1/profile",
        json=first_payload,
        headers=auth_headers(access_token),
    )
    assert first_response.status_code == 200

    second_response = await client.put(
        "/api/v1/profile",
        json=second_payload,
        headers=auth_headers(access_token),
    )
    assert second_response.status_code == 200

    data = second_response.json()["data"]
    expected = _calculate_expected_targets(second_payload)
    assert data["weight_kg"] == 82.0
    assert data["goal"] == "diet"
    assert data["activity_level"] == "active"
    assert data["allergies"] == ["milk"]
    assert data["food_preferences"] == ["brown_rice", "egg"]
    assert data["tdee_kcal"] == expected["tdee_kcal"]
    assert data["target_calories"] == expected["target_calories"]
    assert data["target_protein_g"] == expected["target_protein_g"]
    assert data["target_carbs_g"] == expected["target_carbs_g"]
    assert data["target_fat_g"] == expected["target_fat_g"]
