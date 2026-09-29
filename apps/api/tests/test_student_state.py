import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient


async def create_authenticated_user(async_client: AsyncClient, email_prefix: str = "user"):
    suffix = uuid.uuid4().hex[:8]
    email = f"{email_prefix}_{suffix}@example.com"
    password = "StrongPassword123!"
    display_name = f"Test User {suffix}"

    res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    assert res.status_code == 201
    token = res.json()["access_token"]
    user_id = res.json()["user"]["id"]
    return {"token": token, "user_id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.mark.asyncio
async def test_student_profile_lifecycle(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "profile_user")

    # 1. Get initial default profile
    get_res = await async_client.get("/api/v1/student/profile", headers=user["headers"])
    assert get_res.status_code == 200
    profile = get_res.json()
    assert profile["timezone"] == "UTC"
    assert profile["user_id"] == user["user_id"]

    # 2. Update profile
    patch_res = await async_client.patch(
        "/api/v1/student/profile",
        headers=user["headers"],
        json={
            "institution": "MIT",
            "degree": "B.S. Computer Science",
            "semester": "Fall 2026",
            "branch": "AI & Systems",
            "timezone": "America/New_York",
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["institution"] == "MIT"
    assert updated["degree"] == "B.S. Computer Science"
    assert updated["timezone"] == "America/New_York"


@pytest.mark.asyncio
async def test_availability_windows(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "avail_user")

    # Set availability windows (Monday 09:00 to 12:00, Wednesday 14:00 to 18:00)
    put_res = await async_client.put(
        "/api/v1/student/availability",
        headers=user["headers"],
        json={
            "windows": [
                {"weekday": 0, "start_time": "09:00:00", "end_time": "12:00:00", "enabled": True},
                {"weekday": 2, "start_time": "14:00:00", "end_time": "18:00:00", "enabled": True},
            ]
        },
    )
    assert put_res.status_code == 200
    windows = put_res.json()
    assert len(windows) == 2
    assert windows[0]["weekday"] == 0
    assert windows[1]["weekday"] == 2


@pytest.mark.asyncio
async def test_goals_crud(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "goal_user")

    # Create goal
    create_res = await async_client.post(
        "/api/v1/student/goals",
        headers=user["headers"],
        json={
            "title": "Master Linear Algebra Basics",
            "target_type": "mastery",
            "target_value": 0.85,
            "priority": 1.5,
        },
    )
    assert create_res.status_code == 201
    goal = create_res.json()
    goal_id = goal["id"]
    assert goal["title"] == "Master Linear Algebra Basics"

    # List goals
    list_res = await async_client.get("/api/v1/student/goals", headers=user["headers"])
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Update goal
    patch_res = await async_client.patch(
        f"/api/v1/student/goals/{goal_id}",
        headers=user["headers"],
        json={"title": "Master Advanced Linear Algebra", "status": "in_progress"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Master Advanced Linear Algebra"

    # Delete goal
    del_res = await async_client.delete(f"/api/v1/student/goals/{goal_id}", headers=user["headers"])
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_academics_subjects_and_tenant_isolation(async_client: AsyncClient):
    user1 = await create_authenticated_user(async_client, "user1")
    user2 = await create_authenticated_user(async_client, "user2")

    # User 1 creates Subject
    s1_res = await async_client.post(
        "/api/v1/subjects",
        headers=user1["headers"],
        json={"name": "Operating Systems", "code": "CS301", "color": "#3B82F6"},
    )
    assert s1_res.status_code == 201
    s1 = s1_res.json()
    s1_id = s1["id"]

    # User 2 lists subjects -> must NOT see User 1's subject
    u2_list = await async_client.get("/api/v1/subjects", headers=user2["headers"])
    assert u2_list.status_code == 200
    assert not any(s["id"] == s1_id for s in u2_list.json())

    # User 2 tries to modify User 1's subject -> 403 Forbidden
    u2_patch = await async_client.patch(
        f"/api/v1/subjects/{s1_id}",
        headers=user2["headers"],
        json={"name": "Hacked Subject"},
    )
    assert u2_patch.status_code == 403
    assert u2_patch.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_topics_hierarchy_and_prerequisites(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "topic_user")

    # Create subject
    sub_res = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Calculus", "code": "MATH101"},
    )
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["id"]

    # Create Topic A: Derivatives
    t1_res = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Derivatives", "syllabus_weight": 2.0},
    )
    assert t1_res.status_code == 201
    t1_id = t1_res.json()["id"]

    # Create Topic B: Integrals (with parent = Derivatives)
    t2_res = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Integrals", "parent_topic_id": t1_id, "syllabus_weight": 2.5},
    )
    assert t2_res.status_code == 201
    t2_id = t2_res.json()["id"]

    # Create prerequisite relationship: Derivatives is prerequisite of Integrals
    rel_res = await async_client.post(
        f"/api/v1/topics/{t1_id}/relationships",
        headers=user["headers"],
        json={
            "target_topic_id": t2_id,
            "relationship_type": "prerequisite",
            "confidence": 1.0,
        },
    )
    assert rel_res.status_code == 201
    assert rel_res.json()["relationship_type"] == "prerequisite"

    # Self-loop rejection test
    self_loop = await async_client.post(
        f"/api/v1/topics/{t1_id}/relationships",
        headers=user["headers"],
        json={
            "target_topic_id": t1_id,
            "relationship_type": "prerequisite",
        },
    )
    assert self_loop.status_code == 400
    assert self_loop.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_assembled_student_state(async_client: AsyncClient):
    user = await create_authenticated_user(async_client, "state_user")

    # Create subject, topic, exam, goal, availability
    sub_res = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Algorithms", "code": "CS202"},
    )
    sub_id = sub_res.json()["id"]

    await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Graph Traversal"},
    )

    exam_time = datetime.now(timezone.utc) + timedelta(days=14)
    await async_client.post(
        "/api/v1/exams",
        headers=user["headers"],
        json={
            "subject_id": sub_id,
            "name": "Midterm Exam",
            "exam_at": exam_time.isoformat(),
        },
    )

    await async_client.post(
        "/api/v1/student/goals",
        headers=user["headers"],
        json={"title": "Score A on Midterm", "target_type": "grade", "target_value": 90.0},
    )

    # Query assembled read-only student state
    state_res = await async_client.get("/api/v1/student/state", headers=user["headers"])
    assert state_res.status_code == 200
    state = state_res.json()

    assert "profile" in state
    assert len(state["subjects"]) == 1
    assert state["subjects"][0]["name"] == "Algorithms"
    assert len(state["topics"]) == 1
    assert state["topics"][0]["name"] == "Graph Traversal"
    assert len(state["exams"]) == 1
    assert state["exams"][0]["name"] == "Midterm Exam"
    assert len(state["goals"]) == 1
    assert state["goals"][0]["title"] == "Score A on Midterm"
    assert "mastery" in state
    assert "memory" in state
    assert "availability" in state


@pytest.mark.asyncio
async def test_student_progress_overview(async_client: AsyncClient):
    """
    STAGE 6 TEST: Verifies aggregated mastery levels (Strong, Developing, Needs Attention, Review Due).
    """
    user = await create_authenticated_user(async_client, "progress_test_user")

    # 1. Setup syllabus via onboarding
    await async_client.post(
        "/api/v1/onboarding/confirm-syllabus",
        headers=user["headers"],
        json={
            "subjects": [
                {
                    "name": "Computer Networks",
                    "code": "CS401",
                    "topics": ["TCP/IP", "DNS Resolution", "Routing Algorithms"],
                }
            ]
        },
    )

    # 2. Get progress overview
    prog_res = await async_client.get("/api/v1/student/progress-overview", headers=user["headers"])
    assert prog_res.status_code == 200
    prog = prog_res.json()

    assert prog["total_subjects"] == 1
    assert prog["total_topics"] == 3
    assert isinstance(prog["overall_mastery_pct"], (int, float))
    assert isinstance(prog["strong_topics"], list)
    assert isinstance(prog["developing_topics"], list)
    assert isinstance(prog["needs_attention_topics"], list)
    assert isinstance(prog["review_due_topics"], list)
    assert prog["total_study_minutes_completed"] >= 0


@pytest.mark.asyncio
async def test_student_suggestions_explainability(async_client: AsyncClient):
    """
    STAGE 7 TEST: Verifies natural language student suggestions explaining 'Why this?'.
    """
    user = await create_authenticated_user(async_client, "suggestions_user")

    # 1. Create subject and upcoming exam in 6 days
    sub_res = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Compiler Design", "code": "CS405"},
    )
    sub_id = sub_res.json()["id"]

    await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Lexical Analysis"},
    )

    exam_time = datetime.now(timezone.utc) + timedelta(days=6)
    await async_client.post(
        "/api/v1/exams",
        headers=user["headers"],
        json={
            "subject_id": sub_id,
            "name": "End Semester Exam",
            "exam_at": exam_time.isoformat(),
        },
    )

    # 2. Fetch suggestions
    sug_res = await async_client.get("/api/v1/student/suggestions", headers=user["headers"])
    assert sug_res.status_code == 200
    sugs = sug_res.json()["suggestions"]
    assert len(sugs) >= 1

    exam_sug = next((s for s in sugs if "End Semester Exam" in s["title"]), None)
    assert exam_sug is not None
    assert exam_sug["priority"] == "HIGH"
    assert "days" in exam_sug["reason"]
    assert exam_sug["action_type"] in ["REVIEW", "PRACTICE", "STUDY"]


@pytest.mark.asyncio
async def test_student_home_dashboard(async_client: AsyncClient):
    """
    STAGE 8 TEST: Verifies student home dashboard payload: top task, next task, daily progress, and summary.
    """
    user = await create_authenticated_user(async_client, "home_dash_user")

    # 1. Setup syllabus
    await async_client.post(
        "/api/v1/onboarding/confirm-syllabus",
        headers=user["headers"],
        json={
            "subjects": [
                {
                    "name": "Software Engineering",
                    "code": "CS305",
                    "topics": ["Agile Methodologies", "Design Patterns"],
                }
            ]
        },
    )

    # 2. Fetch student home dashboard
    home_res = await async_client.get("/api/v1/student/home", headers=user["headers"])
    assert home_res.status_code == 200
    home = home_res.json()

    assert "student_name" in home
    assert "academic_summary" in home
    assert "today_target_minutes" in home
    assert home["today_target_minutes"] >= 30
    assert "today_completed_minutes" in home
    assert "overall_mastery_pct" in home
    assert home["subjects_count"] == 1

