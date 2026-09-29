import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_registration_and_login_flow(async_client: AsyncClient):
    random_suffix = uuid.uuid4().hex[:8]
    email = f"student_{random_suffix}@example.com"
    password = "StrongPassword123!"
    display_name = f"Test Student {random_suffix}"

    # 1. Registration
    reg_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
        },
    )
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert "access_token" in reg_data
    assert reg_data["token_type"] == "bearer"
    assert reg_data["user"]["email"] == email
    assert reg_data["user"]["display_name"] == display_name
    assert "password" not in reg_data["user"]
    assert "password_hash" not in reg_data["user"]

    token = reg_data["access_token"]

    # 2. Get Me (Protected Route)
    me_response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data["display_name"] == display_name

    # 3. Duplicate Email Rejection
    dup_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email.upper(),  # test case insensitivity
            "password": "AnotherPassword123!",
            "display_name": "Another Name",
        },
    )
    assert dup_response.status_code == 409
    dup_data = dup_response.json()
    assert dup_data["error"]["code"] == "CONFLICT"

    # 4. Login with Correct Credentials
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == email

    # 5. Login with Invalid Password
    bad_login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "WrongPassword!",
        },
    )
    assert bad_login_response.status_code == 401
    assert bad_login_response.json()["error"]["code"] == "UNAUTHORIZED"

    # 6. Logout
    logout_response = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_invalid_password_validation(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "shortpw@example.com",
            "password": "short",  # < 8 chars
            "display_name": "Short",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_unauthorized_route_without_token(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_unauthorized_route_with_invalid_token(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer completely-bogus-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_password_reset_flow(async_client: AsyncClient):
    random_suffix = uuid.uuid4().hex[:8]
    email = f"reset_user_{random_suffix}@example.com"
    old_pw = "OldPassword123!"
    new_pw = "NewSuperPassword123!"

    # Register user first
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": old_pw,
            "display_name": "Reset Tester",
        },
    )

    # Request reset
    req_response = await async_client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": email},
    )
    assert req_response.status_code == 200
    dev_token = req_response.json().get("dev_token")
    assert dev_token is not None

    # Confirm reset
    confirm_response = await async_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": dev_token,
            "new_password": new_pw,
        },
    )
    assert confirm_response.status_code == 200

    # Old password no longer works
    old_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_pw},
    )
    assert old_login.status_code == 401

    # New password works
    new_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_pw},
    )
    assert new_login.status_code == 200
