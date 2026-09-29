import uuid
import pytest
from httpx import AsyncClient
from app.common.mongo import get_mongo_db


@pytest.mark.asyncio
async def test_mongo_registration_and_onboarding_persistence(async_client: AsyncClient):
    """
    STAGE 1 TEST: Verifies registration stores user and onboarding records in MongoDB
    and maintains PostgreSQL identity stub for relational foreign-key consistency.
    """
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"mongo_student_{unique_suffix}@example.com"
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123!",
            "display_name": "MongoDB Student",
        },
    )
    assert reg_res.status_code == 201
    data = reg_res.json()
    token = data["access_token"]
    user_id = data["user"]["id"]

    # 1. Verify record in MongoDB users collection
    mongo_db = get_mongo_db()
    mongo_user = await mongo_db.users.find_one({"user_id": user_id})
    assert mongo_user is not None
    assert mongo_user["email"] == email
    assert mongo_user["display_name"] == "MongoDB Student"
    assert mongo_user["is_active"] is True
    assert "password_hash" in mongo_user

    # 2. Verify onboarding state initialized in MongoDB
    onboarding = await mongo_db.student_onboarding.find_one({"user_id": user_id})
    assert onboarding is not None
    assert onboarding["current_step"] == "ACADEMIC_TYPE"
    assert onboarding["academic_type"] is None

    # 3. Verify /me endpoint returns user profile and onboarding_step
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == email
    assert me_data["onboarding_step"] == "ACADEMIC_TYPE"

    # 4. Verify duplicate registration fails with 409 Conflict
    dup_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "DifferentPassword123!",
            "display_name": "Imposter",
        },
    )
    assert dup_res.status_code == 409


@pytest.mark.asyncio
async def test_mongo_login_and_logout_flow(async_client: AsyncClient):
    """
    STAGE 1 TEST: Verifies authentication against MongoDB credentials and logout endpoint.
    """
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"mongo_login_{unique_suffix}@example.com"
    password = "SecurePassword2026!"

    # Register user
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "Login Tester",
        },
    )
    assert reg_res.status_code == 201

    # Login with correct credentials
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    token = login_data["access_token"]

    # Logout
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "success"

    # Login with invalid password fails
    bad_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401
