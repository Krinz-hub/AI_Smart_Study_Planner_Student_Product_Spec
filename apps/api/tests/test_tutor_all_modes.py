import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_tutor_all_modes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"tutor_test_{unique_suffix}@study.edu"
        password = "SecurePassword123!"

        # Register & login
        reg_res = await ac.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "display_name": "Tutor Student"},
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a Subject and Topic
        sub_res = await ac.post(
            "/api/v1/subjects",
            headers=headers,
            json={"name": "Computer Science", "code": "CS101", "color": "#6366f1"},
        )
        assert sub_res.status_code == 201
        sub_id = sub_res.json()["id"]

        top_res = await ac.post(
            f"/api/v1/subjects/{sub_id}/topics",
            headers=headers,
            json={"name": "Binary Search Trees"},
        )
        assert top_res.status_code == 201
        topic_id = top_res.json()["id"]

        # Test all modes including aliases (eli5, deep_dive, exam_rubric, socratic, hint)
        modes_to_test = [
            "socratic",
            "eli5",
            "deep_dive",
            "exam_rubric",
            "hint",
            "explain_simply",
            "explain_in_detail",
            "give_example",
            "exam_answer",
            "correct_my_answer",
        ]

        for mode in modes_to_test:
            chat_res = await ac.post(
                "/api/v1/tutor/chat",
                headers=headers,
                json={
                    "topic_id": topic_id,
                    "mode": mode,
                    "message": "How does search time complexity work?",
                },
            )
            assert chat_res.status_code == 200, f"Mode {mode} failed: {chat_res.text}"
            data = chat_res.json()
            assert len(data["response_text"]) > 0
            assert "suggested_followups" in data
            assert len(data["suggested_followups"]) > 0
