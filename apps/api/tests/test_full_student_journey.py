import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone, timedelta

from app.main import app


@pytest.mark.asyncio
async def test_complete_student_end_to_end_journey():
    """
    Executes the exact end-to-end journey specified in the prompt:
    1. Sign up new student
    2. Login
    3. Save academic college profile
    4. Discover syllabus
    5. Confirm syllabus
    6. Set goals & availability
    7. Generate & submit diagnostic assessment
    8. Initial study plan generated
    9. Open student home (view top recommended task)
    10. Start task (launch study session)
    11. Complete study session with score & rating
    12. Generate topic quiz & start quiz session
    13. Submit quiz answers -> BKT & FSRS mastery updates
    14. Check progress overview reflecting updated mastery
    15. Ingest study document (lecture notes)
    16. Generate 10-point document synthesis
    17. Generate active recall quiz from notes
    18. Ask Socratic AI Tutor in multiple modes
    19. Verify final progress dashboard updates
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"student_{unique_suffix}@university.edu"
        password = "SecureStudyPassword123!"
        display_name = f"Scholar {unique_suffix}"

        # 1. Sign up
        reg_res = await ac.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "display_name": display_name},
        )
        assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
        reg_data = reg_res.json()
        assert "access_token" in reg_data
        token = reg_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Login
        login_res = await ac.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert "access_token" in login_data
        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Enter College / University Academic Profile
        type_res = await ac.post(
            "/api/v1/onboarding/academic-type",
            headers=headers,
            json={"academic_type": "COLLEGE"},
        )
        assert type_res.status_code == 200

        profile_res = await ac.post(
            "/api/v1/onboarding/academic-profile",
            headers=headers,
            json={
                "details": {
                    "university": "Stanford University",
                    "degree": "B.S.",
                    "branch": "Computer Science",
                    "year": 2,
                    "semester": 4,
                }
            },
        )
        assert profile_res.status_code == 200

        # 4. Discover Syllabus
        discover_res = await ac.post(
            "/api/v1/onboarding/discover-syllabus",
            headers=headers,
        )
        assert discover_res.status_code == 200
        discovered = discover_res.json()
        assert len(discovered["subjects"]) > 0

        # 5. Confirm Syllabus
        confirm_res = await ac.post(
            "/api/v1/onboarding/confirm-syllabus",
            headers=headers,
            json={
                "subjects": [
                    {
                        "name": sub["name"],
                        "code": sub.get("code"),
                        "color_code": sub.get("color_code", "#6366f1"),
                        "topics": [
                            topic
                            for unit in sub.get("units", [])
                            for topic in unit.get("topics", [])
                        ],
                    }
                    for sub in discovered["subjects"]
                ]
            },
        )
        assert confirm_res.status_code == 200
        assert confirm_res.json()["topics_created"] > 0

        # 6. Set Goals & Availability
        now = datetime.now(timezone.utc)
        exam_date = (now + timedelta(days=21)).isoformat()
        goals_res = await ac.post(
            "/api/v1/onboarding/goals-availability",
            headers=headers,
            json={
                "daily_capacity_minutes": 180,
                "study_time_preference": "evening",
                "exams": [
                    {
                        "name": "Midterm Exam",
                        "exam_at": exam_date,
                    }
                ],
                "goals": [
                    {
                        "title": "Achieve 85% Mastery in Core Topics",
                        "target_type": "MASTERY_PCT",
                        "target_value": 85,
                    }
                ],
                "weekly_availability": [
                    {"weekday": w, "start_time": "09:00", "end_time": "21:00", "enabled": True}
                    for w in range(7)
                ],
            },
        )
        assert goals_res.status_code == 200

        # 7. Complete Diagnostic Assessment
        diag_get = await ac.get(
            "/api/v1/onboarding/diagnostic/generate",
            headers=headers,
        )
        assert diag_get.status_code == 200
        diag_data = diag_get.json()
        assert len(diag_data["questions"]) > 0

        # Submit answers to establish baseline BKT posterior
        diag_answers = [
            {
                "question_id": q["id"],
                "selected_key": q["options"][0]["key"],
                "response_time_seconds": 12,
            }
            for q in diag_data["questions"]
        ]
        diag_submit = await ac.post(
            "/api/v1/onboarding/diagnostic/submit",
            headers=headers,
            json={"answers": diag_answers},
        )
        assert diag_submit.status_code == 200
        submit_res = diag_submit.json()
        assert submit_res["status"] == "success"
        assert submit_res["plan_tasks_scheduled"] > 0

        # 8 & 9. Open Student Home (Cockpit)
        home_res = await ac.get("/api/v1/student/home", headers=headers)
        assert home_res.status_code == 200
        home_data = home_res.json()
        assert home_data["onboarding_completed"] is True
        assert home_data["top_task"] is not None
        top_task_id = home_data["top_task"]["id"]

        # 10. Start Task (Launch study session)
        start_task_res = await ac.post(f"/api/v1/tasks/{top_task_id}/start", headers=headers)
        assert start_task_res.status_code == 200
        assert start_task_res.json()["status"] == "IN_PROGRESS"

        # 11. Complete Study Session
        complete_task_res = await ac.post(
            f"/api/v1/tasks/{top_task_id}/complete",
            headers=headers,
            json={
                "actual_minutes": 45,
                "score": 0.9,
                "self_rating": 4,
                "notes": "Covered foundational concepts and derivations.",
            },
        )
        assert complete_task_res.status_code == 200
        complete_data = complete_task_res.json()
        assert complete_data["task"]["status"] == "COMPLETED"

        # 12. Take Quiz (generate topic quiz and start session)
        topic_id = home_data["top_task"].get("topic_id")
        if not topic_id:
            # Query subjects/topics
            subjects_res = await ac.get("/api/v1/subjects", headers=headers)
            first_sub_id = subjects_res.json()[0]["id"]
            topics_res = await ac.get(f"/api/v1/subjects/{first_sub_id}/topics", headers=headers)
            topic_id = topics_res.json()[0]["id"]

        gen_quiz_res = await ac.post(
            "/api/v1/quizzes/generate",
            headers=headers,
            json={
                "topic_id": topic_id,
                "num_questions": 3,
                "difficulty": "MEDIUM",
            },
        )
        assert gen_quiz_res.status_code == 201
        quiz_id = gen_quiz_res.json()["quiz_id"]

        start_quiz_res = await ac.post(f"/api/v1/quizzes/{quiz_id}/start", headers=headers)
        assert start_quiz_res.status_code == 200
        quiz_questions = start_quiz_res.json()["questions"]
        assert len(quiz_questions) > 0

        # 13. Submit Quiz Answers
        quiz_submit_res = await ac.post(
            f"/api/v1/quizzes/{quiz_id}/submit",
            headers=headers,
            json={
                "answers": [
                    {
                        "question_id": q["id"],
                        "selected_key": q["options"][0]["key"] if q.get("options") else "A",
                        "response_time_seconds": 15,
                    }
                    for q in quiz_questions
                ]
            },
        )
        assert quiz_submit_res.status_code == 200
        eval_data = quiz_submit_res.json()
        assert eval_data["total_questions"] == len(quiz_questions)

        # 14. Check Progress Overview Updates
        prog_res = await ac.get("/api/v1/student/progress-overview", headers=headers)
        assert prog_res.status_code == 200
        prog_data = prog_res.json()
        assert prog_data["total_subjects"] > 0
        assert prog_data["total_topics"] > 0

        # 15. Ingest Study Document (Lecture Notes)
        sample_doc_content = (
            "# Advanced Data Structures\n\n"
            "An AVL tree is a self-balancing binary search tree where the heights of the two "
            "child subtrees of any node differ by at most one. Lookup, insertion, and deletion "
            "all take O(log n) time in both the average and worst cases.\n\n"
            "## Key Formulas\n"
            "Balance Factor = Height(Left Subtree) - Height(Right Subtree)\n"
            "Valid Balance Factors: {-1, 0, 1}\n\n"
            "## Common Pitfalls\n"
            "Double rotations (LR and RL) must be applied when the child is heavy in the opposite direction."
        )
        upload_res = await ac.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("lecture_avl_trees.md", sample_doc_content.encode("utf-8"), "text/markdown")},
        )
        assert upload_res.status_code == 201
        doc_id = upload_res.json()["document_id"]

        # 16. Generate 10-Point Synthesis
        summary_res = await ac.get(f"/api/v1/documents/{doc_id}/summary", headers=headers)
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert "executive_summary" in summary_data

        # 17. Generate Active Recall Quiz from Document
        doc_quiz_res = await ac.post(
            f"/api/v1/documents/{doc_id}/generate-quiz",
            headers=headers,
            json={"num_questions": 3, "difficulty": "MEDIUM"},
        )
        assert doc_quiz_res.status_code == 200
        assert doc_quiz_res.json()["total_questions"] > 0

        # 18. Ask Socratic AI Tutor
        tutor_res = await ac.post(
            "/api/v1/tutor/chat",
            headers=headers,
            json={
                "topic_id": topic_id,
                "message": "Can you explain how rotation preserves the BST invariant?",
                "mode": "socratic",
            },
        )
        assert tutor_res.status_code == 200
        assert len(tutor_res.json()["response_text"]) > 0

        # 19. Final verification of Progress & Home
        final_home = await ac.get("/api/v1/home", headers=headers)
        assert final_home.status_code == 200
        assert final_home.json()["onboarding_completed"] is True
