import uuid
import pytest
from httpx import AsyncClient
from tests.test_student_state import create_authenticated_user


async def create_subject_and_topic(async_client: AsyncClient, headers: dict, name: str = "Test Topic"):
    sub = await async_client.post(
        "/api/v1/subjects",
        headers=headers,
        json={"name": f"Subj_{uuid.uuid4().hex[:6]}"},
    )
    sub_id = sub.json()["id"]

    top = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=headers,
        json={"name": name},
    )
    return top.json()["id"]


@pytest.mark.asyncio
async def test_bkt_and_mastery_progression(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "bkt_user")
    topic_id = await create_subject_and_topic(async_client, user["headers"], "Graph Theory")

    # 1. Initial State -> UNKNOWN
    init_res = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["mastery"]["state"] == "UNKNOWN"
    assert init_data["mastery"]["evidence_count"] == 0

    # 2. First Correct Observation -> Mastery climbs
    obs1 = await async_client.post(
        f"/api/v1/learner/topics/{topic_id}/observation",
        headers=user["headers"],
        json={"is_correct": True, "response_time_seconds": 25},
    )
    assert obs1.status_code == 200
    data1 = obs1.json()
    assert data1["mastery_probability"] > 0.10
    assert data1["confidence"] > 0.0
    assert data1["state"] != "UNKNOWN"

    # 3. Multiple consecutive correct answers -> Progress to STRONG / MASTERED
    for _ in range(4):
        await async_client.post(
            f"/api/v1/learner/topics/{topic_id}/observation",
            headers=user["headers"],
            json={"is_correct": True},
        )

    final_res = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    final_data = final_res.json()
    assert final_data["mastery"]["probability"] >= 0.85
    assert final_data["mastery"]["evidence_count"] == 5
    assert final_data["mastery"]["state"] in ("STRONG", "MASTERED")


@pytest.mark.asyncio
async def test_fsrs_memory_dynamics(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "fsrs_user")
    topic_id = await create_subject_and_topic(async_client, user["headers"], "Memory Topic")

    # Correct observation -> stability increases
    obs_good = await async_client.post(
        f"/api/v1/learner/topics/{topic_id}/observation",
        headers=user["headers"],
        json={"is_correct": True},
    )
    assert obs_good.status_code == 200
    stability_good = obs_good.json()["stability_days"]
    assert stability_good > 1.0

    # Incorrect observation -> stability is impacted
    obs_fail = await async_client.post(
        f"/api/v1/learner/topics/{topic_id}/observation",
        headers=user["headers"],
        json={"is_correct": False},
    )
    assert obs_fail.status_code == 200
    stability_fail = obs_fail.json()["stability_days"]
    assert stability_fail < stability_good


@pytest.mark.asyncio
async def test_confidence_calibration(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "calib_user")
    topic_id = await create_subject_and_topic(async_client, user["headers"], "Calib Topic")

    # User rates high confidence (0.95), but has low mastery -> OVERCONFIDENT
    await async_client.post(
        f"/api/v1/learner/topics/{topic_id}/observation",
        headers=user["headers"],
        json={"is_correct": False},  # low mastery
    )
    await async_client.post(
        f"/api/v1/learner/topics/{topic_id}/confidence",
        headers=user["headers"],
        json={"self_confidence": 0.95},
    )

    state_res = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    calib = state_res.json()["confidence"]
    assert calib["calibration_status"] == "OVERCONFIDENT"


@pytest.mark.asyncio
async def test_prerequisite_blocker_detection(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "prereq_user")

    # Subject with 2 topics: A (prerequisite) and B (dependent)
    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Machine Learning"},
    )
    sub_id = sub.json()["id"]

    top_a = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Linear Algebra"},
    )
    topic_a_id = top_a.json()["id"]

    top_b = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Principal Component Analysis"},
    )
    topic_b_id = top_b.json()["id"]

    # Create prerequisite relationship: A is required for B
    await async_client.post(
        f"/api/v1/topics/{topic_a_id}/relationships",
        headers=user["headers"],
        json={"target_topic_id": topic_b_id, "relationship_type": "prerequisite"},
    )

    # Check topic B gaps -> Should have PREREQUISITE_GAP because topic A is unmastered
    gaps_res = await async_client.get(
        f"/api/v1/learner/topics/{topic_b_id}/gaps",
        headers=user["headers"],
    )
    assert gaps_res.status_code == 200
    gaps = gaps_res.json()
    assert any(g["gap_type"] == "PREREQUISITE_GAP" for g in gaps)

    # Check state blockers
    state_res = await async_client.get(
        f"/api/v1/learner/topics/{topic_b_id}",
        headers=user["headers"],
    )
    blockers = state_res.json()["prerequisite_blockers"]
    assert len(blockers) == 1
    assert blockers[0]["topic_name"] == "Linear Algebra"


@pytest.mark.asyncio
async def test_cold_start_diagnostic(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "diag_user")
    topic1 = await create_subject_and_topic(async_client, user["headers"], "Diag Topic 1")
    topic2 = await create_subject_and_topic(async_client, user["headers"], "Diag Topic 2")

    diag_res = await async_client.post(
        "/api/v1/learner/diagnostic",
        headers=user["headers"],
        json={
            "results": [
                {"topic_id": topic1, "is_correct": True},
                {"topic_id": topic2, "is_correct": False},
            ]
        },
    )
    assert diag_res.status_code == 200
    assert diag_res.json()["topics_updated"] == 2

    t1_state = await async_client.get(f"/api/v1/learner/topics/{topic1}", headers=user["headers"])
    assert t1_state.json()["mastery"]["evidence_count"] == 1
    assert t1_state.json()["mastery"]["probability"] > 0.10
