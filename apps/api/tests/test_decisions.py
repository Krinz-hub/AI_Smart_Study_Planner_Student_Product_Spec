import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_weak_and_urgent_topic(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "decision_urgent")

    # Subject with exam in 2 days
    sub_res = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Database Systems", "code": "CS401"},
    )
    sub_id = sub_res.json()["id"]

    exam_date = datetime.now(timezone.utc) + timedelta(days=2)
    await async_client.post(
        "/api/v1/exams",
        headers=user["headers"],
        json={"subject_id": sub_id, "name": "Finals", "exam_at": exam_date.isoformat()},
    )

    top_res = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "B+ Trees and Indexing"},
    )
    topic_id = top_res.json()["id"]

    # Student scored poorly on assessment -> low mastery
    await async_client.post(
        f"/api/v1/learner/topics/{topic_id}/observation",
        headers=user["headers"],
        json={"is_correct": False},
    )

    # Query recommendations
    rec_res = await async_client.get(
        "/api/v1/decisions/recommendations",
        headers=user["headers"],
    )
    assert rec_res.status_code == 200
    data = rec_res.json()
    top_rec = data["top_recommendation"]

    assert top_rec is not None
    assert top_rec["topic_id"] == topic_id
    assert top_rec["priority"] >= 0.50
    assert any("exam" in r.lower() for r in top_rec["reason"])
    assert any("mastery" in r.lower() or "unassessed" in r.lower() for r in top_rec["reason"])


@pytest.mark.asyncio
async def test_strong_and_distant_exam(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "decision_distant")

    # Subject with exam in 60 days
    sub_res = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "History of Computing"},
    )
    sub_id = sub_res.json()["id"]

    exam_date = datetime.now(timezone.utc) + timedelta(days=60)
    await async_client.post(
        "/api/v1/exams",
        headers=user["headers"],
        json={"subject_id": sub_id, "name": "Term Exam", "exam_at": exam_date.isoformat()},
    )

    top_res = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Turing Machines"},
    )
    topic_id = top_res.json()["id"]

    # High mastery through repeated correct answers
    for _ in range(5):
        await async_client.post(
            f"/api/v1/learner/topics/{topic_id}/observation",
            headers=user["headers"],
            json={"is_correct": True},
        )

    rec_res = await async_client.get(
        "/api/v1/decisions/recommendations",
        headers=user["headers"],
    )
    assert rec_res.status_code == 200
    top_rec = rec_res.json()["top_recommendation"]
    assert top_rec["priority"] < 0.40


@pytest.mark.asyncio
async def test_prerequisite_weakness_triggers_repair(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "decision_prereq")

    sub_res = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Calculus II"},
    )
    sub_id = sub_res.json()["id"]

    top_a = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Limits"},
    )
    topic_a_id = top_a.json()["id"]

    top_b = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Continuity"},
    )
    topic_b_id = top_b.json()["id"]

    # Limits is prerequisite of Continuity
    await async_client.post(
        f"/api/v1/topics/{topic_a_id}/relationships",
        headers=user["headers"],
        json={"target_topic_id": topic_b_id, "relationship_type": "prerequisite"},
    )

    # Check topic B recommendation specifically
    rec_res = await async_client.get(
        f"/api/v1/decisions/recommendations?subject_id={sub_id}",
        headers=user["headers"],
    )
    assert rec_res.status_code == 200
    recs = rec_res.json()["recommendations"]
    rec_b = next((r for r in recs if r["topic_id"] == topic_b_id), None)
    assert rec_b is not None
    assert rec_b["action"] == "PREREQUISITE_REPAIR"
    assert any("prerequisite" in r.lower() for r in rec_b["reason"])


@pytest.mark.asyncio
async def test_unknown_topic_recommendation(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "decision_unknown")

    sub_res = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Networks"},
    )
    sub_id = sub_res.json()["id"]

    await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "TCP Handshake"},
    )

    rec_res = await async_client.get(
        "/api/v1/decisions/next",
        headers=user["headers"],
    )
    assert rec_res.status_code == 200
    top_rec = rec_res.json()
    assert top_rec["action"] == "LEARN"
    assert any("unassessed" in r.lower() or "unknown" in r.lower() for r in top_rec["reason"])


@pytest.mark.asyncio
async def test_no_action_scenario(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "decision_noaction")

    # User with no enrolled subjects
    rec_res = await async_client.get(
        "/api/v1/decisions/recommendations",
        headers=user["headers"],
    )
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["top_recommendation"]["action"] == "NO_ACTION"
