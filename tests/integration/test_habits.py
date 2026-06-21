from __future__ import annotations

from httpx import AsyncClient


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
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


async def test_habit_crud_and_listing(client: AsyncClient) -> None:
    h = await _auth_headers(client)
    create = await client.post(
        "/api/v1/habits",
        headers=h,
        json={"name": "Morning run", "category": "Fitness", "xp_value": 30},
    )
    assert create.status_code == 201
    habit_id = create.json()["id"]

    listing = await client.get("/api/v1/habits", headers=h)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["checked_in_today"] is False

    patch = await client.patch(f"/api/v1/habits/{habit_id}", headers=h, json={"xp_value": 40})
    assert patch.json()["xp_value"] == 40


async def test_checkin_is_idempotent_per_day(client: AsyncClient) -> None:
    h = await _auth_headers(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Cold shower", "category": "Discipline", "xp_value": 15},
        )
    ).json()["id"]

    first = await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)
    assert first.status_code == 200
    body = first.json()
    assert body["xp_awarded"] == 15
    assert body["current_streak"] == 1
    assert body["perfect_day"] is True  # only one scheduled habit, now checked in

    second = await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "already_checked_in"

    # /me reflects awarded XP (15 habit + 25 perfect day = 40).
    me = await client.get("/api/v1/me", headers=h)
    assert me.json()["xp_total"] == 40


async def test_undo_checkin_refunds_xp(client: AsyncClient) -> None:
    h = await _auth_headers(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Read", "category": "Learning", "xp_value": 20},
        )
    ).json()["id"]

    await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)
    undo = await client.delete(f"/api/v1/habits/{habit_id}/checkin", headers=h)
    assert undo.status_code == 204

    me = await client.get("/api/v1/me", headers=h)
    assert me.json()["xp_total"] == 0  # habit + perfect-day fully refunded


async def test_archive_hides_from_default_list(client: AsyncClient) -> None:
    h = await _auth_headers(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Meditate", "category": "Mind", "xp_value": 15},
        )
    ).json()["id"]

    await client.post(f"/api/v1/habits/{habit_id}/archive", headers=h)
    default = await client.get("/api/v1/habits", headers=h)
    assert default.json() == []

    with_archived = await client.get("/api/v1/habits?include_archived=true", headers=h)
    assert len(with_archived.json()) == 1

    await client.post(f"/api/v1/habits/{habit_id}/restore", headers=h)
    restored = await client.get("/api/v1/habits", headers=h)
    assert len(restored.json()) == 1


async def test_cannot_touch_another_users_habit(client: AsyncClient) -> None:
    h = await _auth_headers(client)
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": 30},
        )
    ).json()["id"]

    # Second user.
    await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "supersecret", "display_name": "Other"},
    )
    other_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "supersecret"},
    )
    other_h = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    resp = await client.patch(f"/api/v1/habits/{habit_id}", headers=other_h, json={"xp_value": 1})
    assert resp.status_code == 404
