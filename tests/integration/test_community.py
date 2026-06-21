from __future__ import annotations

from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, name: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret", "display_name": name},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _earn_xp(client: AsyncClient, h: dict[str, str], xp: int) -> None:
    habit_id = (
        await client.post(
            "/api/v1/habits",
            headers=h,
            json={"name": "Run", "category": "Fitness", "xp_value": xp},
        )
    ).json()["id"]
    await client.post(f"/api/v1/habits/{habit_id}/checkin", headers=h)


async def test_global_leaderboard_ranks_by_xp(client: AsyncClient) -> None:
    a = await _register(client, "a@example.com", "Ann")
    b = await _register(client, "b@example.com", "Bob")
    await _earn_xp(client, a, 40)  # Ann earns more
    await _earn_xp(client, b, 15)

    board = await client.get("/api/v1/leaderboard?scope=global", headers=a)
    entries = board.json()["entries"]
    assert entries[0]["display_name"] == "Ann"
    assert entries[0]["rank"] == 1
    assert board.json()["my_rank"] == 1


async def test_friend_request_accept_and_friends_board(client: AsyncClient) -> None:
    a = await _register(client, "a@example.com", "Ann")
    b = await _register(client, "b@example.com", "Bob")

    # Ann sends a request to Bob.
    req = await client.post("/api/v1/friends", headers=a, json={"email": "b@example.com"})
    assert req.status_code == 201

    # Duplicate request rejected.
    dup = await client.post("/api/v1/friends", headers=a, json={"email": "b@example.com"})
    assert dup.status_code == 409

    # Bob sees an incoming request.
    bob_friends = await client.get("/api/v1/friends", headers=b)
    assert len(bob_friends.json()["incoming_requests"]) == 1
    friendship_id = bob_friends.json()["incoming_requests"][0]["friendship_id"]

    # Bob accepts.
    accept = await client.post(
        f"/api/v1/friends/{friendship_id}/respond", headers=b, json={"accept": True}
    )
    assert len(accept.json()["friends"]) == 1

    # Friends board now includes both.
    board = await client.get("/api/v1/leaderboard?scope=friends", headers=a)
    names = {e["display_name"] for e in board.json()["entries"]}
    assert names == {"Ann", "Bob"}


async def test_cannot_friend_self(client: AsyncClient) -> None:
    a = await _register(client, "a@example.com", "Ann")
    resp = await client.post("/api/v1/friends", headers=a, json={"email": "a@example.com"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "self_friend"


async def test_challenges_endpoint(client: AsyncClient) -> None:
    a = await _register(client, "a@example.com", "Ann")
    resp = await client.get("/api/v1/challenges", headers=a)
    assert resp.status_code == 200
    codes = {c["code"] for c in resp.json()}
    assert "consistency_20" in codes


async def test_league_board_weekly(client: AsyncClient) -> None:
    a = await _register(client, "a@example.com", "Ann")
    await _earn_xp(client, a, 30)
    board = await client.get("/api/v1/leaderboard?scope=league", headers=a)
    assert board.status_code == 200
    me = next(e for e in board.json()["entries"] if e["is_me"])
    assert me["xp"] >= 30  # weekly xp earned
