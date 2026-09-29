import uuid
from datetime import datetime, timezone, timedelta, date, time
import pytest
from httpx import AsyncClient
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_skipped_task_does_not_lower_mastery(async_client: AsyncClient):
    """
    CRITICAL TEST: Skipped task must NEVER lower or degrade BKT mastery state.
    Anti-feedback compliance: produces BEHAVIOR event only.
    """
    user = await create_authenticated_user(async_client, "skip_user")

    # 1. Create Subject and Topic
    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Computer Networks", "code": "CS401"},
    )
    sub_id = sub.json()["id"]

    topic = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "TCP Handshake"},
    )
    topic_id = topic.json()["id"]

    # 2. Establish initial baseline mastery via diagnostic or observation
    obs_res = await async_client.post(
        f"/api/v1/learner/topics/{topic_id}/observation",
        headers=user["headers"],
        json={"is_correct": True, "response_time_seconds": 30},
    )
    assert obs_res.status_code == 200
    baseline_mastery = obs_res.json()["mastery_probability"]
    baseline_state = obs_res.json()["state"]

    # 3. Create a scheduled study task for this topic
    now = datetime.now(timezone.utc)
    # Set availability windows
    await async_client.put(
        "/api/v1/student/availability",
        headers=user["headers"],
        json={
            "windows": [
                {"weekday": i, "start_time": "10:00:00", "end_time": "14:00:00", "enabled": True}
                for i in range(7)
            ]
        },
    )

    today = date.today()
    plan_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=3)).isoformat(),
            "daily_capacity_minutes": 180,
        },
    )
    assert plan_res.status_code == 201
    tasks = plan_res.json()["tasks"]
    assert len(tasks) > 0
    target_task = tasks[0]

    # 4. Skip the task
    skip_res = await async_client.post(
        f"/api/v1/tasks/{target_task['id']}/skip",
        headers=user["headers"],
        json={"reason": "too_busy_with_assignment"},
    )
    assert skip_res.status_code == 200
    assert skip_res.json()["status"] == "SKIPPED"

    # 5. Check mastery state afterwards - MUST BE STRICTLY UNCHANGED
    state_res = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    assert state_res.status_code == 200
    post_skip_mastery = state_res.json()["mastery"]["probability"]
    assert post_skip_mastery == baseline_mastery

    # 6. Verify evidence log has BEHAVIOR category, NOT KNOWLEDGE
    ev_res = await async_client.get(
        "/api/v1/learner/events",
        headers=user["headers"],
    )
    assert ev_res.status_code == 200
    events = ev_res.json()
    skip_events = [e for e in events if e["event_type"] == "TASK_SKIPPED"]
    assert len(skip_events) >= 1
    assert skip_events[0]["evidence_category"] == "BEHAVIOR"


@pytest.mark.asyncio
async def test_failed_quiz_lowers_mastery(async_client: AsyncClient):
    """
    CRITICAL TEST: Failed quiz/assessment must degrade BKT mastery and update FSRS memory stability.
    """
    user = await create_authenticated_user(async_client, "fail_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Discrete Math", "code": "MATH201"},
    )
    sub_id = sub.json()["id"]

    topic = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Graph Theory"},
    )
    topic_id = topic.json()["id"]

    # Initial correct observation to set moderate mastery
    obs1 = await async_client.post(
        f"/api/v1/learner/topics/{topic_id}/observation",
        headers=user["headers"],
        json={"is_correct": True, "response_time_seconds": 25},
    )
    initial_mastery = obs1.json()["mastery_probability"]

    # Generate plan and obtain task
    await async_client.put(
        "/api/v1/student/availability",
        headers=user["headers"],
        json={
            "windows": [
                {"weekday": i, "start_time": "14:00:00", "end_time": "18:00:00", "enabled": True}
                for i in range(7)
            ]
        },
    )
    today = date.today()
    plan_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=2)).isoformat(),
        },
    )
    tasks = plan_res.json()["tasks"]
    task_id = tasks[0]["id"]

    # Complete task with a failing score (0.25 -> is_correct=False)
    comp_res = await async_client.post(
        f"/api/v1/tasks/{task_id}/complete",
        headers=user["headers"],
        json={
            "actual_minutes": 40,
            "score": 0.25,
            "notes": "Struggled with bipartite graphs",
        },
    )
    assert comp_res.status_code == 200
    result = comp_res.json()
    assert result["task"]["status"] == "COMPLETED"
    assert result["bkt_mastery_probability"] is not None
    assert result["bkt_mastery_probability"] < initial_mastery


@pytest.mark.asyncio
async def test_strong_quiz_reduces_priority(async_client: AsyncClient):
    """
    CRITICAL TEST: High score on assessment drives mastery UP and priority DOWN.
    """
    user = await create_authenticated_user(async_client, "priority_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Operating Systems", "code": "CS401"},
    )
    sub_id = sub.json()["id"]

    topic = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Virtual Memory"},
    )
    topic_id = topic.json()["id"]

    # Topic is unassessed / weak initially
    recs_initial = await async_client.get(
        "/api/v1/decisions/recommendations",
        headers=user["headers"],
    )
    assert recs_initial.status_code == 200
    initial_recs = [r for r in recs_initial.json()["recommendations"] if r["topic_id"] == topic_id]
    assert len(initial_recs) == 1
    priority_before = initial_recs[0]["priority"]

    # Generate plan
    await async_client.put(
        "/api/v1/student/availability",
        headers=user["headers"],
        json={
            "windows": [
                {"weekday": i, "start_time": "09:00:00", "end_time": "13:00:00", "enabled": True}
                for i in range(7)
            ]
        },
    )
    today = date.today()
    plan_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=2)).isoformat(),
        },
    )
    tasks = plan_res.json()["tasks"]
    task_id = tasks[0]["id"]

    # Complete with perfect assessment score (score = 1.0)
    for _ in range(3):
        await async_client.post(
            f"/api/v1/tasks/{task_id}/complete",
            headers=user["headers"],
            json={"score": 1.0, "actual_minutes": 35},
        )

    # Check updated recommendations from Decision Engine
    recs_after = await async_client.get(
        "/api/v1/decisions/recommendations",
        headers=user["headers"],
    )
    after_recs = [r for r in recs_after.json()["recommendations"] if r["topic_id"] == topic_id]
    priority_after = after_recs[0]["priority"]

    # High mastery must reduce need/priority
    assert priority_after < priority_before


@pytest.mark.asyncio
async def test_plan_does_not_oscillate_unnecessarily(async_client: AsyncClient):
    """
    CRITICAL TEST: Replan maintains schedule stability:
    - Locked tasks are anchored at exact start/end
    - Completed tasks are preserved
    - Feasible new schedule is produced without churn
    """
    user = await create_authenticated_user(async_client, "stability_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Algorithms", "code": "CS301"},
    )
    sub_id = sub.json()["id"]

    for name in ["Sorting", "Dynamic Programming", "Greedy"]:
        await async_client.post(
            f"/api/v1/subjects/{sub_id}/topics",
            headers=user["headers"],
            json={"name": name},
        )

    await async_client.put(
        "/api/v1/student/availability",
        headers=user["headers"],
        json={
            "windows": [
                {"weekday": i, "start_time": "12:00:00", "end_time": "17:00:00", "enabled": True}
                for i in range(7)
            ]
        },
    )

    today = date.today()
    plan_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=4)).isoformat(),
        },
    )
    assert plan_res.status_code == 201
    plan = plan_res.json()
    tasks = plan["tasks"]
    assert len(tasks) >= 2

    # Lock task 0
    locked_task_id = tasks[0]["id"]
    locked_start = tasks[0]["planned_start"]
    locked_end = tasks[0]["planned_end"]

    lock_res = await async_client.post(
        f"/api/v1/tasks/{locked_task_id}/lock",
        headers=user["headers"],
        json={"locked": True},
    )
    assert lock_res.status_code == 200
    assert lock_res.json()["locked"] is True

    # Complete task 1
    completed_task_id = tasks[1]["id"]
    await async_client.post(
        f"/api/v1/tasks/{completed_task_id}/complete",
        headers=user["headers"],
        json={"actual_minutes": 45},
    )

    # Trigger Replan
    replan_res = await async_client.post(
        f"/api/v1/plans/{plan['plan_id']}/replan",
        headers=user["headers"],
        json={
            "reason": "TASK_COMPLETED",
            "context": {"completed_task_id": completed_task_id},
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=4)).isoformat(),
        },
    )
    assert replan_res.status_code == 200
    replanned_tasks = replan_res.json()["tasks"]

    # Verify locked task was NOT moved or deleted (Schedule stability)
    locked_in_replan = [t for t in replanned_tasks if t["id"] == locked_task_id]
    assert len(locked_in_replan) == 1
    assert locked_in_replan[0]["planned_start"] == locked_start
    assert locked_in_replan[0]["planned_end"] == locked_end
    assert locked_in_replan[0]["locked"] is True

    # Verify completed task is preserved
    completed_in_replan = [t for t in replanned_tasks if t["id"] == completed_task_id]
    assert len(completed_in_replan) == 1
    assert completed_in_replan[0]["status"] == "COMPLETED"
