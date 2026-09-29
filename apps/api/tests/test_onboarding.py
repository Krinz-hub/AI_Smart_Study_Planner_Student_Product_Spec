import uuid
import pytest
from httpx import AsyncClient

from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_onboarding_status_initial_state(async_client: AsyncClient):
    """
    STAGE 2 TEST: Verifies new student onboarding initializes at ACADEMIC_TYPE.
    """
    user = await create_authenticated_user(async_client, "onboarding_init_user")

    res = await async_client.get("/api/v1/onboarding/status", headers=user["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["current_step"] == "ACADEMIC_TYPE"
    assert data["academic_type"] is None
    assert data["academic_details"] == {}
    assert data["is_completed"] is False


@pytest.mark.asyncio
async def test_onboarding_select_academic_type_advances_step(async_client: AsyncClient):
    """
    STAGE 2 TEST: Selecting educational track advances state to ACADEMIC_PROFILE.
    """
    user = await create_authenticated_user(async_client, "onboarding_type_user")

    type_res = await async_client.post(
        "/api/v1/onboarding/academic-type",
        headers=user["headers"],
        json={"academic_type": "COLLEGE"},
    )
    assert type_res.status_code == 200
    data = type_res.json()
    assert data["academic_type"] == "COLLEGE"
    assert data["current_step"] == "ACADEMIC_PROFILE"


@pytest.mark.asyncio
async def test_onboarding_save_college_profile_advances_to_discovery(async_client: AsyncClient):
    """
    STAGE 2 TEST: Saving valid college details persists in MongoDB and advances to ACADEMIC_DISCOVERY.
    """
    user = await create_authenticated_user(async_client, "onboarding_college_user")

    # 1. Set type to COLLEGE
    await async_client.post(
        "/api/v1/onboarding/academic-type",
        headers=user["headers"],
        json={"academic_type": "COLLEGE"},
    )

    # 2. Submit College Details
    college_details = {
        "country": "India",
        "university": "Anna University",
        "college": "College of Engineering Guindy",
        "degree": "B.Tech",
        "branch": "Computer Science and Engineering",
        "year": 2,
        "semester": 3,
        "academic_year": "2026-2027",
    }
    prof_res = await async_client.post(
        "/api/v1/onboarding/academic-profile",
        headers=user["headers"],
        json={"details": college_details},
    )
    assert prof_res.status_code == 200
    data = prof_res.json()
    assert data["current_step"] == "ACADEMIC_DISCOVERY"
    assert data["academic_details"]["university"] == "Anna University"
    assert data["academic_details"]["semester"] == 3
    assert data["academic_details"]["degree"] == "B.Tech"

    # 3. Verify GET /onboarding/status returns updated state
    status_res = await async_client.get("/api/v1/onboarding/status", headers=user["headers"])
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["current_step"] == "ACADEMIC_DISCOVERY"
    assert status_data["academic_details"]["college"] == "College of Engineering Guindy"


@pytest.mark.asyncio
async def test_onboarding_save_school_profile(async_client: AsyncClient):
    """
    STAGE 2 TEST: Saving valid school details (board, grade) succeeds and advances step.
    """
    user = await create_authenticated_user(async_client, "onboarding_school_user")

    # Set type to SCHOOL
    await async_client.post(
        "/api/v1/onboarding/academic-type",
        headers=user["headers"],
        json={"academic_type": "SCHOOL"},
    )

    school_details = {
        "country": "India",
        "board": "CBSE",
        "grade": "Class 12",
        "school_name": "Delhi Public School",
        "academic_year": "2026-2027",
    }
    prof_res = await async_client.post(
        "/api/v1/onboarding/academic-profile",
        headers=user["headers"],
        json={"details": school_details},
    )
    assert prof_res.status_code == 200
    data = prof_res.json()
    assert data["current_step"] == "ACADEMIC_DISCOVERY"
    assert data["academic_details"]["board"] == "CBSE"
    assert data["academic_details"]["grade"] == "Class 12"


@pytest.mark.asyncio
async def test_onboarding_invalid_profile_details_rejected(async_client: AsyncClient):
    """
    STAGE 2 TEST: Missing mandatory fields (e.g. missing university for college) returns 400 Bad Request.
    """
    user = await create_authenticated_user(async_client, "onboarding_invalid_user")

    await async_client.post(
        "/api/v1/onboarding/academic-type",
        headers=user["headers"],
        json={"academic_type": "COLLEGE"},
    )

    # Missing university and degree
    invalid_details = {
        "branch": "Computer Science",
        "year": 2,
    }
    res = await async_client.post(
        "/api/v1/onboarding/academic-profile",
        headers=user["headers"],
        json={"details": invalid_details},
    )
    assert res.status_code == 400
    err = res.json()["error"]
    assert "Invalid COLLEGE academic profile details" in err["message"]


@pytest.mark.asyncio
async def test_onboarding_tenant_isolation(async_client: AsyncClient):
    """
    STAGE 2 TEST: User A's academic profile is completely isolated from User B.
    """
    user_a = await create_authenticated_user(async_client, "tenant_onboard_a")
    user_b = await create_authenticated_user(async_client, "tenant_onboard_b")

    # User A sets college details
    await async_client.post(
        "/api/v1/onboarding/academic-type",
        headers=user_a["headers"],
        json={"academic_type": "COLLEGE"},
    )
    await async_client.post(
        "/api/v1/onboarding/academic-profile",
        headers=user_a["headers"],
        json={
            "details": {
                "university": "Harvard University",
                "degree": "B.S.",
                "branch": "Applied Mathematics",
                "year": 1,
                "semester": 1,
            }
        },
    )

    # User B checks status -> must be initial pristine state, not User A's data
    b_res = await async_client.get("/api/v1/onboarding/status", headers=user_b["headers"])
    assert b_res.status_code == 200
    b_data = b_res.json()
    assert b_data["current_step"] == "ACADEMIC_TYPE"
    assert b_data["academic_type"] is None
    assert b_data["academic_details"] == {}


@pytest.mark.asyncio
async def test_onboarding_discover_syllabus_flow(async_client: AsyncClient):
    """
    STAGE 3 TEST: Academic Discovery automatically discovers syllabus,
    ranks official sources, and advances state to SYLLABUS_REVIEW in MongoDB.
    """
    user = await create_authenticated_user(async_client, "discovery_test_user")

    # Set profile to College
    await async_client.post(
        "/api/v1/onboarding/academic-type",
        headers=user["headers"],
        json={"academic_type": "COLLEGE"},
    )
    await async_client.post(
        "/api/v1/onboarding/academic-profile",
        headers=user["headers"],
        json={
            "details": {
                "country": "India",
                "university": "Anna University",
                "degree": "B.Tech",
                "branch": "Computer Science and Engineering",
                "year": 2,
                "semester": 3,
            }
        },
    )

    # Trigger Discovery
    disc_res = await async_client.post("/api/v1/onboarding/discover-syllabus", headers=user["headers"])
    assert disc_res.status_code == 200
    data = disc_res.json()

    assert data["confidence_score"] >= 0.90
    assert len(data["sources"]) >= 1
    assert "Official" in data["sources"][0]["title"]
    assert len(data["subjects"]) >= 3

    sub_names = [s["name"] for s in data["subjects"]]
    assert "Operating Systems" in sub_names
    assert "Database Management Systems" in sub_names

    # Verify MongoDB state advanced to SYLLABUS_REVIEW
    status_res = await async_client.get("/api/v1/onboarding/status", headers=user["headers"])
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["current_step"] == "SYLLABUS_REVIEW"
    assert status_data["discovered_syllabus"] is not None


@pytest.mark.asyncio
async def test_onboarding_confirm_and_persist_syllabus_flow(async_client: AsyncClient):
    """
    STAGE 3 TEST: Student reviews and confirms syllabus.
    Persists subjects and topics into relational PostgreSQL and advances to GOALS_EXAMS.
    """
    user = await create_authenticated_user(async_client, "confirm_syllabus_user")

    # Submit Confirmed Syllabus
    confirmation_payload = {
        "subjects": [
            {
                "name": "Operating Systems",
                "code": "CS301",
                "color_code": "#0284c7",
                "topics": ["Processes & Threads", "CPU Scheduling", "Virtual Memory", "Deadlocks"],
            },
            {
                "name": "Database Management Systems",
                "code": "CS302",
                "color_code": "#059669",
                "topics": ["Relational Algebra", "SQL Joins", "B-Tree Indexing", "Transaction Isolation"],
            },
        ]
    }
    confirm_res = await async_client.post(
        "/api/v1/onboarding/confirm-syllabus",
        headers=user["headers"],
        json=confirmation_payload,
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["status"] == "success"
    assert confirm_data["subjects_created"] == 2
    assert confirm_data["topics_created"] == 8
    assert confirm_data["current_step"] == "GOALS_EXAMS"

    # Verify PostgreSQL relational subjects endpoint now returns the confirmed subjects!
    subjects_res = await async_client.get("/api/v1/subjects", headers=user["headers"])
    assert subjects_res.status_code == 200
    subs = subjects_res.json()
    assert len(subs) == 2
    sub_names = {s["name"] for s in subs}
    assert "Operating Systems" in sub_names
    assert "Database Management Systems" in sub_names

    # Verify topics under first subject
    os_sub = next(s for s in subs if s["name"] == "Operating Systems")
    topics_res = await async_client.get(f"/api/v1/subjects/{os_sub['id']}/topics", headers=user["headers"])
    assert topics_res.status_code == 200
    topics = topics_res.json()
    assert len(topics) == 4

    # Verify MongoDB onboarding state is now GOALS_EXAMS
    status_res = await async_client.get("/api/v1/onboarding/status", headers=user["headers"])
    assert status_res.status_code == 200
    assert status_res.json()["current_step"] == "GOALS_EXAMS"


@pytest.mark.asyncio
async def test_onboarding_goals_and_availability_advances_to_diagnostic(async_client: AsyncClient):
    """
    STAGE 4 TEST: Configures exams, mastery goals, daily capacity, and weekly availability.
    Advances onboarding state to DIAGNOSTIC.
    """
    user = await create_authenticated_user(async_client, "goals_avail_user")

    # 1. Setup syllabus first
    await async_client.post(
        "/api/v1/onboarding/confirm-syllabus",
        headers=user["headers"],
        json={
            "subjects": [
                {
                    "name": "Linear Algebra",
                    "code": "MATH201",
                    "topics": ["Vector Spaces", "Eigenvalues", "Matrix Factorization"],
                }
            ]
        },
    )

    # 2. Submit Goals & Availability
    goals_payload = {
        "daily_capacity_minutes": 180,
        "study_time_preference": "evening",
        "exams": [
            {
                "name": "Midterm Examination",
                "exam_at": "2026-10-15T09:00:00Z",
            }
        ],
        "goals": [
            {
                "title": "Master Eigenvalues & Matrix Inverses",
                "target_type": "mastery",
                "target_value": 0.90,
                "priority": 1.5,
            }
        ],
        "weekly_availability": [
            {"weekday": 0, "start_time": "18:00", "end_time": "21:00", "enabled": True},
            {"weekday": 1, "start_time": "18:00", "end_time": "21:00", "enabled": True},
            {"weekday": 2, "start_time": "18:00", "end_time": "21:00", "enabled": True},
            {"weekday": 3, "start_time": "18:00", "end_time": "21:00", "enabled": True},
            {"weekday": 4, "start_time": "18:00", "end_time": "21:00", "enabled": True},
        ],
    }

    res = await async_client.post(
        "/api/v1/onboarding/goals-availability",
        headers=user["headers"],
        json=goals_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["exams_created"] == 1
    assert data["goals_created"] == 1
    assert data["availability_slots_created"] == 5
    assert data["daily_capacity_minutes"] == 180
    assert data["current_step"] == "DIAGNOSTIC"

    # Verify status in MongoDB
    status_res = await async_client.get("/api/v1/onboarding/status", headers=user["headers"])
    assert status_res.status_code == 200
    assert status_res.json()["current_step"] == "DIAGNOSTIC"


@pytest.mark.asyncio
async def test_onboarding_diagnostic_generate_and_submit_creates_first_plan(async_client: AsyncClient):
    """
    STAGE 5 TEST: Generates diagnostic test with concealed answers, submits answers,
    initializes BKT mastery states, produces first study plan, and completes onboarding!
    """
    user = await create_authenticated_user(async_client, "diagnostic_user")

    # 1. Setup syllabus
    await async_client.post(
        "/api/v1/onboarding/confirm-syllabus",
        headers=user["headers"],
        json={
            "subjects": [
                {
                    "name": "Data Structures",
                    "code": "CS201",
                    "topics": ["Binary Search Trees", "Hash Tables"],
                }
            ]
        },
    )

    # 2. Setup goals & availability
    await async_client.post(
        "/api/v1/onboarding/goals-availability",
        headers=user["headers"],
        json={
            "daily_capacity_minutes": 120,
            "study_time_preference": "morning",
            "exams": [],
            "goals": [],
            "weekly_availability": [
                {"weekday": i, "start_time": "09:00", "end_time": "11:00", "enabled": True}
                for i in range(7)
            ],
        },
    )

    # 3. Generate Diagnostic Test
    diag_res = await async_client.get("/api/v1/onboarding/diagnostic/generate", headers=user["headers"])
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    assert diag_data["status"] == "success"
    assert diag_data["total_questions"] >= 2
    for q in diag_data["questions"]:
        assert "question_text" in q
        assert "options" in q
        assert len(q["options"]) > 0
        # CRITICAL PRIVACY/INTEGRITY CHECK: correct_answer must NOT be exposed to student
        assert "correct_answer" not in q

    # 4. Submit Diagnostic Answers
    submissions = [
        {"question_id": q["id"], "selected_key": "A", "response_time_seconds": 15}
        for q in diag_data["questions"]
    ]
    submit_res = await async_client.post(
        "/api/v1/onboarding/diagnostic/submit",
        headers=user["headers"],
        json={"answers": submissions},
    )
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    assert sub_data["status"] == "success"
    assert sub_data["total_answered"] == len(submissions)
    assert "accuracy_pct" in sub_data
    assert len(sub_data["topic_masteries"]) >= 2
    assert sub_data["plan_tasks_scheduled"] >= 0
    assert sub_data["current_step"] == "COMPLETED"
    assert sub_data["is_completed"] is True

    # 5. Verify onboarding status is COMPLETED
    status_res = await async_client.get("/api/v1/onboarding/status", headers=user["headers"])
    assert status_res.status_code == 200
    final_status = status_res.json()
    assert final_status["current_step"] == "COMPLETED"
    assert final_status["is_completed"] is True

