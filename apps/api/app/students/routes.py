import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.students.schemas import (
    StudentProfileUpdate,
    StudentProfileResponse,
    AvailabilityBatchUpdate,
    AvailabilityWindowResponse,
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    StudentStateResponse,
    ProgressOverviewResponse,
    StudentSuggestionsResponse,
    StudentHomeResponse,
)
from app.students.service import (
    get_or_create_profile,
    update_profile,
    get_availability_windows,
    set_availability_windows,
    create_goal,
    list_goals,
    update_goal,
    delete_goal,
    get_assembled_student_state,
    get_student_progress_overview,
    get_student_suggestions,
    get_student_home_dashboard,
)

router = APIRouter(prefix="/student", tags=["student"])


@router.get("/profile", response_model=StudentProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfileResponse:
    profile = await get_or_create_profile(db, current_user.id)
    return StudentProfileResponse.model_validate(profile)


@router.patch("/profile", response_model=StudentProfileResponse)
async def patch_profile(
    req: StudentProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfileResponse:
    profile = await update_profile(db, current_user.id, req)
    return StudentProfileResponse.model_validate(profile)


@router.get("/state", response_model=StudentStateResponse)
async def get_student_state(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentStateResponse:
    """Returns authoritative read-only student state."""
    return await get_assembled_student_state(db, current_user.id)


@router.get("/availability", response_model=List[AvailabilityWindowResponse])
async def get_availability(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AvailabilityWindowResponse]:
    windows = await get_availability_windows(db, current_user.id)
    return [AvailabilityWindowResponse.model_validate(w) for w in windows]


@router.put("/availability", response_model=List[AvailabilityWindowResponse])
async def update_availability(
    req: AvailabilityBatchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AvailabilityWindowResponse]:
    windows = await set_availability_windows(db, current_user.id, req.windows)
    return [AvailabilityWindowResponse.model_validate(w) for w in windows]


@router.get("/goals", response_model=List[GoalResponse])
async def get_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[GoalResponse]:
    goals = await list_goals(db, current_user.id)
    return [GoalResponse.model_validate(g) for g in goals]


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def post_goal(
    req: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    goal = await create_goal(db, current_user.id, req)
    return GoalResponse.model_validate(goal)


@router.patch("/goals/{goal_id}", response_model=GoalResponse)
async def patch_goal(
    goal_id: uuid.UUID,
    req: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    goal = await update_goal(db, current_user.id, goal_id, req)
    return GoalResponse.model_validate(goal)


@router.delete("/goals/{goal_id}")
async def remove_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    await delete_goal(db, current_user.id, goal_id)
    return {"status": "success", "message": "Goal deleted"}


@router.get("/home", response_model=StudentHomeResponse)
async def get_home(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentHomeResponse:
    """Returns student cockpit home dashboard: top task, next task, today's progress, and summary."""
    return await get_student_home_dashboard(db, current_user.id)


@router.get("/progress-overview", response_model=ProgressOverviewResponse)
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressOverviewResponse:
    """Returns aggregated mastery levels (Strong, Developing, Needs Attention, Review Due)."""
    return await get_student_progress_overview(db, current_user.id)


@router.get("/suggestions", response_model=StudentSuggestionsResponse)
async def get_suggestions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentSuggestionsResponse:
    """Returns explainable recommendations explaining 'Why this?' for upcoming exams and decaying memory."""
    return await get_student_suggestions(db, current_user.id)

