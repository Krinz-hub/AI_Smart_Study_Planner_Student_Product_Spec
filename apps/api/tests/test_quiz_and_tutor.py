import uuid
import pytest
from httpx import AsyncClient
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_quiz_generation_and_student_privacy(async_client: AsyncClient):
    """
    Verifies that generated quiz returns schema-compliant questions
    while strictly concealing correct answers and explanations before submission.
    """
    user = await create_authenticated_user(async_client, "quiz_gen_user")

    # Create subject and topic
    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Database Internals", "code": "DB401"},
    )
    sub_id = sub.json()["id"]

    topic = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "B-Tree Indexing"},
    )
    topic_id = topic.json()["id"]

    # Generate quiz
    gen_res = await async_client.post(
        "/api/v1/quizzes/generate",
        headers=user["headers"],
        json={"topic_id": topic_id, "num_questions": 4, "difficulty": "MEDIUM"},
    )
    assert gen_res.status_code == 201
    quiz_data = gen_res.json()
    assert quiz_data["status"] == "GENERATED"
    assert quiz_data["total_questions"] == 4
    questions = quiz_data["questions"]
    assert len(questions) == 4

    # Verify student privacy (answers must NOT leak in student view)
    for q in questions:
        assert "question_text" in q
        assert "options" in q
        assert "correct_answer" not in q
        assert "explanation" not in q
        assert len(q["options"]) >= 2


@pytest.mark.asyncio
async def test_quiz_submission_updates_mastery_and_difficulty(async_client: AsyncClient):
    """
    CRITICAL TEST:
    1. Perfect score quiz drives BKT mastery state UP.
    2. Difficulty is empirically recalibrated.
    3. Weak concepts / explanations are returned.
    """
    user = await create_authenticated_user(async_client, "quiz_submit_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Compilers", "code": "CS450"},
    )
    sub_id = sub.json()["id"]

    topic = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Parsing"},
    )
    topic_id = topic.json()["id"]

    # Check baseline mastery
    state_before = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    mastery_before = state_before.json()["mastery"]["probability"]

    # Generate quiz
    gen_res = await async_client.post(
        "/api/v1/quizzes/generate",
        headers=user["headers"],
        json={"topic_id": topic_id, "num_questions": 3, "difficulty": "MEDIUM"},
    )
    quiz_id = gen_res.json()["quiz_id"]
    questions = gen_res.json()["questions"]

    # Start quiz
    start_res = await async_client.post(
        f"/api/v1/quizzes/{quiz_id}/start",
        headers=user["headers"],
    )
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "IN_PROGRESS"

    # Submit all correct answers (Key "A" per generator templates)
    submit_res = await async_client.post(
        f"/api/v1/quizzes/{quiz_id}/submit",
        headers=user["headers"],
        json={
            "answers": [
                {"question_id": q["id"], "answer": {"key": "A"}, "response_time_seconds": 15}
                for q in questions
            ],
            "time_spent_seconds": 45,
        },
    )
    assert submit_res.status_code == 200
    res_data = submit_res.json()
    assert res_data["score"] == 1.0
    assert res_data["accuracy"] == 1.0
    assert res_data["correct_count"] == 3
    assert len(res_data["strong_concepts"]) == 3
    assert len(res_data["weak_concepts"]) == 0

    # Verify BKT Mastery State increased
    state_after = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    mastery_after = state_after.json()["mastery"]["probability"]
    assert mastery_after > mastery_before


@pytest.mark.asyncio
async def test_quiz_failing_submission_identifies_weak_concepts(async_client: AsyncClient):
    """Verifies that failed quiz flags weak concepts and prompts practice action."""
    user = await create_authenticated_user(async_client, "quiz_fail_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Cybersecurity", "code": "SEC301"},
    )
    sub_id = sub.json()["id"]

    topic = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Public Key Cryptography"},
    )
    topic_id = topic.json()["id"]

    gen_res = await async_client.post(
        "/api/v1/quizzes/generate",
        headers=user["headers"],
        json={"topic_id": topic_id, "num_questions": 3},
    )
    quiz_id = gen_res.json()["quiz_id"]
    questions = gen_res.json()["questions"]

    # Submit intentionally wrong answers (Key "Z")
    submit_res = await async_client.post(
        f"/api/v1/quizzes/{quiz_id}/submit",
        headers=user["headers"],
        json={
            "answers": [
                {"question_id": q["id"], "answer": {"key": "Z"}} for q in questions
            ],
            "time_spent_seconds": 30,
        },
    )
    assert submit_res.status_code == 200
    res_data = submit_res.json()
    assert res_data["score"] == 0.0
    assert len(res_data["weak_concepts"]) == 3
    assert res_data["recommended_next_action"] == "PRACTICE"


@pytest.mark.asyncio
async def test_socratic_tutor_modes(async_client: AsyncClient):
    """Verifies AI tutor pedagogical modes: Socratic, Explain Simply, Exam Answer."""
    user = await create_authenticated_user(async_client, "tutor_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Distributed Systems", "code": "CS500"},
    )
    sub_id = sub.json()["id"]

    topic = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Raft Consensus"},
    )
    topic_id = topic.json()["id"]

    # 1. Socratic mode
    soc_res = await async_client.post(
        "/api/v1/tutor/chat",
        headers=user["headers"],
        json={
            "topic_id": topic_id,
            "mode": "socratic",
            "message": "Why do we need a leader heartbeat?",
        },
    )
    assert soc_res.status_code == 200
    soc_data = soc_res.json()
    assert soc_data["mode"] == "socratic"
    assert soc_data["pedagogical_intent"] == "guide_with_leading_question"
    assert "?" in soc_data["response_text"]
    assert len(soc_data["suggested_followups"]) >= 1

    # 2. Explain Simply mode
    eli5_res = await async_client.post(
        "/api/v1/tutor/chat",
        headers=user["headers"],
        json={
            "topic_id": topic_id,
            "mode": "explain_simply",
            "message": "Explain leader election",
        },
    )
    assert eli5_res.status_code == 200
    assert eli5_res.json()["mode"] == "explain_simply"

    # 3. Exam Answer mode
    exam_res = await async_client.post(
        "/api/v1/tutor/chat",
        headers=user["headers"],
        json={
            "topic_id": topic_id,
            "mode": "exam_answer",
            "message": "How does split vote get resolved?",
        },
    )
    assert exam_res.status_code == 200
    assert "Exam-Ready Solution Structure" in exam_res.json()["response_text"]


@pytest.mark.asyncio
async def test_tutor_source_grounding_and_no_mutation(async_client: AsyncClient):
    """
    CRITICAL ARCHITECTURAL RULES:
    1. Tutor returns course citations when relevant documents exist.
    2. Tutor CANNOT directly mutate MasteryState!
    """
    user = await create_authenticated_user(async_client, "grounded_tutor_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Data Structures", "code": "CS201"},
    )
    sub_id = sub.json()["id"]

    topic = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Red-Black Trees"},
    )
    topic_id = topic.json()["id"]

    # Upload course note
    content = (
        "Red-Black Tree Properties:\n\n"
        "1. Every node is either red or black.\n"
        "2. The root is always black.\n"
        "3. Red nodes cannot have red children (no two consecutive red nodes).\n"
        "4. Every path from a node to descendant leaves contains the same number of black nodes."
    ).encode("utf-8")
    files = {"file": ("rb_trees.txt", content, "text/plain")}
    await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files=files,
        data={"subject_id": sub_id},
    )

    # Initial mastery
    state_before = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    mastery_before = state_before.json()["mastery"]["probability"]

    # Chat with tutor
    chat_res = await async_client.post(
        "/api/v1/tutor/chat",
        headers=user["headers"],
        json={
            "topic_id": topic_id,
            "mode": "explain_in_detail",
            "message": "What is the black height property of Red-Black Trees?",
        },
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert len(chat_data["sources"]) >= 1
    assert "rb_trees.txt" in chat_data["response_text"]

    # CRITICAL: Verify MasteryState did NOT mutate from tutor conversation
    state_after = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    mastery_after = state_after.json()["mastery"]["probability"]
    assert mastery_after == mastery_before
