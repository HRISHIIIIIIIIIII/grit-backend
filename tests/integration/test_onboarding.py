from __future__ import annotations

from httpx import AsyncClient


async def _auth(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "j@example.com", "password": "supersecret", "display_name": "J"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "j@example.com", "password": "supersecret"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_new_user_starts_not_onboarded(client: AsyncClient) -> None:
    h = await _auth(client)
    me = await client.get("/api/v1/me", headers=h)
    assert me.json()["onboarding_completed"] is False


async def test_patch_me_updates_identity(client: AsyncClient) -> None:
    h = await _auth(client)
    resp = await client.patch(
        "/api/v1/me",
        headers=h,
        json={"identity_word": "Relentless", "display_name": "Jordan", "timezone": "America/New_York"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["identity_word"] == "Relentless"
    assert body["display_name"] == "Jordan"
    assert body["timezone"] == "America/New_York"


async def test_patch_me_rejects_bad_timezone(client: AsyncClient) -> None:
    h = await _auth(client)
    resp = await client.patch("/api/v1/me", headers=h, json={"timezone": "Mars/Phobos"})
    assert resp.status_code == 422


async def test_complete_onboarding(client: AsyncClient) -> None:
    h = await _auth(client)
    resp = await client.post(
        "/api/v1/onboarding",
        headers=h,
        json={
            "focus_areas": ["Fitness", "Learning"],
            "habits": [
                {"name": "Morning run", "category": "Fitness", "xp_value": 30},
                {"name": "Read", "category": "Learning", "xp_value": 20},
            ],
            "daily_target": 4,
            "reminder_slot": "morning",
            "intensity": "relentless",
            "identity_word": "Unstoppable",
            "pact_accepted": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["habits_created"] == 2
    assert body["user"]["onboarding_completed"] is True
    assert body["user"]["identity_word"] == "Unstoppable"
    assert body["user"]["focus_areas"] == ["Fitness", "Learning"]

    # Habits were created.
    habits = await client.get("/api/v1/habits", headers=h)
    assert len(habits.json()) == 2

    # Settings reflect tone + target.
    settings = await client.get("/api/v1/settings", headers=h)
    assert settings.json()["mentor_tone"] == "relentless"
    assert settings.json()["daily_target"] == 4
    assert settings.json()["reminder_slot"] == "morning"


async def test_enriched_analytics_shape(client: AsyncClient) -> None:
    h = await _auth(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": 30},
        )
    ).json()["id"]
    await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)

    resp = await client.get("/api/v1/analytics?period=week", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["trend"]) == 7  # daily points for the week
    assert len(body["time_of_day"]) == 5
    assert sum(b["count"] for b in body["time_of_day"]) == 1
    assert body["records"]["total_checkins"] == 1
