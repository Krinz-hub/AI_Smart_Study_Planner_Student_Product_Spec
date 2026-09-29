import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.mongo import get_mongo_db
from app.students.models import StudentProfile, AvailabilityWindow, Goal
from app.students.schemas import (
    StudentProfileUpdate,
    AvailabilityWindowCreate,
    GoalCreate,
    GoalUpdate,
    StudentStateResponse,
    StudentProfileResponse,
    AvailabilityWindowResponse,
    GoalResponse,
    ProgressOverviewResponse,
    TopicMasteryOverview,
    StudentSuggestionsResponse,
    StudentSuggestion,
    StudentHomeResponse,
    StudentTaskSummary,
)
from app.academics.models import Subject, Topic, Exam
from app.tasks.models import StudyTask
from app.learner.models import MasteryState, MemoryState
from app.common.errors import NotFoundException, ForbiddenException
from app.common.logging import get_logger

logger = get_logger("student_service")


async def get_or_create_profile(db: AsyncSession, user_id: uuid.UUID) -> StudentProfile:
    stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        profile = StudentProfile(user_id=user_id, timezone="UTC")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        logger.info("created_default_student_profile", user_id=str(user_id))

    return profile


async def update_profile(
    db: AsyncSession, user_id: uuid.UUID, update_data: StudentProfileUpdate
) -> StudentProfile:
    profile = await get_or_create_profile(db, user_id)

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    logger.info("updated_student_profile", user_id=str(user_id))
    return profile


async def get_availability_windows(
    db: AsyncSession, user_id: uuid.UUID
) -> List[AvailabilityWindow]:
    stmt = (
        select(AvailabilityWindow)
        .where(AvailabilityWindow.user_id == user_id)
        .order_by(AvailabilityWindow.weekday, AvailabilityWindow.start_time)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def set_availability_windows(
    db: AsyncSession, user_id: uuid.UUID, windows: List[AvailabilityWindowCreate]
) -> List[AvailabilityWindow]:
    # Replace user's availability windows atomically
    del_stmt = delete(AvailabilityWindow).where(AvailabilityWindow.user_id == user_id)
    await db.execute(del_stmt)

    new_windows = [
        AvailabilityWindow(
            user_id=user_id,
            weekday=w.weekday,
            start_time=w.start_time,
            end_time=w.end_time,
            enabled=w.enabled,
        )
        for w in windows
    ]
    db.add_all(new_windows)
    await db.commit()

    return await get_availability_windows(db, user_id)


async def create_goal(db: AsyncSession, user_id: uuid.UUID, goal_in: GoalCreate) -> Goal:
    goal = Goal(
        user_id=user_id,
        subject_id=goal_in.subject_id,
        topic_id=goal_in.topic_id,
        title=goal_in.title,
        target_type=goal_in.target_type,
        target_value=goal_in.target_value,
        deadline=goal_in.deadline,
        priority=goal_in.priority,
        status=goal_in.status,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def list_goals(db: AsyncSession, user_id: uuid.UUID) -> List[Goal]:
    stmt = select(Goal).where(Goal.user_id == user_id).order_by(Goal.priority.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_goal(
    db: AsyncSession, user_id: uuid.UUID, goal_id: uuid.UUID, goal_in: GoalUpdate
) -> Goal:
    stmt = select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    result = await db.execute(stmt)
    goal = result.scalar_one_or_none()
    if not goal:
        raise NotFoundException("Goal not found")

    update_dict = goal_in.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(goal, field, value)

    await db.commit()
    await db.refresh(goal)
    return goal


async def delete_goal(db: AsyncSession, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    stmt = select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    result = await db.execute(stmt)
    goal = result.scalar_one_or_none()
    if not goal:
        raise NotFoundException("Goal not found")

    await db.delete(goal)
    await db.commit()


async def get_assembled_student_state(
    db: AsyncSession, user_id: uuid.UUID
) -> StudentStateResponse:
    """Assembles the complete authoritative read-only student state per 03_API_CONTRACT.md."""
    profile = await get_or_create_profile(db, user_id)
    availability = await get_availability_windows(db, user_id)
    goals = await list_goals(db, user_id)

    # Subjects belonging to user
    subj_stmt = select(Subject).where(Subject.user_id == user_id).order_by(Subject.name)
    subj_result = await db.execute(subj_stmt)
    subjects = list(subj_result.scalars().all())

    # Topics belonging to user's subjects
    subject_ids = [s.id for s in subjects]
    topics = []
    if subject_ids:
        topic_stmt = (
            select(Topic)
            .where(Topic.subject_id.in_(subject_ids))
            .order_by(Topic.name)
        )
        topic_result = await db.execute(topic_stmt)
        topics = list(topic_result.scalars().all())

    # Exams
    exam_stmt = select(Exam).where(Exam.user_id == user_id).order_by(Exam.exam_at)
    exam_result = await db.execute(exam_stmt)
    exams = list(exam_result.scalars().all())

    return StudentStateResponse(
        profile=StudentProfileResponse.model_validate(profile),
        subjects=[
            {"id": s.id, "name": s.name, "code": s.code, "color": s.color}
            for s in subjects
        ],
        topics=[
            {
                "id": t.id,
                "subject_id": t.subject_id,
                "parent_topic_id": t.parent_topic_id,
                "name": t.name,
                "syllabus_weight": float(t.syllabus_weight) if t.syllabus_weight else 1.0,
            }
            for t in topics
        ],
        mastery=[],  # Populated in Phase 5
        memory=[],   # Populated in Phase 5
        goals=[GoalResponse.model_validate(g) for g in goals],
        availability=[AvailabilityWindowResponse.model_validate(w) for w in availability],
        exams=[
            {"id": e.id, "subject_id": e.subject_id, "name": e.name, "exam_at": e.exam_at}
            for e in exams
        ],
    )


async def get_student_progress_overview(
    db: AsyncSession, user_id: uuid.UUID
) -> ProgressOverviewResponse:
    """
    Computes aggregated student mastery breakdown across subjects:
    Strong (>=85%), Developing (40-84%), Needs Attention (<40%), and Review Due (FSRS).
    """
    # 1. Fetch subjects
    subj_stmt = select(Subject).where(Subject.user_id == user_id)
    subj_res = await db.execute(subj_stmt)
    subjects = list(subj_res.scalars().all())
    subj_map = {s.id: s for s in subjects}

    if not subjects:
        return ProgressOverviewResponse(
            overall_mastery_pct=0.0,
            total_subjects=0,
            total_topics=0,
            mastered_topics_count=0,
            strong_topics=[],
            developing_topics=[],
            needs_attention_topics=[],
            review_due_topics=[],
            total_study_minutes_completed=0,
            streak_days=1,
        )

    # 2. Fetch topics
    subject_ids = [s.id for s in subjects]
    top_stmt = select(Topic).where(Topic.subject_id.in_(subject_ids))
    top_res = await db.execute(top_stmt)
    topics = list(top_res.scalars().all())

    # 3. Fetch Mastery & Memory states
    m_stmt = select(MasteryState).where(MasteryState.user_id == user_id)
    m_res = await db.execute(m_stmt)
    mastery_map = {m.topic_id: m for m in m_res.scalars().all()}

    mem_stmt = select(MemoryState).where(MemoryState.user_id == user_id)
    mem_res = await db.execute(mem_stmt)
    memory_map = {mem.topic_id: mem for mem in mem_res.scalars().all()}

    now_utc = datetime.now(timezone.utc)
    strong_topics: List[TopicMasteryOverview] = []
    developing_topics: List[TopicMasteryOverview] = []
    needs_attention_topics: List[TopicMasteryOverview] = []
    review_due_topics: List[TopicMasteryOverview] = []
    total_mastery_sum = 0.0

    for topic in topics:
        sub = subj_map.get(topic.subject_id)
        sub_name = sub.name if sub else "Subject"
        sub_color = sub.color if sub and sub.color else "#3b82f6"

        mstate = mastery_map.get(topic.id)
        m_prob = float(mstate.mastery_probability) if mstate else 0.10
        state_str = mstate.state if mstate else "UNKNOWN"

        memstate = memory_map.get(topic.id)
        retrievability = float(memstate.retrievability) if memstate else 1.0
        next_rev = memstate.next_review_at if memstate else None

        item = TopicMasteryOverview(
            id=topic.id,
            name=topic.name,
            subject_id=topic.subject_id,
            subject_name=sub_name,
            subject_color=sub_color,
            mastery_probability=round(m_prob, 3),
            state=state_str,
            retrievability=round(retrievability, 3),
            next_review_at=next_rev,
        )

        total_mastery_sum += m_prob

        if m_prob >= 0.85:
            strong_topics.append(item)
        elif m_prob >= 0.40:
            developing_topics.append(item)
        else:
            needs_attention_topics.append(item)

        # Check for review due
        if retrievability < 0.80 or (next_rev and next_rev <= now_utc):
            review_due_topics.append(item)

    overall_pct = round((total_mastery_sum / len(topics)) * 100.0, 1) if topics else 0.0

    # 4. Completed study minutes
    comp_stmt = select(func.sum(StudyTask.duration_minutes)).where(
        StudyTask.user_id == user_id,
        StudyTask.status == "COMPLETED",
    )
    comp_res = await db.execute(comp_stmt)
    total_minutes = comp_res.scalar() or 0

    return ProgressOverviewResponse(
        overall_mastery_pct=overall_pct,
        total_subjects=len(subjects),
        total_topics=len(topics),
        mastered_topics_count=len(strong_topics),
        strong_topics=strong_topics,
        developing_topics=developing_topics,
        needs_attention_topics=needs_attention_topics,
        review_due_topics=review_due_topics,
        total_study_minutes_completed=int(total_minutes),
        streak_days=1 if total_minutes > 0 else 0,
    )


async def get_student_suggestions(
    db: AsyncSession, user_id: uuid.UUID
) -> StudentSuggestionsResponse:
    """
    Generates explainable, friendly student suggestions explaining 'Why this?'
    based on upcoming exams, decaying memory stability, and syllabus progression.
    """
    now_utc = datetime.now(timezone.utc)
    suggestions: List[StudentSuggestion] = []

    # 1. Check upcoming exams (within 30 days)
    exam_stmt = (
        select(Exam, Subject)
        .join(Subject, Subject.id == Exam.subject_id)
        .where(
            Exam.user_id == user_id,
            Exam.exam_at >= now_utc,
        )
        .order_by(Exam.exam_at.asc())
        .limit(3)
    )
    exam_res = await db.execute(exam_stmt)
    for exam, subj in exam_res.all():
        days_left = max((exam.exam_at.date() - now_utc.date()).days, 0)
        suggestions.append(
            StudentSuggestion(
                id=f"exam-{exam.id}",
                title=f"Upcoming Exam: {exam.name}",
                subject_name=subj.name,
                action_type="REVIEW",
                priority="HIGH" if days_left <= 7 else "MEDIUM",
                reason=f"Target exam scheduled in {days_left} days. Intensive review and practice quizzes recommended.",
            )
        )

    # 2. Check decaying memory or weak topics
    mem_stmt = (
        select(MemoryState, Topic, Subject)
        .join(Topic, Topic.id == MemoryState.topic_id)
        .join(Subject, Subject.id == Topic.subject_id)
        .where(
            MemoryState.user_id == user_id,
            MemoryState.retrievability < Decimal("0.80"),
        )
        .order_by(MemoryState.retrievability.asc())
        .limit(3)
    )
    mem_res = await db.execute(mem_stmt)
    for mem, topic, subj in mem_res.all():
        ret_pct = int(float(mem.retrievability) * 100)
        suggestions.append(
            StudentSuggestion(
                id=f"decay-{topic.id}",
                title=f"Memory Retention Alert: {topic.name}",
                subject_name=subj.name,
                topic_name=topic.name,
                action_type="PRACTICE",
                priority="HIGH" if ret_pct < 60 else "MEDIUM",
                reason=f"Memory retrievability dropped to {ret_pct}%. A 15-minute active recall session will restore stability.",
            )
        )

    # 3. If few suggestions, recommend exploring available syllabus topics
    if len(suggestions) < 3:
        top_stmt = (
            select(Topic, Subject)
            .join(Subject, Subject.id == Topic.subject_id)
            .where(Subject.user_id == user_id)
            .limit(3)
        )
        top_res = await db.execute(top_stmt)
        for top, subj in top_res.all():
            if not any(s.topic_name == top.name for s in suggestions):
                suggestions.append(
                    StudentSuggestion(
                        id=f"learn-{top.id}",
                        title=f"Deep Dive: {top.name}",
                        subject_name=subj.name,
                        topic_name=top.name,
                        action_type="STUDY",
                        priority="MEDIUM",
                        reason=f"Foundational syllabus topic in {subj.name}. Recommended next learning block.",
                    )
                )
            if len(suggestions) >= 4:
                break

    return StudentSuggestionsResponse(suggestions=suggestions[:5])


async def get_student_home_dashboard(
    db: AsyncSession, user_id: uuid.UUID
) -> StudentHomeResponse:
    """
    Aggregates high-level student cockpit state: top recommended task, next task,
    daily progress bar, and academic summary.
    """
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()

    # Query MongoDB for user profile and onboarding
    mongo_db = get_mongo_db()
    str_id = str(user_id)
    user_doc = await mongo_db.users.find_one({"user_id": str_id})
    student_name = user_doc.get("full_name", "Student") if user_doc else "Student"

    onb_doc = await mongo_db.student_onboarding.find_one({"user_id": str_id})
    onboarding_completed = onb_doc.get("is_completed", False) if onb_doc else False

    pref_doc = await mongo_db.student_preferences.find_one({"user_id": str_id})
    daily_target = pref_doc.get("daily_capacity_minutes", 180) if pref_doc else 180

    # Build academic summary
    academic_summary = "Student Dashboard"
    if onb_doc:
        ac_details = onb_doc.get("academic_details", {})
        if "degree" in ac_details and "university" in ac_details:
            academic_summary = f"{ac_details.get('degree')} - {ac_details.get('university')}"
        elif "board" in ac_details and "grade" in ac_details:
            academic_summary = f"{ac_details.get('grade')} ({ac_details.get('board')})"
        elif "exam_name" in ac_details:
            academic_summary = f"{ac_details.get('exam_name')} Preparation"

    # Query Tasks for student
    task_stmt = (
        select(StudyTask, Subject, Topic)
        .join(Subject, Subject.id == StudyTask.subject_id)
        .outerjoin(Topic, Topic.id == StudyTask.topic_id)
        .where(StudyTask.user_id == user_id)
        .order_by(StudyTask.planned_start.asc(), StudyTask.priority.desc())
    )
    task_res = await db.execute(task_stmt)
    all_tasks = task_res.all()

    # Filter tasks scheduled for today
    today_tasks = [t for t in all_tasks if t[0].planned_start.date() == today]
    if not today_tasks and all_tasks:
        today_tasks = all_tasks[:5]

    tasks_total = len(today_tasks)
    tasks_completed = sum(1 for t in today_tasks if t[0].status == "COMPLETED")
    completed_mins = sum(t[0].duration_minutes for t in today_tasks if t[0].status == "COMPLETED")

    # Find top pending task and next task
    pending_tasks = [t for t in today_tasks if t[0].status != "COMPLETED"]
    top_task_tuple = pending_tasks[0] if pending_tasks else (today_tasks[0] if today_tasks else None)
    next_task_tuple = pending_tasks[1] if len(pending_tasks) > 1 else None

    top_task_summary = None
    top_task_reason = None
    if top_task_tuple:
        st, sub, top = top_task_tuple
        top_task_summary = StudentTaskSummary(
            id=st.id,
            title=st.title,
            subject_name=sub.name if sub else "General",
            topic_name=top.name if top else None,
            duration_minutes=st.duration_minutes,
            task_type=st.task_type,
            status=st.status,
            scheduled_start=st.planned_start,
            scheduled_end=st.planned_end,
        )
        top_task_reason = f"High-priority {st.task_type.lower()} session scheduled to optimize memory stability and syllabus mastery."

    next_task_summary = None
    if next_task_tuple:
        nst, nsub, ntop = next_task_tuple
        next_task_summary = StudentTaskSummary(
            id=nst.id,
            title=nst.title,
            subject_name=nsub.name if nsub else "General",
            topic_name=ntop.name if ntop else None,
            duration_minutes=nst.duration_minutes,
            task_type=nst.task_type,
            status=nst.status,
            scheduled_start=nst.planned_start,
            scheduled_end=nst.planned_end,
        )

    # Quick overview of subjects and overall mastery
    prog = await get_student_progress_overview(db, user_id)

    return StudentHomeResponse(
        student_name=student_name,
        academic_summary=academic_summary,
        onboarding_completed=onboarding_completed,
        top_task=top_task_summary,
        top_task_reason=top_task_reason,
        next_task=next_task_summary,
        today_completed_minutes=completed_mins,
        today_target_minutes=daily_target,
        tasks_completed_today=tasks_completed,
        tasks_total_today=tasks_total,
        subjects_count=prog.total_subjects,
        overall_mastery_pct=prog.overall_mastery_pct,
        streak_days=1 if completed_mins > 0 else 0,
    )

