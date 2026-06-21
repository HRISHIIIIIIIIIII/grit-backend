from __future__ import annotations

from httpx import AsyncClient


async def _auth(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "j@example.com", "password": "supersecret", "display_name": "Jordan"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "j@example.com", "password": "supersecret"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_settings_get_and_patch(client: AsyncClient) -> None:
    h = await _auth(client)
    get = await client.get("/api/v1/settings", headers=h)
    assert get.status_code == 200
    assert get.json()["mentor_tone"] == "hard"
    assert get.json()["accent_color"] == "#0EA47F"

    patch = await client.patch(
        "/api/v1/settings",
        headers=h,
        json={"mentor_tone": "relentless", "theme": "dark", "notify_achievement": False},
    )
    assert patch.json()["mentor_tone"] == "relentless"
    assert patch.json()["theme"] == "dark"
    assert patch.json()["notify_achievement"] is False


async def test_achievement_unlock_creates_notification(client: AsyncClient) -> None:
    h = await _auth(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": 30},
        )
    ).json()["id"]
    await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)
    # Trigger achievement sync (unlocks "First Step").
    await client.get("/api/v1/achievements", headers=h)

    notes = await client.get("/api/v1/notifications", headers=h)
    assert notes.status_code == 200
    achievement_notes = [n for n in notes.json() if n["type"] == "achievement"]
    assert len(achievement_notes) >= 1


async def test_disabled_type_suppresses_notification(client: AsyncClient) -> None:
    h = await _auth(client)
    await client.patch("/api/v1/settings", headers=h, json={"notify_achievement": False})

    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": 30},
        )
    ).json()["id"]
    await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)
    await client.get("/api/v1/achievements", headers=h)

    notes = await client.get("/api/v1/notifications", headers=h)
    achievement_notes = [n for n in notes.json() if n["type"] == "achievement"]
    assert achievement_notes == []


async def test_mark_read_and_read_all(client: AsyncClient) -> None:
    h = await _auth(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": 30},
        )
    ).json()["id"]
    await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)
    await client.get("/api/v1/achievements", headers=h)

    notes = (await client.get("/api/v1/notifications", headers=h)).json()
    assert notes
    nid = notes[0]["id"]

    read = await client.post(f"/api/v1/notifications/{nid}/read", headers=h)
    assert read.json()["read_at"] is not None

    all_read = await client.post("/api/v1/notifications/read-all", headers=h)
    assert all_read.json()["marked_read"] >= 0
