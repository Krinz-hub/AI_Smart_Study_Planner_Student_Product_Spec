import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.students.models import AvailabilityWindow
from app.academics.models import Exam
from app.tasks.models import StudyTask, StudySession
from app.learner.models import LearnerEvent
from app.learner.intelligence_service import process_knowledge_observation
from app.decisions.service import generate_recommendations
from app.planner.ortools_scheduler import (
    ORToolsPlanner,
    PlannerCandidate,
    ScheduledSlot,
    TimeSlot,
)
from app.planner.schemas import (
    PlanGenerateRequest,
    PlanResponse,
    StudyTaskResponse,
    TaskCompleteRequest,
    TaskCompletionResult,
    TaskSkipRequest,
    PlanReplanRequest,
)
from app.common.errors import NotFoundException, ForbiddenException, InvalidRequestException
from app.common.logging import get_logger

logger = get_logger("planner_service")


async def generate_study_plan(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: PlanGenerateRequest,
) -> PlanResponse:
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()

    start_date = req.start_date or today
    end_date = req.end_date or (start_date + timedelta(days=7))

    if end_date < start_date:
        raise InvalidRequestException("end_date must be on or after start_date")

    planning_start = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
    planning_end = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)

    # 1. Fetch user's availability windows
    avail_stmt = select(AvailabilityWindow).where(
        AvailabilityWindow.user_id == user_id,
        AvailabilityWindow.enabled.is_(True),
    )
    avail_res = await db.execute(avail_stmt)
    avail_windows = list(avail_res.scalars().all())

    # Fallback default windows if none created yet (Mon-Sun 16:00 to 20:00)
    if not avail_windows:
        avail_windows = [
            AvailabilityWindow(
                user_id=user_id,
                weekday=w,
                start_time=time(16, 0),
                end_time=time(20, 0),
                enabled=True,
            )
            for w in range(7)
        ]

    # Map recurring weekday windows to actual date intervals
    concrete_slots: List[TimeSlot] = []
    curr_date = start_date
    while curr_date <= end_date:
        curr_weekday = curr_date.weekday()
        for win in avail_windows:
            if win.weekday == curr_weekday:
                s_dt = datetime.combine(curr_date, win.start_time).replace(tzinfo=timezone.utc)
                e_dt = datetime.combine(curr_date, win.end_time).replace(tzinfo=timezone.utc)
                if e_dt > now_utc:
                    start_clamped = max(now_utc, s_dt)
                    dur = int((e_dt - start_clamped).total_seconds() / 60)
                    if dur >= 30:
                        concrete_slots.append(
                            TimeSlot(start=start_clamped, end=e_dt, duration_minutes=dur)
                        )
        curr_date += timedelta(days=1)

    # 2. Fetch existing locked tasks in this horizon
    locked_stmt = select(StudyTask).where(
        StudyTask.user_id == user_id,
        StudyTask.locked.is_(True),
        StudyTask.planned_start >= planning_start,
        StudyTask.planned_start <= planning_end,
    )
    locked_res = await db.execute(locked_stmt)
    existing_locked_db = list(locked_res.scalars().all())

    locked_slots = [
        ScheduledSlot(
            candidate_id=str(lt.id),
            topic_id=lt.topic_id,
            topic_name=lt.title,
            subject_id=lt.subject_id,
            action=lt.task_type,
            start_time=lt.planned_start,
            end_time=lt.planned_end,
            duration_minutes=lt.duration_minutes,
            priority=float(lt.priority),
            reasons=lt.reason.get("factors", []),
            locked=True,
        )
        for lt in existing_locked_db
    ]

    # 3. Fetch candidate recommendations from Decision Engine
    decisions_res = await generate_recommendations(db, user_id, limit=25)
    candidates = []

    # Fetch subject exams for deadlines
    exam_stmt = select(Exam).where(Exam.user_id == user_id)
    exam_res = await db.execute(exam_stmt)
    exams_map = {e.subject_id: e.exam_at for e in exam_res.scalars().all()}

    for rec in decisions_res.recommendations:
        if rec.action in ("REST", "NO_ACTION") or not rec.topic_id:
            continue

        deadline = exams_map.get(rec.subject_id)
        candidates.append(
            PlannerCandidate(
                candidate_id=str(rec.topic_id),
                topic_id=rec.topic_id,
                topic_name=rec.topic_name or "Topic Study",
                subject_id=rec.subject_id,
                action=rec.action,
                priority=rec.priority,
                duration_minutes=45,
                reasons=rec.reason,
                exam_deadline=deadline,
            )
        )

    # 4. Run OR-Tools Scheduler
    scheduler = ORToolsPlanner(
        daily_max_minutes=req.daily_capacity_minutes,
        session_duration_minutes=45,
        min_break_minutes=15,
    )
    scheduled_slots = scheduler.schedule(
        planning_start=planning_start,
        planning_end=planning_end,
        availability_slots=concrete_slots,
        candidates=candidates,
        locked_tasks=locked_slots,
    )

    # 5. Persist tasks to database
    # Clear unlocked future pending tasks in this window to avoid duplication
    del_stmt = delete(StudyTask).where(
        StudyTask.user_id == user_id,
        StudyTask.locked.is_(False),
        StudyTask.status == "PENDING",
        StudyTask.planned_start >= planning_start,
        StudyTask.planned_start <= planning_end,
    )
    await db.execute(del_stmt)

    plan_version = f"plan-{int(now_utc.timestamp())}"
    saved_tasks: List[StudyTask] = []

    for slot in scheduled_slots:
        if slot.locked:
            # Already saved in DB
            lt_task = next((lt for lt in existing_locked_db if lt.id == uuid.UUID(slot.candidate_id)), None)
            if lt_task:
                saved_tasks.append(lt_task)
            continue

        new_task = StudyTask(
            user_id=user_id,
            subject_id=slot.subject_id,
            topic_id=slot.topic_id,
            title=f"{slot.action.replace('_', ' ').title()}: {slot.topic_name}",
            objective=f"Review and practice key objectives for {slot.topic_name}.",
            task_type=slot.action,
            planned_start=slot.start_time,
            planned_end=slot.end_time,
            duration_minutes=slot.duration_minutes,
            priority=Decimal(str(slot.priority)),
            priority_version="priority-v1",
            reason={"factors": slot.reasons},
            status="PENDING",
            locked=False,
            plan_version=plan_version,
        )
        db.add(new_task)
        saved_tasks.append(new_task)

    await db.commit()
    for t in saved_tasks:
        await db.refresh(t)

    # Emit PLAN_GENERATED event
    event = LearnerEvent(
        user_id=user_id,
        event_type="PLAN_GENERATED",
        entity_type="plan",
        evidence_category="BEHAVIOR",
        payload={
            "plan_version": plan_version,
            "total_tasks": len(saved_tasks),
            "start_date": str(start_date),
            "end_date": str(end_date),
        },
    )
    db.add(event)
    await db.commit()

    total_mins = sum(t.duration_minutes for t in saved_tasks)
    return PlanResponse(
        plan_id=str(uuid.uuid4()),
        plan_version=plan_version,
        start_date=start_date,
        end_date=end_date,
        total_tasks=len(saved_tasks),
        total_minutes=total_mins,
        tasks=[StudyTaskResponse.model_validate(t) for t in saved_tasks],
    )


async def set_task_lock(
    db: AsyncSession,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    locked: bool,
) -> StudyTask:
    stmt = select(StudyTask).where(StudyTask.id == task_id, StudyTask.user_id == user_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException("Task not found")

    task.locked = locked
    await db.commit()
    await db.refresh(task)
    return task


async def reschedule_task(
    db: AsyncSession,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    new_start: datetime,
) -> StudyTask:
    stmt = select(StudyTask).where(StudyTask.id == task_id, StudyTask.user_id == user_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException("Task not found")

    new_end = new_start + timedelta(minutes=task.duration_minutes)
    task.planned_start = new_start
    task.planned_end = new_end
    await db.commit()
    await db.refresh(task)
    return task


async def complete_task(
    db: AsyncSession,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    req: TaskCompleteRequest,
) -> TaskCompletionResult:
    stmt = select(StudyTask).where(StudyTask.id == task_id, StudyTask.user_id == user_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    if not task:
        raise NotFoundException("Task not found")

    now_utc = datetime.now(timezone.utc)
    task.status = "COMPLETED"

    actual_dur = req.actual_minutes or task.duration_minutes
    # Check for active in-progress session
    sess_stmt = (
        select(StudySession)
        .where(
            StudySession.task_id == task.id,
            StudySession.user_id == user_id,
            StudySession.completion_status == "IN_PROGRESS",
        )
        .order_by(StudySession.started_at.desc())
    )
    sess_res = await db.execute(sess_stmt)
    active_session = sess_res.scalar_one_or_none()
    if active_session:
        active_session.ended_at = now_utc
        active_session.actual_minutes = actual_dur
        active_session.completion_status = "COMPLETED"
        if req.self_rating is not None:
            active_session.self_rating = Decimal(str(req.self_rating))
    else:
        session = StudySession(
            user_id=user_id,
            task_id=task.id,
            started_at=now_utc - timedelta(minutes=actual_dur),
            ended_at=now_utc,
            actual_minutes=actual_dur,
            completion_status="COMPLETED",
            self_rating=Decimal(str(req.self_rating)) if req.self_rating is not None else None,
        )
        db.add(session)


    mastery_prob = None
    mastery_state_label = None
    retrievability_val = None

    # Knowledge evaluation: only when an assessment score or is_correct indicator is provided
    if req.score is not None or req.is_correct is not None:
        is_correct = req.is_correct if req.is_correct is not None else (req.score >= 0.7)
        mastery, memory = await process_knowledge_observation(
            db,
            user_id=user_id,
            topic_id=task.topic_id,
            is_correct=is_correct,
            response_time_seconds=int(actual_dur * 60),
        )
        mastery_prob = float(mastery.mastery_probability)
        mastery_state_label = mastery.state
        retrievability_val = float(memory.retrievability)
    else:
        # Anti-feedback rule: completion without formal assessment is purely a behavioral observation
        event = LearnerEvent(
            user_id=user_id,
            event_type="TASK_COMPLETED",
            entity_type="task",
            entity_id=task.id,
            evidence_category="BEHAVIOR",
            payload={
                "task_id": str(task.id),
                "topic_id": str(task.topic_id),
                "duration_minutes": actual_dur,
                "notes": req.notes,
            },
        )
        db.add(event)

    await db.commit()
    await db.refresh(task)

    return TaskCompletionResult(
        task=StudyTaskResponse.model_validate(task),
        bkt_mastery_probability=mastery_prob,
        bkt_state=mastery_state_label,
        fsrs_retrievability=retrievability_val,
        replanned=False,
    )


async def skip_task(
    db: AsyncSession,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    req: TaskSkipRequest,
) -> StudyTask:
    stmt = select(StudyTask).where(StudyTask.id == task_id, StudyTask.user_id == user_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    if not task:
        raise NotFoundException("Task not found")

    task.status = "SKIPPED"

    # CRITICAL ANTI-FEEDBACK ENFORCEMENT:
    # Skipped task produces ONLY a BEHAVIOR event and NEVER degrades BKT or FSRS mastery state!
    event = LearnerEvent(
        user_id=user_id,
        event_type="TASK_SKIPPED",
        entity_type="task",
        entity_id=task.id,
        evidence_category="BEHAVIOR",
        payload={
            "task_id": str(task.id),
            "topic_id": str(task.topic_id),
            "reason": req.reason,
        },
    )
    db.add(event)
    await db.commit()
    await db.refresh(task)
    return task


async def replan_study_plan(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan_id: str,
    req: PlanReplanRequest,
) -> PlanResponse:
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()

    start_date = req.start_date or today
    end_date = req.end_date or (start_date + timedelta(days=7))

    if end_date < start_date:
        raise InvalidRequestException("end_date must be on or after start_date")

    planning_start = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
    planning_end = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)

    # 1. Fetch user's availability windows
    avail_stmt = select(AvailabilityWindow).where(
        AvailabilityWindow.user_id == user_id,
        AvailabilityWindow.enabled.is_(True),
    )
    avail_res = await db.execute(avail_stmt)
    avail_windows = list(avail_res.scalars().all())
    if not avail_windows:
        avail_windows = [
            AvailabilityWindow(
                user_id=user_id,
                weekday=w,
                start_time=time(16, 0),
                end_time=time(20, 0),
                enabled=True,
            )
            for w in range(7)
        ]

    concrete_slots: List[TimeSlot] = []
    curr_date = start_date
    while curr_date <= end_date:
        curr_weekday = curr_date.weekday()
        for win in avail_windows:
            if win.weekday == curr_weekday:
                s_dt = datetime.combine(curr_date, win.start_time).replace(tzinfo=timezone.utc)
                e_dt = datetime.combine(curr_date, win.end_time).replace(tzinfo=timezone.utc)
                if e_dt > now_utc:
                    start_clamped = max(now_utc, s_dt)
                    dur = int((e_dt - start_clamped).total_seconds() / 60)
                    if dur >= 30:
                        concrete_slots.append(
                            TimeSlot(start=start_clamped, end=e_dt, duration_minutes=dur)
                        )
        curr_date += timedelta(days=1)

    # 2. Schedule Stability: Preserve locked tasks and already completed/skipped tasks
    preserved_stmt = select(StudyTask).where(
        StudyTask.user_id == user_id,
        (StudyTask.locked.is_(True) | (StudyTask.status.in_(["COMPLETED", "SKIPPED"]))),
        StudyTask.planned_start >= planning_start,
        StudyTask.planned_start <= planning_end,
    )
    preserved_res = await db.execute(preserved_stmt)
    existing_preserved_db = list(preserved_res.scalars().all())

    locked_slots = [
        ScheduledSlot(
            candidate_id=str(pt.id),
            topic_id=pt.topic_id,
            topic_name=pt.title,
            subject_id=pt.subject_id,
            action=pt.task_type,
            start_time=pt.planned_start,
            end_time=pt.planned_end,
            duration_minutes=pt.duration_minutes,
            priority=float(pt.priority),
            reasons=pt.reason.get("factors", []),
            locked=True,
        )
        for pt in existing_preserved_db
    ]

    # 3. Decision Engine recommendations reflecting updated knowledge/evidence
    decisions_res = await generate_recommendations(db, user_id, limit=25)

    exam_stmt = select(Exam).where(Exam.user_id == user_id)
    exam_res = await db.execute(exam_stmt)
    exams_map = {e.subject_id: e.exam_at for e in exam_res.scalars().all()}

    candidates = []
    for rec in decisions_res.recommendations:
        if rec.action in ("REST", "NO_ACTION") or not rec.topic_id:
            continue
        deadline = exams_map.get(rec.subject_id)
        candidates.append(
            PlannerCandidate(
                candidate_id=str(rec.topic_id),
                topic_id=rec.topic_id,
                topic_name=rec.topic_name or "Topic Study",
                subject_id=rec.subject_id,
                action=rec.action,
                priority=rec.priority,
                duration_minutes=45,
                reasons=rec.reason,
                exam_deadline=deadline,
            )
        )

    # 4. OR-Tools scheduling with soft oscillation penalty
    scheduler = ORToolsPlanner(
        daily_max_minutes=req.daily_capacity_minutes,
        session_duration_minutes=45,
        min_break_minutes=15,
    )
    scheduled_slots = scheduler.schedule(
        planning_start=planning_start,
        planning_end=planning_end,
        availability_slots=concrete_slots,
        candidates=candidates,
        locked_tasks=locked_slots,
    )

    # 5. Clear only unlocked PENDING tasks in the window
    del_stmt = delete(StudyTask).where(
        StudyTask.user_id == user_id,
        StudyTask.locked.is_(False),
        StudyTask.status == "PENDING",
        StudyTask.planned_start >= planning_start,
        StudyTask.planned_start <= planning_end,
    )
    await db.execute(del_stmt)

    new_plan_version = f"replan-{int(now_utc.timestamp())}"
    saved_tasks: List[StudyTask] = []

    for slot in scheduled_slots:
        if slot.locked:
            p_task = next((pt for pt in existing_preserved_db if pt.id == uuid.UUID(slot.candidate_id)), None)
            if p_task:
                saved_tasks.append(p_task)
            continue

        new_task = StudyTask(
            user_id=user_id,
            subject_id=slot.subject_id,
            topic_id=slot.topic_id,
            title=f"{slot.action.replace('_', ' ').title()}: {slot.topic_name}",
            objective=f"Review and practice key objectives for {slot.topic_name}.",
            task_type=slot.action,
            planned_start=slot.start_time,
            planned_end=slot.end_time,
            duration_minutes=slot.duration_minutes,
            priority=Decimal(str(slot.priority)),
            priority_version="priority-v1",
            reason={"factors": slot.reasons, "replan_reason": req.reason},
            status="PENDING",
            locked=False,
            plan_version=new_plan_version,
        )
        db.add(new_task)
        saved_tasks.append(new_task)

    await db.commit()
    for t in saved_tasks:
        await db.refresh(t)

    # Record audit & replan event
    event = LearnerEvent(
        user_id=user_id,
        event_type="PLAN_REPLANNED",
        entity_type="plan",
        evidence_category="BEHAVIOR",
        payload={
            "plan_version": new_plan_version,
            "replan_reason": req.reason,
            "context": req.context or {},
            "total_tasks": len(saved_tasks),
        },
    )
    db.add(event)
    await db.commit()

    total_mins = sum(t.duration_minutes for t in saved_tasks)
    return PlanResponse(
        plan_id=str(uuid.uuid4()),
        plan_version=new_plan_version,
        start_date=start_date,
        end_date=end_date,
        total_tasks=len(saved_tasks),
        total_minutes=total_mins,
        tasks=[StudyTaskResponse.model_validate(t) for t in saved_tasks],
    )


async def start_task(
    db: AsyncSession,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
) -> StudyTask:
    stmt = select(StudyTask).where(StudyTask.id == task_id, StudyTask.user_id == user_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    if not task:
        raise NotFoundException("Task not found")

    now_utc = datetime.now(timezone.utc)
    task.status = "IN_PROGRESS"

    session = StudySession(
        user_id=user_id,
        task_id=task.id,
        started_at=now_utc,
        ended_at=None,
        actual_minutes=0,
        completion_status="IN_PROGRESS",
    )
    db.add(session)

    event = LearnerEvent(
        user_id=user_id,
        event_type="TASK_STARTED",
        entity_type="task",
        entity_id=task.id,
        evidence_category="BEHAVIOR",
        payload={
            "task_id": str(task.id),
            "topic_id": str(task.topic_id),
            "title": task.title,
        },
    )
    db.add(event)
    await db.commit()
    await db.refresh(task)
    return task


async def list_study_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
) -> List[StudySession]:
    stmt = (
        select(StudySession)
        .where(StudySession.user_id == user_id)
        .order_by(StudySession.started_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())

