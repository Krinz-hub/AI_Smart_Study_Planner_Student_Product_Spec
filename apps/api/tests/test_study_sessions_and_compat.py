import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.asyncio


import uuid

async def test_settings_and_compat_routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unique_email = f"test_settings_{uuid.uuid4().hex[:8]}@example.com"
        # Register a test student
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "Password123!",
                "display_name": "Settings Student",
            },
        )

        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test /api/v1/settings GET
        settings_get = await client.get("/api/v1/settings", headers=headers)
        assert settings_get.status_code == 200
        data = settings_get.json()
        assert data["theme"] == "system"
        assert data["daily_capacity_minutes"] == 180

        # 2. Test /api/v1/settings PATCH
        settings_patch = await client.patch(
            "/api/v1/settings",
            headers=headers,
            json={"theme": "dark", "daily_capacity_minutes": 240, "ai_tutor_mode": "exam_answer"},
        )
        assert settings_patch.status_code == 200
        updated = settings_patch.json()
        assert updated["theme"] == "dark"
        assert updated["daily_capacity_minutes"] == 240
        assert updated["ai_tutor_mode"] == "exam_answer"

        # 3. Test /api/v1/profile alias
        profile_res = await client.get("/api/v1/profile", headers=headers)
        assert profile_res.status_code == 200
        assert "user_id" in profile_res.json()

        # 4. Test /api/v1/home alias
        home_res = await client.get("/api/v1/home", headers=headers)
        assert home_res.status_code == 200
        assert "academic_summary" in home_res.json()

        # 5. Test /api/v1/goals alias
        goal_res = await client.post(
            "/api/v1/goals",
            headers=headers,
            json={"title": "Master Linear Algebra", "target_type": "mastery", "target_value": 0.9},
        )
        assert goal_res.status_code == 201
        goal_id = goal_res.json()["id"]

        list_goals = await client.get("/api/v1/goals", headers=headers)
        assert list_goals.status_code == 200
        assert len(list_goals.json()) >= 1

        del_goal = await client.delete(f"/api/v1/goals/{goal_id}", headers=headers)
        assert del_goal.status_code == 200

        # 6. Test /api/v1/study-sessions
        sessions_res = await client.get("/api/v1/study-sessions", headers=headers)
        assert sessions_res.status_code == 200
        assert isinstance(sessions_res.json(), list)

