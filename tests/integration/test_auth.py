from __future__ import annotations

from httpx import AsyncClient

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
ME = "/api/v1/me"


async def _register(client: AsyncClient, email: str = "jordan@example.com") -> None:
    resp = await client.post(
        REGISTER,
        json={
            "email": email,
            "password": "supersecret",
            "display_name": "Jordan Reyes",
            "timezone": "Europe/Berlin",
            "identity_word": "Relentless",
        },
    )
    assert resp.status_code == 201, resp.text


async def test_register_login_me_flow(client: AsyncClient) -> None:
    await _register(client)

    creds = {"email": "jordan@example.com", "password": "supersecret"}
    login = await client.post(LOGIN, json=creds)
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"

    me = await client.get(ME, headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "jordan@example.com"
    assert body["level"] == 1
    assert body["level_name"] == "Beginner"


async def test_duplicate_email_conflict(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(
        REGISTER,
        json={"email": "jordan@example.com", "password": "supersecret", "display_name": "Dup"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_taken"


async def test_wrong_password_unauthorized(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(LOGIN, json={"email": "jordan@example.com", "password": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(ME)
    assert resp.status_code == 401


async def test_refresh_issues_new_tokens(client: AsyncClient) -> None:
    await _register(client)
    creds = {"email": "jordan@example.com", "password": "supersecret"}
    login = await client.post(LOGIN, json=creds)
    refresh_token = login.json()["refresh_token"]

    resp = await client.post(REFRESH, json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    # An access token may not be used to refresh.
    access_token = login.json()["access_token"]
    bad = await client.post(REFRESH, json={"refresh_token": access_token})
    assert bad.status_code == 401
