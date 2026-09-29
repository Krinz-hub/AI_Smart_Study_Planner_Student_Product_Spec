import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academics.models import Subject, Topic, Exam
from app.students.models import Goal
from app.learner.models import MasteryState, MemoryState, LearnerEvent
from app.learner.prerequisites import find_prerequisite_blockers
from app.decisions.schemas import Recommendation, CandidateDecisionsResponse
from app.decisions.priority import compute_topic_priority, DEFAULT_PRIORITY_WEIGHTS
from app.common.logging import get_logger

logger = get_logger("decision_service")


async def generate_recommendations(
    db: AsyncSession,
    user_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = None,
    limit: int = 10,
) -> CandidateDecisionsResponse:
    """
    Ranks academic interventions deterministically per 05_DECISION_AND_PLANNER.md.
    """
    # 1. Fetch relevant subjects
    subj_stmt = select(Subject).where(Subject.user_id == user_id)
    if subject_id:
        subj_stmt = subj_stmt.where(Subject.id == subject_id)
    subj_result = await db.execute(subj_stmt)
    subjects = {s.id: s for s in subj_result.scalars().all()}

    if not subjects:
        # No subjects registered yet -> NO_ACTION
        no_action = Recommendation(
            priority=0.0,
            action="NO_ACTION",
            reason=["No subjects or topics have been enrolled yet. Please create a subject."],
            algorithm_version=DEFAULT_PRIORITY_WEIGHTS.version,
        )
        return CandidateDecisionsResponse(
            recommendations=[no_action],
            top_recommendation=no_action,
            algorithm_version=DEFAULT_PRIORITY_WEIGHTS.version,
        )

    # 2. Fetch topics
    topic_stmt = select(Topic).where(Topic.subject_id.in_(list(subjects.keys())))
    topic_result = await db.execute(topic_stmt)
    topics = list(topic_result.scalars().all())

    if not topics:
        no_action = Recommendation(
            priority=0.0,
            action="NO_ACTION",
            reason=["No topics exist in your enrolled subjects. Please add topics or import syllabus."],
            algorithm_version=DEFAULT_PRIORITY_WEIGHTS.version,
        )
        return CandidateDecisionsResponse(
            recommendations=[no_action],
            top_recommendation=no_action,
            algorithm_version=DEFAULT_PRIORITY_WEIGHTS.version,
        )

    # 3. Fetch upcoming exams for these subjects
    now_utc = datetime.now(timezone.utc)
    exam_stmt = (
        select(Exam)
        .where(Exam.user_id == user_id, Exam.exam_at >= now_utc)
        .order_by(Exam.exam_at)
    )
    exam_result = await db.execute(exam_stmt)
    exams_by_subject = {}
    for ex in exam_result.scalars().all():
        if ex.subject_id not in exams_by_subject:
            exams_by_subject[ex.subject_id] = ex

    # 4. Fetch active goals
    goal_stmt = select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
    goal_result = await db.execute(goal_stmt)
    active_goals = list(goal_result.scalars().all())

    recommendations: List[Recommendation] = []
    all_mastered = True

    for t in topics:
        subj = subjects[t.subject_id]

        # Mastery State
        mst_stmt = select(MasteryState).where(
            MasteryState.user_id == user_id, MasteryState.topic_id == t.id
        )
        mst_res = await db.execute(mst_stmt)
        mst = mst_res.scalar_one_or_none()

        mastery_prob = float(mst.mastery_probability) if mst else 0.10
        mastery_state = mst.state if mst else "UNKNOWN"

        if mastery_prob < 0.85:
            all_mastered = False

        # Memory State
        mem_stmt = select(MemoryState).where(
            MemoryState.user_id == user_id, MemoryState.topic_id == t.id
        )
        mem_res = await db.execute(mem_stmt)
        mem = mem_res.scalar_one_or_none()
        retrievability = float(mem.retrievability) if mem else 1.0

        # Exam Proximity
        subject_exam = exams_by_subject.get(t.subject_id)
        days_to_exam = None
        if subject_exam:
            days_to_exam = (subject_exam.exam_at - now_utc).total_seconds() / 86400.0

        # Prerequisite Blockers
        blockers = await find_prerequisite_blockers(db, user_id, t.id)
        has_blockers = len(blockers) > 0

        # Goal Match
        topic_goals = [
            g for g in active_goals if g.topic_id == t.id or g.subject_id == t.subject_id
        ]
        max_goal_prio = (
            max(float(g.priority) for g in topic_goals) / 2.0 if topic_goals else 0.0
        )

        syllabus_wt = float(t.syllabus_weight) if t.syllabus_weight else 1.0

        # Compute priority
        priority_val, action, reasons = compute_topic_priority(
            mastery_prob=mastery_prob,
            mastery_state=mastery_state,
            retrievability=retrievability,
            exam_days_remaining=days_to_exam,
            has_prereq_blockers=has_blockers,
            goal_importance=max_goal_prio,
            syllabus_weight=syllabus_wt,
        )

        # Collect evidence references
        ev_stmt = (
            select(LearnerEvent.id)
            .where(
                LearnerEvent.user_id == user_id,
                LearnerEvent.payload["topic_id"].as_string() == str(t.id),
            )
            .limit(3)
        )
        ev_res = await db.execute(ev_stmt)
        evidence_ids = list(ev_res.scalars().all())

        rec = Recommendation(
            topic_id=t.id,
            topic_name=t.name,
            subject_id=subj.id,
            subject_name=subj.name,
            priority=priority_val,
            action=action,
            reason=reasons,
            evidence_ids=evidence_ids,
            algorithm_version=DEFAULT_PRIORITY_WEIGHTS.version,
        )
        recommendations.append(rec)

    # Sort descending by priority
    recommendations.sort(key=lambda r: r.priority, reverse=True)

    # Check for NO_ACTION / REST scenario
    if all_mastered and not exams_by_subject and recommendations:
        top_prio = recommendations[0].priority
        if top_prio < 0.25:
            rest_rec = Recommendation(
                priority=0.10,
                action="REST",
                reason=["All topics have reached mastery threshold and no imminent exams exist. Rest or light reading."],
                algorithm_version=DEFAULT_PRIORITY_WEIGHTS.version,
            )
            return CandidateDecisionsResponse(
                recommendations=[rest_rec] + recommendations[:limit],
                top_recommendation=rest_rec,
                algorithm_version=DEFAULT_PRIORITY_WEIGHTS.version,
            )

    top_rec = recommendations[0] if recommendations else None
    return CandidateDecisionsResponse(
        recommendations=recommendations[:limit],
        top_recommendation=top_rec,
        algorithm_version=DEFAULT_PRIORITY_WEIGHTS.version,
    )
