from __future__ import annotations

from httpx import AsyncClient

MD = """# 01 — Python DSA

## Phase 1: Fundamentals (Week 1)
- Lists and tuples
- Dictionaries

## Phase 2: Arrays (Week 2)
- Two pointers
"""


async def _auth(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "j@example.com", "password": "supersecret", "display_name": "J"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "j@example.com", "password": "supersecret"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_import_creates_phases_and_topics(client: AsyncClient) -> None:
    h = await _auth(client)
    resp = await client.post(
        "/api/v1/roadmaps/import", headers=h, json={"markdown": MD}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Python DSA"
    assert body["total_topics"] == 3
    assert len(body["phases"]) == 2
    assert body["phases"][0]["name"] == "Fundamentals"
    assert body["phases"][0]["duration_label"] == "Week 1"


async def test_toggle_topic_awards_xp_and_progress(client: AsyncClient) -> None:
    h = await _auth(client)
    detail = (
        await client.post("/api/v1/roadmaps/import", headers=h, json={"markdown": MD})
    ).json()
    roadmap_id = detail["id"]
    topic_id = detail["phases"][0]["topics"][0]["id"]

    toggle = await client.patch(
        f"/api/v1/roadmaps/{roadmap_id}/topics/{topic_id}",
        headers=h,
        json={"done": True},
    )
    assert toggle.status_code == 200
    body = toggle.json()
    assert body["topic"]["done"] is True
    assert body["xp_awarded"] == 25
    assert body["roadmap_progress_pct"] == 33  # 1/3
    assert body["dsa_habit_credited"] is False  # roadmap not DSA-linked

    me = await client.get("/api/v1/me", headers=h)
    assert me.json()["xp_total"] == 25

    # Untoggle refunds the topic XP.
    await client.patch(
        f"/api/v1/roadmaps/{roadmap_id}/topics/{topic_id}",
        headers=h,
        json={"done": False},
    )
    me2 = await client.get("/api/v1/me", headers=h)
    assert me2.json()["xp_total"] == 0


async def test_dsa_linked_topic_credits_habit(client: AsyncClient) -> None:
    h = await _auth(client)
    # Import a DSA-linked roadmap.
    detail = (
        await client.post(
            "/api/v1/roadmaps/import",
            headers=h,
            json={"markdown": MD, "is_dsa_linked": True},
        )
    ).json()
    roadmap_id = detail["id"]
    topic_id = detail["phases"][0]["topics"][0]["id"]

    # Create a habit linked to that roadmap (the DSA habit).
    habit = await client.post(
        "/api/v1/habits",
        headers=h,
        json={
            "name": "Solve a DSA topic",
            "category": "Learning",
            "xp_value": 25,
            "linked_roadmap_id": roadmap_id,
        },
    )
    habit_id = habit.json()["id"]

    toggle = await client.patch(
        f"/api/v1/roadmaps/{roadmap_id}/topics/{topic_id}",
        headers=h,
        json={"done": True},
    )
    assert toggle.json()["dsa_habit_credited"] is True

    # The DSA habit now shows a check-in for today.
    habits = await client.get("/api/v1/habits", headers=h)
    dsa = next(x for x in habits.json() if x["id"] == habit_id)
    assert dsa["checked_in_today"] is True
    assert dsa["current_streak"] == 1
