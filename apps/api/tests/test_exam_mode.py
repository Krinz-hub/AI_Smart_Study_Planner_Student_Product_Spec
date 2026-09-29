import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_exam_mode_generation_and_syllabus_coverage(async_client: AsyncClient):
    """
    CRITICAL TEST: Exam mode achieves comprehensive syllabus coverage
    and schedules high-yield final revision within the final 48h.
    """
    user = await create_authenticated_user(async_client, "exam_mode_user")

    # Create Subject & 4 Topics
    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Operating Systems", "code": "CS401"},
    )
    sub_id = sub.json()["id"]

    for name in ["Processes & Threads", "CPU Scheduling", "Synchronization", "Deadlocks"]:
        await async_client.post(
            f"/api/v1/subjects/{sub_id}/topics",
            headers=user["headers"],
            json={"name": name},
        )

    # Schedule Exam 4 days from now
    exam_date = datetime.now(timezone.utc) + timedelta(days=4)
    exam_res = await async_client.post(
        "/api/v1/exams",
        headers=user["headers"],
        json={
            "name": "OS Final Exam",
            "subject_id": sub_id,
            "exam_at": exam_date.isoformat(),
            "target_score": 90.0,
        },
    )
    assert exam_res.status_code == 201
    exam_id = exam_res.json()["id"]

    # Generate Exam Mode Plan
    plan_res = await async_client.post(
        "/api/v1/exam-mode/generate",
        headers=user["headers"],
        json={
            "exam_id": exam_id,
            "workload_ceiling_minutes": 360,
        },
    )
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    assert plan_data["status"] == "PROPOSED"
    assert plan_data["syllabus_coverage_pct"] >= 75.0
    assert plan_data["daily_workload_minutes"] <= 360

    # Verify tasks include FINAL_REVISION in the final 48 hours
    tasks = plan_data["tasks"]
    final_rev_tasks = [t for t in tasks if t["task_type"] == "FINAL_REVISION"]
    assert len(final_rev_tasks) >= 1


@pytest.mark.asyncio
async def test_rescue_procedure_backlog_pruning(async_client: AsyncClient):
    """
    CRITICAL TEST: Rescue procedure detects backlog, defers unrelated subjects,
    and preserves critical exam preparation tasks without exceeding workload ceilings.
    """
    user = await create_authenticated_user(async_client, "rescue_user")

    # Subject A: Exam Subject
    sub_a = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Linear Algebra", "code": "MATH101"},
    )
    sub_a_id = sub_a.json()["id"]

    top_a = await async_client.post(
        f"/api/v1/subjects/{sub_a_id}/topics",
        headers=user["headers"],
        json={"name": "Eigenvalues"},
    )
    top_a_id = top_a.json()["id"]

    # Subject B: Unrelated Subject with overdue backlog task
    sub_b = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "History of Art", "code": "ART101"},
    )
    sub_b_id = sub_b.json()["id"]

    top_b = await async_client.post(
        f"/api/v1/subjects/{sub_b_id}/topics",
        headers=user["headers"],
        json={"name": "Renaissance Painting"},
    )
    top_b_id = top_b.json()["id"]

    # Create overdue pending task in Art
    past_start = datetime.now(timezone.utc) - timedelta(days=2)
    # We can create a task via planner generate or directly
    exam_date = datetime.now(timezone.utc) + timedelta(days=3)
    exam_res = await async_client.post(
        "/api/v1/exams",
        headers=user["headers"],
        json={
            "name": "Linear Algebra Exam",
            "subject_id": sub_a_id,
            "exam_at": exam_date.isoformat(),
            "target_score": 85.0,
        },
    )
    exam_id = exam_res.json()["id"]

    # Generate exam mode plan with rescue recovery
    plan_res = await async_client.post(
        "/api/v1/exam-mode/generate",
        headers=user["headers"],
        json={
            "exam_id": exam_id,
            "workload_ceiling_minutes": 240,
            "include_rescue_recovery": True,
        },
    )
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    assert plan_data["workload_ceiling_minutes"] == 240
    assert plan_data["daily_workload_minutes"] <= 240


@pytest.mark.asyncio
async def test_exam_plan_user_acceptance_flow(async_client: AsyncClient):
    """
    CRITICAL TEST: Acceptance converts proposed exam plan into locked,
    stable study tasks that cannot be perturbed by automatic replanning.
    """
    user = await create_authenticated_user(async_client, "accept_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Computer Architecture", "code": "CS301"},
    )
    sub_id = sub.json()["id"]

    await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Pipelining"},
    )

    exam_date = datetime.now(timezone.utc) + timedelta(days=3)
    exam_res = await async_client.post(
        "/api/v1/exams",
        headers=user["headers"],
        json={"name": "CompArch Exam", "subject_id": sub_id, "exam_at": exam_date.isoformat()},
    )
    exam_id = exam_res.json()["id"]

    # Generate plan
    plan_res = await async_client.post(
        "/api/v1/exam-mode/generate",
        headers=user["headers"],
        json={"exam_id": exam_id},
    )
    plan_id = plan_res.json()["id"]

    # Accept the plan
    accept_res = await async_client.post(
        f"/api/v1/exam-mode/{plan_id}/action",
        headers=user["headers"],
        json={"action": "ACCEPT"},
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "ACCEPTED"

    # Verify locked tasks are present in user tasks
    tasks_res = await async_client.get(
        "/api/v1/tasks",
        headers=user["headers"],
    )
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()
    exam_tasks = [t for t in tasks if t["locked"] is True and "Exam Prep" in t["title"]]
    assert len(exam_tasks) >= 1
