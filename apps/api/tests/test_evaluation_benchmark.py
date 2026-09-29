import uuid
from datetime import datetime, timezone, timedelta, date
import pytest
from httpx import AsyncClient

from tests.test_student_state import create_authenticated_user
from app.evaluation.synthetic_students import SyntheticStudentFactory
from app.evaluation.metrics import (
    calculate_normalized_gain,
    calculate_calibration_error,
    verify_hard_constraints,
)
from app.learner.calibration import evaluate_confidence_calibration


@pytest.mark.asyncio
async def test_synthetic_student_learning_outcome_trajectory(async_client: AsyncClient):
    """
    CRITICAL LEARNING OUTCOME EVALUATION:
    Simulates Pre-test -> Study Intervention -> Post-test.
    Demonstrates empirical mastery convergence and positive normalized learning gain.
    """
    user = await create_authenticated_user(async_client, "synth_eval_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Linear Algebra", "code": "MATH101"},
    )
    sub_id = sub.json()["id"]

    topic = await async_client.post(
        f"/api/v1/subjects/{sub_id}/topics",
        headers=user["headers"],
        json={"name": "Matrix Decomposition"},
    )
    topic_id = topic.json()["id"]

    # 1. Pre-test: Weak initial performance (score: 0.25)
    pre_score = 0.25
    await async_client.post(
        f"/api/v1/learner/topics/{topic_id}/observation",
        headers=user["headers"],
        json={"is_correct": False, "response_time_seconds": 40},
    )
    state_pre = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    mastery_pre = state_pre.json()["mastery"]["probability"]

    # 2. Study Intervention: 3 deliberate successful practice repetitions
    for _ in range(3):
        await async_client.post(
            f"/api/v1/learner/topics/{topic_id}/observation",
            headers=user["headers"],
            json={"is_correct": True, "response_time_seconds": 25},
        )

    # 3. Post-test: High performance (score: 0.85)
    post_score = 0.85
    state_post = await async_client.get(
        f"/api/v1/learner/topics/{topic_id}",
        headers=user["headers"],
    )
    mastery_post = state_post.json()["mastery"]["probability"]

    # Evaluate Learning Engineering Metrics
    gain = calculate_normalized_gain(pre_score, post_score)
    assert gain > 0.50, f"Expected normalized gain > 0.50, got {gain}"
    assert mastery_post > mastery_pre, "BKT mastery must show positive convergence"


@pytest.mark.asyncio
async def test_synthetic_learner_calibration_error(async_client: AsyncClient):
    """
    CRITICAL EVALUATION:
    Verifies that Overconfident and Underconfident synthetic student personas
    are rigorously detected and measured with calibration error.
    """
    overconfident = SyntheticStudentFactory.get_overconfident_learner()
    underconfident = SyntheticStudentFactory.get_underconfident_learner()

    # 1. Evaluate Overconfident persona: High confidence (0.90) vs Low mastery (0.20)
    over_status, over_desc = evaluate_confidence_calibration(
        self_confidence=overconfident.self_confidence,
        mastery_prob=overconfident.initial_mastery,
        evidence_count=5,
    )
    over_gap = calculate_calibration_error(overconfident.self_confidence, overconfident.initial_mastery)
    assert over_status == "OVERCONFIDENT"
    assert over_gap >= 0.50

    # 2. Evaluate Underconfident persona: Low confidence (0.25) vs High mastery (0.70)
    under_status, under_desc = evaluate_confidence_calibration(
        self_confidence=underconfident.self_confidence,
        mastery_prob=underconfident.initial_mastery,
        evidence_count=5,
    )
    under_gap = calculate_calibration_error(underconfident.self_confidence, underconfident.initial_mastery)
    assert under_status == "UNDERCONFIDENT"
    assert under_gap >= 0.40


@pytest.mark.asyncio
async def test_synthetic_busy_learner_capacity_adherence(async_client: AsyncClient):
    """
    CRITICAL EVALUATION:
    Busy learner has only 60m daily availability.
    Planner must schedule strictly <= 60m with zero hard constraint violations.
    """
    user = await create_authenticated_user(async_client, "busy_eval_user")

    sub = await async_client.post(
        "/api/v1/subjects",
        headers=user["headers"],
        json={"name": "Machine Learning", "code": "CS601"},
    )
    sub_id = sub.json()["id"]

    for name in ["Supervised Learning", "SVM", "Neural Networks"]:
        await async_client.post(
            f"/api/v1/subjects/{sub_id}/topics",
            headers=user["headers"],
            json={"name": name},
        )

    # Set availability windows (60 min daily: 18:00 to 19:00)
    await async_client.put(
        "/api/v1/student/availability",
        headers=user["headers"],
        json={
            "windows": [
                {"weekday": i, "start_time": "18:00:00", "end_time": "19:00:00", "enabled": True}
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
            "end_date": (today + timedelta(days=5)).isoformat(),
            "daily_capacity_minutes": 60,
        },
    )
    assert plan_res.status_code == 201
    tasks = plan_res.json()["tasks"]

    # Evaluate Hard Constraints
    violations = verify_hard_constraints(tasks, daily_max_minutes=60)
    assert len(violations) == 0, f"Expected 0 constraint violations, got: {violations}"
