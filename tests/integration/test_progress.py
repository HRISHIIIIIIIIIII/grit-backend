from __future__ import annotations

from httpx import AsyncClient


async def _setup(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "jordan@example.com",
            "password": "supersecret",
            "display_name": "Jordan Reyes",
            "timezone": "Europe/Berlin",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "jordan@example.com", "password": "supersecret"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_streak_and_progress_after_checkin(client: AsyncClient) -> None:
    h = await _setup(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": 30},
        )
    ).json()["id"]
    await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)

    streak = await client.get("/api/v1/streaks", headers=h)
    assert streak.status_code == 200
    body = streak.json()
    assert body["current_daily"] == 1
    assert body["evolution_stage"] == "Spark"

    level = await client.get("/api/v1/level", headers=h)
    assert level.json()["level"] == 1

    xp = await client.get("/api/v1/xp", headers=h)
    # 30 habit + 25 perfect day.
    assert xp.json()["xp_total"] == 55
    assert len(xp.json()["recent_events"]) >= 1

    heatmap = await client.get("/api/v1/heatmap?range=weeks", headers=h)
    assert heatmap.status_code == 200
    assert sum(c["count"] for c in heatmap.json()["cells"]) == 1

    analytics = await client.get("/api/v1/analytics?period=week", headers=h)
    a = analytics.json()
    assert a["total_checkins"] == 1
    assert a["active_days"] == 1
    assert a["perfect_days"] == 1
    assert a["xp_earned"] == 55


async def test_freeze_endpoint(client: AsyncClient) -> None:
    h = await _setup(client)
    resp = await client.post("/api/v1/streaks/freeze", headers=h)
    assert resp.status_code == 200
    assert resp.json()["protected"] is False  # no 14-day run yet
