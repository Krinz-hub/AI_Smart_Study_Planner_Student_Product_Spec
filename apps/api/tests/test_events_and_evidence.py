import uuid
import pytest
from httpx import AsyncClient
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_event_ingestion_and_idempotency(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "event_user")
    topic_id = str(uuid.uuid4())
    idempotency_key = f"key_{uuid.uuid4().hex}"

    event_payload = {
        "event_type": "TASK_COMPLETED",
        "entity_type": "task",
        "entity_id": str(uuid.uuid4()),
        "evidence_category": "BEHAVIOR",
        "idempotency_key": idempotency_key,
        "payload": {"topic_id": topic_id, "duration_minutes": 45, "completed_status": "done"},
    }

    # 1. Post event
    res1 = await async_client.post(
        "/api/v1/learner/events",
        headers=user["headers"],
        json=event_payload,
    )
    assert res1.status_code == 201
    data1 = res1.json()
    event_id1 = data1["id"]
    assert data1["event_type"] == "TASK_COMPLETED"
    assert data1["evidence_category"] == "BEHAVIOR"

    # 2. Post identical event with same idempotency key
    res2 = await async_client.post(
        "/api/v1/learner/events",
        headers=user["headers"],
        json=event_payload,
    )
    assert res2.status_code == 201
    data2 = res2.json()
    # Must return same event record
    assert data2["id"] == event_id1


@pytest.mark.asyncio
async def test_evidence_categorization_and_anti_feedback_rule(async_client: AsyncClient):
    """Verifies knowledge evidence vs behavior evidence separation (skipped task != low knowledge)."""
    user = await create_authenticated_user(async_client, "evidence_user")
    topic_id = str(uuid.uuid4())

    # Record 1: Knowledge evidence (Quiz passed)
    await async_client.post(
        "/api/v1/learner/events",
        headers=user["headers"],
        json={
            "event_type": "QUIZ_COMPLETED",
            "entity_type": "quiz_attempt",
            "entity_id": str(uuid.uuid4()),
            "evidence_category": "KNOWLEDGE",
            "payload": {"topic_id": topic_id, "score": 0.9, "total_questions": 10},
        },
    )

    # Record 2: Behavior evidence (Task skipped due to busy schedule)
    await async_client.post(
        "/api/v1/learner/events",
        headers=user["headers"],
        json={
            "event_type": "TASK_SKIPPED",
            "entity_type": "task",
            "entity_id": str(uuid.uuid4()),
            "evidence_category": "BEHAVIOR",
            "payload": {"topic_id": topic_id, "reason": "no_time"},
        },
    )

    # Record 3: Self-report evidence (Student feedback: topic was useful)
    await async_client.post(
        "/api/v1/learner/feedback",
        headers=user["headers"],
        json={
            "topic_id": topic_id,
            "feedback_type": "useful",
            "notes": "Clear explanations in lecture",
        },
    )

    # Retrieve topic evidence
    ev_res = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}/evidence",
        headers=user["headers"],
    )
    assert ev_res.status_code == 200
    evidence = ev_res.json()

    assert evidence["total_evidence_count"] == 3
    assert len(evidence["knowledge_evidence"]) == 1
    assert evidence["knowledge_evidence"][0]["event_type"] == "QUIZ_COMPLETED"

    assert len(evidence["behavior_evidence"]) == 1
    assert evidence["behavior_evidence"][0]["event_type"] == "TASK_SKIPPED"

    assert len(evidence["self_report_evidence"]) == 1
    assert evidence["self_report_evidence"][0]["event_type"] == "RECOMMENDATION_FEEDBACK"


@pytest.mark.asyncio
async def test_feedback_types_validation(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "fb_val_user")

    # Invalid feedback type
    bad_res = await async_client.post(
        "/api/v1/learner/feedback",
        headers=user["headers"],
        json={"feedback_type": "completely_invalid_type"},
    )
    assert bad_res.status_code == 422

    # Valid feedback type: too_hard
    good_res = await async_client.post(
        "/api/v1/learner/feedback",
        headers=user["headers"],
        json={"feedback_type": "too_hard"},
    )
    assert good_res.status_code == 201
    assert good_res.json()["payload"]["feedback_type"] == "too_hard"
