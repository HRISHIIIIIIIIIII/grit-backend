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


async def test_first_step_unlocks_on_first_checkin(client: AsyncClient) -> None:
    h = await _auth(client)

    before = await client.get("/api/v1/achievements", headers=h)
    first = next(a for a in before.json() if a["code"] == "first_step")
    assert first["unlocked"] is False
    assert first["progress"] == 0

    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": 30},
        )
    ).json()["id"]
    await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)

    after = await client.get("/api/v1/achievements", headers=h)
    first = next(a for a in after.json() if a["code"] == "first_step")
    assert first["unlocked"] is True
    assert first["unlocked_at"] is not None


async def test_hidden_achievement_is_masked_until_unlocked(client: AsyncClient) -> None:
    h = await _auth(client)
    resp = await client.get("/api/v1/achievements", headers=h)
    hidden = next(a for a in resp.json() if a["code"] == "polymath")
    assert hidden["hidden"] is True
    assert hidden["name"] == "Hidden Achievement"
    assert "Polymath" not in hidden["description"]


async def test_achievement_unlock_awards_tier_xp(client: AsyncClient) -> None:
    h = await _auth(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": 30},
        )
    ).json()["id"]
    await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)
    # Trigger achievement sync.
    await client.get("/api/v1/achievements", headers=h)

    me = await client.get("/api/v1/me", headers=h)
    # 30 habit + 25 perfect-day + 50 first_step (Common tier bonus) = 105.
    assert me.json()["xp_total"] == 105
