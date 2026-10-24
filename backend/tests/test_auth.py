import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(async_client: AsyncClient):
    # Register new user
    reg_res = await async_client.post("/api/auth/register", json={
        "email": "newbie@example.com",
        "password": "SecurePassword123!",
        "full_name": "New Developer"
    })
    assert reg_res.status_code == 201, reg_res.text
    data = reg_res.json()
    assert data["email"] == "newbie@example.com"
    assert data["role"] == "USER"

    # Login with credentials
    login_res = await async_client.post("/api/auth/login", json={
        "email": "newbie@example.com",
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 200, login_res.text
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["email"] == "newbie@example.com"

    # Verify Profile
    me_res = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "newbie@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient, normal_user):
    res = await async_client.post("/api/auth/login", json={
        "email": normal_user.email,
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
