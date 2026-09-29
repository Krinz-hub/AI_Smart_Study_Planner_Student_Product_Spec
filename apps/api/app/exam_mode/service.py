import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academics.models import Exam, Subject, Topic
from app.tasks.models import StudyTask
from app.learner.models import MasteryState, LearnerEvent
from app.exam_mode.models import ExamPlan
from app.exam_mode.schemas import (
    ExamModeGenerateRequest,
    ExamPlanResponse,
    ExamRescueAction,
    ExamPlanActionRequest,
)
from app.common.errors import NotFoundException, InvalidRequestException
from app.common.logging import get_logger

logger = get_logger("exam_mode_service")


async def generate_exam_mode_plan(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: ExamModeGenerateRequest,
) -> ExamPlanResponse:
    now_utc = datetime.now(timezone.utc)

    # 1. Fetch Exam
    exam_stmt = select(Exam).where(Exam.id == req.exam_id, Exam.user_id == user_id)
    exam_res = await db.execute(exam_stmt)
    exam = exam_res.scalar_one_or_none()
    if not exam:
        raise NotFoundException("Exam not found")

    if exam.exam_at <= now_utc:
        raise InvalidRequestException("Cannot generate exam plan for past exam date")

    # 2. Fetch Syllabus Topics
    topics_stmt = select(Topic).where(Topic.subject_id == exam.subject_id).order_by(Topic.created_at)
    topics_res = await db.execute(topics_stmt)
    topics = list(topics_res.scalars().all())

    if not topics:
        raise InvalidRequestException("Subject has no topics defined for syllabus coverage")

    days_remaining = max(1, (exam.exam_at.date() - now_utc.date()).days)

    # 3. Rescue Procedure: Backlog Analysis and Workload Pruning
    rescue_actions: List[ExamRescueAction] = []
    # Check backlog of pending/overdue tasks across other subjects
    backlog_stmt = select(StudyTask).where(
        StudyTask.user_id == user_id,
        StudyTask.status == "PENDING",
        StudyTask.planned_start < now_utc,
    )
    backlog_res = await db.execute(backlog_stmt)
    backlog_tasks = list(backlog_res.scalars().all())

    for bt in backlog_tasks:
        if bt.subject_id != exam.subject_id:
            rescue_actions.append(
                ExamRescueAction(
                    action_type="DEFER_NON_EXAM",
                    topic_name=bt.title,
                    reason="Deferred to prioritize immediate upcoming exam syllabus.",
                )
            )
        else:
            rescue_actions.append(
                ExamRescueAction(
                    action_type="PRESERVE_CRITICAL",
                    topic_name=bt.title,
                    reason="Preserved in high-yield exam recovery schedule.",
                )
            )

    # 4. Fetch Mastery to prioritize weaker topics
    mastery_stmt = select(MasteryState).where(
        MasteryState.user_id == user_id,
        MasteryState.topic_id.in_([t.id for t in topics]),
    )
    mastery_res = await db.execute(mastery_stmt)
    masteries = {m.topic_id: float(m.mastery_probability) for m in mastery_res.scalars().all()}

    # Sort topics: lowest mastery first
    sorted_topics = sorted(topics, key=lambda t: masteries.get(t.id, 0.1))

    # 5. Build Syllabus Coverage Plan with Workload Ceiling
    ceiling = req.workload_ceiling_minutes
    daily_allocated = min(ceiling, max(120, int(len(topics) * 45 / max(1, days_remaining))))

    generated_tasks: List[Dict[str, Any]] = []
    covered_topic_ids = set()

    for day_offset in range(days_remaining):
        day_date = now_utc.date() + timedelta(days=day_offset)
        is_final_48h = (exam.exam_at.date() - day_date).days <= 2

        # Up to 4 slots per day (45 min each)
        slots_for_day = min(daily_allocated // 45, len(sorted_topics))
        for slot_idx in range(slots_for_day):
            t_idx = (day_offset * 3 + slot_idx) % len(sorted_topics)
            topic = sorted_topics[t_idx]
            covered_topic_ids.add(topic.id)

            task_type = (
                "FINAL_REVISION"
                if is_final_48h
                else ("PRACTICE" if masteries.get(topic.id, 0.1) < 0.6 else "REVISE")
            )
            slot_start = datetime.combine(day_date, datetime.min.time()).replace(
                hour=14 + slot_idx, tzinfo=timezone.utc
            )
            slot_end = slot_start + timedelta(minutes=45)

            generated_tasks.append(
                {
                    "topic_id": str(topic.id),
                    "topic_name": topic.name,
                    "subject_id": str(exam.subject_id),
                    "task_type": task_type,
                    "title": f"Exam Prep: {task_type} - {topic.name}",
                    "planned_start": slot_start.isoformat(),
                    "planned_end": slot_end.isoformat(),
                    "duration_minutes": 45,
                }
            )

    coverage_pct = round(len(covered_topic_ids) / len(topics) * 100.0, 2)

    exam_plan = ExamPlan(
        user_id=user_id,
        exam_id=exam.id,
        subject_id=exam.subject_id,
        status="PROPOSED",
        total_topics_covered=len(covered_topic_ids),
        syllabus_coverage_pct=Decimal(str(coverage_pct)),
        target_exam_date=exam.exam_at,
        daily_workload_minutes=daily_allocated,
        workload_ceiling_minutes=ceiling,
        rescue_actions=[a.model_dump() for a in rescue_actions],
        tasks_snapshot=generated_tasks,
    )
    db.add(exam_plan)
    await db.commit()
    await db.refresh(exam_plan)

    # Emit EXAM_PLAN_GENERATED event
    event = LearnerEvent(
        user_id=user_id,
        event_type="EXAM_PLAN_GENERATED",
        entity_type="exam_plan",
        entity_id=exam_plan.id,
        evidence_category="BEHAVIOR",
        payload={
            "exam_id": str(exam.id),
            "coverage_pct": coverage_pct,
            "days_remaining": days_remaining,
            "tasks_count": len(generated_tasks),
        },
    )
    db.add(event)
    await db.commit()

    return ExamPlanResponse(
        id=exam_plan.id,
        exam_id=exam_plan.exam_id,
        subject_id=exam_plan.subject_id,
        status=exam_plan.status,
        total_topics_covered=exam_plan.total_topics_covered,
        syllabus_coverage_pct=float(exam_plan.syllabus_coverage_pct),
        target_exam_date=exam_plan.target_exam_date,
        daily_workload_minutes=exam_plan.daily_workload_minutes,
        workload_ceiling_minutes=exam_plan.workload_ceiling_minutes,
        rescue_actions=rescue_actions,
        tasks=generated_tasks,
        created_at=exam_plan.created_at,
    )


async def get_exam_plan_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
) -> ExamPlanResponse:
    stmt = select(ExamPlan).where(ExamPlan.id == plan_id, ExamPlan.user_id == user_id)
    res = await db.execute(stmt)
    plan = res.scalar_one_or_none()
    if not plan:
        raise NotFoundException("Exam plan not found")

    actions = [ExamRescueAction(**a) for a in plan.rescue_actions]
    return ExamPlanResponse(
        id=plan.id,
        exam_id=plan.exam_id,
        subject_id=plan.subject_id,
        status=plan.status,
        total_topics_covered=plan.total_topics_covered,
        syllabus_coverage_pct=float(plan.syllabus_coverage_pct),
        target_exam_date=plan.target_exam_date,
        daily_workload_minutes=plan.daily_workload_minutes,
        workload_ceiling_minutes=plan.workload_ceiling_minutes,
        rescue_actions=actions,
        tasks=plan.tasks_snapshot,
        created_at=plan.created_at,
    )


async def handle_exam_plan_action(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    req: ExamPlanActionRequest,
) -> ExamPlanResponse:
    stmt = select(ExamPlan).where(ExamPlan.id == plan_id, ExamPlan.user_id == user_id)
    res = await db.execute(stmt)
    plan = res.scalar_one_or_none()
    if not plan:
        raise NotFoundException("Exam plan not found")

    action = req.action.upper()
    if action == "ACCEPT":
        plan.status = "ACCEPTED"
        # Persist generated tasks into real study_tasks with locked=True
        for t in plan.tasks_snapshot:
            new_task = StudyTask(
                user_id=user_id,
                subject_id=uuid.UUID(t["subject_id"]),
                topic_id=uuid.UUID(t["topic_id"]),
                title=t["title"],
                objective=f"Intensive exam preparation for {t['topic_name']}",
                task_type=t["task_type"],
                planned_start=datetime.fromisoformat(t["planned_start"]),
                planned_end=datetime.fromisoformat(t["planned_end"]),
                duration_minutes=t["duration_minutes"],
                priority=Decimal("0.950"),
                priority_version="exam-mode-v1",
                reason={"exam_plan_id": str(plan.id), "rescue": True},
                status="PENDING",
                locked=True,  # Locked to preserve exam schedule
                plan_version=f"exam-{str(plan.id)[:18]}",
            )
            db.add(new_task)

    elif action == "CUSTOMIZE":
        plan.status = "CUSTOMIZED"
        if req.custom_daily_workload_minutes:
            plan.daily_workload_minutes = req.custom_daily_workload_minutes

    elif action == "DISMISS":
        plan.status = "DISMISSED"

    await db.commit()
    await db.refresh(plan)

    actions = [ExamRescueAction(**a) for a in plan.rescue_actions]
    return ExamPlanResponse(
        id=plan.id,
        exam_id=plan.exam_id,
        subject_id=plan.subject_id,
        status=plan.status,
        total_topics_covered=plan.total_topics_covered,
        syllabus_coverage_pct=float(plan.syllabus_coverage_pct),
        target_exam_date=plan.target_exam_date,
        daily_workload_minutes=plan.daily_workload_minutes,
        workload_ceiling_minutes=plan.workload_ceiling_minutes,
        rescue_actions=actions,
        tasks=plan.tasks_snapshot,
        created_at=plan.created_at,
    )
