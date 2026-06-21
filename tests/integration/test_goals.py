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


async def test_goal_with_milestones_progress_and_autocomplete(client: AsyncClient) -> None:
    h = await _auth(client)
    create = await client.post(
        "/api/v1/goals",
        headers=h,
        json={
            "name": "Read 24 books",
            "milestones": [{"name": "Book 1"}, {"name": "Book 2"}],
        },
    )
    assert create.status_code == 201
    goal = create.json()
    assert goal["total_milestones"] == 2
    assert goal["progress_pct"] == 0
    assert goal["status"] == "active"
    goal_id = goal["id"]
    m1, m2 = [m["id"] for m in goal["milestones"]]

    # Complete first milestone -> 50 XP, 50% progress.
    r1 = await client.patch(
        f"/api/v1/goals/{goal_id}/milestones/{m1}", headers=h, json={"done": True}
    )
    assert r1.json()["progress_pct"] == 50
    me = await client.get("/api/v1/me", headers=h)
    assert me.json()["xp_total"] == 50

    # Complete second -> goal auto-completes.
    r2 = await client.patch(
        f"/api/v1/goals/{goal_id}/milestones/{m2}", headers=h, json={"done": True}
    )
    assert r2.json()["progress_pct"] == 100
    assert r2.json()["status"] == "completed"

    # Reopen a milestone -> back to active, XP refunded.
    r3 = await client.patch(
        f"/api/v1/goals/{goal_id}/milestones/{m1}", headers=h, json={"done": False}
    )
    assert r3.json()["status"] == "active"
    me2 = await client.get("/api/v1/me", headers=h)
    assert me2.json()["xp_total"] == 50


async def test_goal_habit_links(client: AsyncClient) -> None:
    h = await _auth(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": 30},
        )
    ).json()["id"]

    goal = (
        await client.post(
            "/api/v1/goals",
            headers=h,
            json={"name": "Half marathon", "habit_ids": [habit_id]},
        )
    ).json()
    assert goal["habit_ids"] == [habit_id]

    # Update to clear the links.
    updated = await client.patch(f"/api/v1/goals/{goal['id']}", headers=h, json={"habit_ids": []})
    assert updated.json()["habit_ids"] == []


async def test_delete_goal(client: AsyncClient) -> None:
    h = await _auth(client)
    goal_id = (await client.post("/api/v1/goals", headers=h, json={"name": "Ship project"})).json()[
        "id"
    ]
    resp = await client.delete(f"/api/v1/goals/{goal_id}", headers=h)
    assert resp.status_code == 204
    assert (await client.get("/api/v1/goals", headers=h)).json() == []
