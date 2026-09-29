import uuid
from datetime import datetime, timezone, timedelta, date, time
import pytest
from httpx import AsyncClient
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_plan_generation_and_no_overlaps(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "planner_user")

    # Create Subject & 3 Topics
    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Software Engineering", "code": "CS350"},
    )
    sub_id = sub.json()["id"]

    for name in ["Design Patterns", "Clean Architecture", "Unit Testing"]:
        await async_client.post(
            f"/api/v1/subjects/{sub_id}/topics",
            headers=user["headers"],
            json={"name": name},
        )

    # Set availability windows (Monday to Sunday 10:00 to 14:00)
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

    # Generate plan for the next 7 days
    today = date.today()
    gen_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat(),
            "daily_capacity_minutes": 240,
        },
    )
    assert gen_res.status_code == 201
    plan = gen_res.json()
    assert plan["total_tasks"] >= 3
    tasks = plan["tasks"]

    # Verify Hard Constraint: Non-overlapping intervals
    for i in range(len(tasks) - 1):
        t1_end = datetime.fromisoformat(tasks[i]["planned_end"])
        t2_start = datetime.fromisoformat(tasks[i + 1]["planned_start"])
        # Next task must start at or after previous task end
        assert t2_start >= t1_end


@pytest.mark.asyncio
async def test_daily_capacity_constraint(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "capacity_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Physics"},
    )
    sub_id = sub.json()["id"]

    for i in range(6):
        await async_client.post(
            f"/api/v1/subjects/{sub_id}/topics",
            headers=user["headers"],
            json={"name": f"Physics Topic {i+1}"},
        )

    # Set wide availability (10 hours available every day)
    await async_client.put(
        "/api/v1/student/availability",
        headers=user["headers"],
        json={
            "windows": [
                {"weekday": i, "start_time": "08:00:00", "end_time": "18:00:00", "enabled": True}
                for i in range(7)
            ]
        },
    )

    # Hard cap: 90 minutes per day (exactly two 45-min sessions max per day)
    today = date.today()
    gen_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat(),
            "daily_capacity_minutes": 90,
        },
    )
    assert gen_res.status_code == 201
    tasks = gen_res.json()["tasks"]

    # Check tasks grouped by day
    tasks_per_day = {}
    for t in tasks:
        start_dt = datetime.fromisoformat(t["planned_start"])
        day_key = start_dt.date()
        tasks_per_day[day_key] = tasks_per_day.get(day_key, 0) + t["duration_minutes"]

    for day_k, minutes in tasks_per_day.items():
        assert minutes <= 90, f"Daily capacity exceeded on {day_k}: {minutes} > 90"


@pytest.mark.asyncio
async def test_locked_task_preservation(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "lock_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Chemistry"},
    )
    sub_id = sub.json()["id"]

    top = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Organic Chemistry"},
    )
    topic_id = top.json()["id"]

    # Generate initial plan
    today = date.today()
    gen_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat(),
            "daily_capacity_minutes": 180,
        },
    )
    assert gen_res.status_code == 201
    initial_tasks = gen_res.json()["tasks"]
    assert len(initial_tasks) >= 1
    task_to_lock = initial_tasks[0]
    task_id = task_to_lock["id"]
    locked_start = task_to_lock["planned_start"]

    # Lock the task
    lock_res = await async_client.post(
        f"/api/v1/tasks/{task_id}/lock",
        headers=user["headers"],
        json={"locked": True},
    )
    assert lock_res.status_code == 200
    assert lock_res.json()["locked"] is True

    # Re-generate plan -> The locked task must be preserved at its exact start time
    regen_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat(),
            "daily_capacity_minutes": 180,
        },
    )
    assert regen_res.status_code == 201
    new_tasks = regen_res.json()["tasks"]
    preserved = next((t for t in new_tasks if t["id"] == task_id), None)
    assert preserved is not None
    assert preserved["locked"] is True
    assert preserved["planned_start"] == locked_start


@pytest.mark.asyncio
async def test_exam_deadline_hard_constraint(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "exam_deadline_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Operating Systems"},
    )
    sub_id = sub.json()["id"]

    await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Process Synchronization"},
    )

    # Exam is scheduled in 3 days at 15:00 UTC
    exam_dt = datetime.now(timezone.utc) + timedelta(days=3)
    await async_client.post(
        "/api/v1/exams",
        headers=user["headers"],
        json={"subject_id": sub_id, "name": "OS Midterm", "exam_at": exam_dt.isoformat()},
    )

    # Generate plan
    today = date.today()
    gen_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat(),
            "daily_capacity_minutes": 180,
        },
    )
    assert gen_res.status_code == 201
    tasks = gen_res.json()["tasks"]
    os_tasks = [t for t in tasks if t["subject_id"] == sub_id]

    # Hard constraint: all OS tasks must complete BEFORE the exam!
    for t in os_tasks:
        end_time = datetime.fromisoformat(t["planned_end"])
        assert end_time <= exam_dt, f"Task {t['title']} ends after exam! {end_time} > {exam_dt}"


@pytest.mark.asyncio
async def test_overloaded_backlog_handles_capacity(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "backlog_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Large Syllabus"},
    )
    sub_id = sub.json()["id"]

    # Create 12 topics
    for i in range(12):
        await async_client.post(
            f"/api/v1/subjects/{sub_id}/topics",
            headers=user["headers"],
            json={"name": f"Module {i+1}"},
        )

    # Restrict availability to only 1 day with 90 minutes (can only fit 2 tasks)
    today = date.today()
    weekday = today.weekday()
    await async_client.put(
        "/api/v1/student/availability",
        headers=user["headers"],
        json={
            "windows": [
                {"weekday": weekday, "start_time": "14:00:00", "end_time": "15:30:00", "enabled": True}
            ]
        },
    )

    gen_res = await async_client.post(
        "/api/v1/plans/generate",
        headers=user["headers"],
        json={
            "start_date": today.isoformat(),
            "end_date": today.isoformat(),
            "daily_capacity_minutes": 90,
        },
    )
    assert gen_res.status_code == 201
    plan = gen_res.json()
    # Must gracefully schedule only what fits, without violating capacity!
    assert len(plan["tasks"]) <= 2
