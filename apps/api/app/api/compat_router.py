import uuid
from typing import Any, Dict, List, Optional
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
    get_student_progress_overview,
    get_student_suggestions,
    get_student_home_dashboard,
)
from app.onboarding.schemas import (
    DiscoveredSyllabusResponse,
    ConfirmSyllabusRequest,
    ConfirmSyllabusResponse,
)
from app.onboarding.service import (
    trigger_academic_discovery,
    confirm_and_persist_syllabus,
)
from app.exam_mode.schemas import ExamModeGenerateRequest, ExamPlanResponse
from app.exam_mode.service import generate_exam_mode_plan

compat_router = APIRouter(tags=["spec-aliases"])


# /profile alias
@compat_router.get("/profile", response_model=StudentProfileResponse)
async def get_profile_alias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfileResponse:
    profile = await get_or_create_profile(db, current_user.id)
    return StudentProfileResponse.model_validate(profile)


@compat_router.patch("/profile", response_model=StudentProfileResponse)
async def patch_profile_alias(
    req: StudentProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfileResponse:
    profile = await update_profile(db, current_user.id, req)
    return StudentProfileResponse.model_validate(profile)


# /goals alias
@compat_router.get("/goals", response_model=List[GoalResponse])
async def get_goals_alias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[GoalResponse]:
    goals = await list_goals(db, current_user.id)
    return [GoalResponse.model_validate(g) for g in goals]


@compat_router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def post_goal_alias(
    req: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    goal = await create_goal(db, current_user.id, req)
    return GoalResponse.model_validate(goal)


@compat_router.patch("/goals/{goal_id}", response_model=GoalResponse)
async def patch_goal_alias(
    goal_id: uuid.UUID,
    req: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    goal = await update_goal(db, current_user.id, goal_id, req)
    return GoalResponse.model_validate(goal)


@compat_router.delete("/goals/{goal_id}")
async def delete_goal_alias(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    await delete_goal(db, current_user.id, goal_id)
    return {"status": "success", "message": "Goal deleted"}


# /availability alias
@compat_router.get("/availability", response_model=List[AvailabilityWindowResponse])
async def get_availability_alias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AvailabilityWindowResponse]:
    windows = await get_availability_windows(db, current_user.id)
    return [AvailabilityWindowResponse.model_validate(w) for w in windows]


@compat_router.put("/availability", response_model=List[AvailabilityWindowResponse])
async def put_availability_alias(
    req: AvailabilityBatchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AvailabilityWindowResponse]:
    windows = await set_availability_windows(db, current_user.id, req.windows)
    return [AvailabilityWindowResponse.model_validate(w) for w in windows]


# /progress alias
@compat_router.get("/progress", response_model=ProgressOverviewResponse)
async def get_progress_alias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressOverviewResponse:
    return await get_student_progress_overview(db, current_user.id)


# /recommendations alias
@compat_router.get("/recommendations", response_model=StudentSuggestionsResponse)
async def get_recommendations_alias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentSuggestionsResponse:
    return await get_student_suggestions(db, current_user.id)


# /home alias
@compat_router.get("/home", response_model=StudentHomeResponse)
async def get_home_alias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentHomeResponse:
    return await get_student_home_dashboard(db, current_user.id)


# /academic/discover alias
@compat_router.post("/academic/discover", response_model=DiscoveredSyllabusResponse)
async def post_discover_syllabus_alias(
    current_user: User = Depends(get_current_user),
) -> DiscoveredSyllabusResponse:
    return await trigger_academic_discovery(current_user.id)


# /academic/syllabus alias
@compat_router.post("/academic/syllabus", response_model=ConfirmSyllabusResponse)
async def post_confirm_syllabus_alias(
    req: ConfirmSyllabusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfirmSyllabusResponse:
    return await confirm_and_persist_syllabus(db, current_user.id, req)


# /rescue alias
@compat_router.post("/rescue", response_model=ExamPlanResponse)
async def post_rescue_alias(
    req: ExamModeGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamPlanResponse:
    return await generate_exam_mode_plan(db, current_user.id, req)
