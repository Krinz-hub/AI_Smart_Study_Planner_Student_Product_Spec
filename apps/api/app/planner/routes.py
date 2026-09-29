import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.planner.schemas import (
    PlanGenerateRequest,
    PlanReplanRequest,
    PlanResponse,
    StudyTaskResponse,
    TaskCompleteRequest,
    TaskCompletionResult,
    TaskLockRequest,
    TaskRescheduleRequest,
    TaskSkipRequest,
    StudySessionResponse,
)
from app.planner.service import (
    complete_task,
    generate_study_plan,
    replan_study_plan,
    reschedule_task,
    set_task_lock,
    skip_task,
    start_task,
    list_study_sessions,
)
from app.tasks.models import StudyTask

router = APIRouter(tags=["planner"])



@router.post("/plans/generate", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def post_generate_plan(
    req: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """Invokes OR-Tools constraint-aware scheduler to generate realistic study plan."""
    return await generate_study_plan(db, current_user.id, req)


@router.get("/tasks", response_model=List[StudyTaskResponse])
async def list_tasks(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[StudyTaskResponse]:
    stmt = select(StudyTask).where(StudyTask.user_id == current_user.id).order_by(StudyTask.planned_start)
    if status_filter:
        stmt = stmt.where(StudyTask.status == status_filter.upper())
    result = await db.execute(stmt)
    tasks = list(result.scalars().all())
    return [StudyTaskResponse.model_validate(t) for t in tasks]


@router.post("/tasks/{task_id}/lock", response_model=StudyTaskResponse)
async def lock_task(
    task_id: uuid.UUID,
    req: TaskLockRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudyTaskResponse:
    task = await set_task_lock(db, current_user.id, task_id, req.locked)
    return StudyTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/reschedule", response_model=StudyTaskResponse)
async def reschedule(
    task_id: uuid.UUID,
    req: TaskRescheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudyTaskResponse:
    task = await reschedule_task(db, current_user.id, task_id, req.new_start)
    return StudyTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/complete", response_model=TaskCompletionResult)
async def post_complete_task(
    task_id: uuid.UUID,
    req: TaskCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskCompletionResult:
    """Marks task completed and updates BKT/FSRS if assessment score is supplied."""
    return await complete_task(db, current_user.id, task_id, req)


@router.post("/tasks/{task_id}/skip", response_model=StudyTaskResponse)
async def post_skip_task(
    task_id: uuid.UUID,
    req: TaskSkipRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudyTaskResponse:
    """Marks task skipped without degrading BKT mastery state (anti-feedback compliance)."""
    task = await skip_task(db, current_user.id, task_id, req)
    return StudyTaskResponse.model_validate(task)


@router.post("/plans/{plan_id}/replan", response_model=PlanResponse)
async def post_replan(
    plan_id: str,
    req: PlanReplanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """Executes constraint-aware replanning respecting schedule stability and capacity limits."""
    return await replan_study_plan(db, current_user.id, plan_id, req)


@router.post("/tasks/{task_id}/start", response_model=StudyTaskResponse)
async def post_start_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudyTaskResponse:
    """Transitions task to IN_PROGRESS and creates an active study session."""
    task = await start_task(db, current_user.id, task_id)
    return StudyTaskResponse.model_validate(task)


@router.get("/study-sessions", response_model=List[StudySessionResponse])
async def get_study_sessions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[StudySessionResponse]:
    """Retrieves chronological study sessions for the authenticated learner."""
    sessions = await list_study_sessions(db, current_user.id, limit=limit)
    return [StudySessionResponse.model_validate(s) for s in sessions]


